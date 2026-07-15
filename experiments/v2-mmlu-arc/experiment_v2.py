#!/usr/bin/env python3
"""
PM × LLM Reasoning Trace Experiment v2 (Harder Questions + Self-Assessment)

Improvements over v1:
1. MMLU STEM + ARC Challenge (harder benchmarks, more accuracy variance)
2. Self-assessment: ask model to rate confidence 0-100%
3. More questions (50 per benchmark = 100 total)
4. Same 5 models for comparability
"""

import json
import time
import os
import re
import urllib.request
import urllib.error
from collections import Counter
import random

import pm4py
import pandas as pd

# ============================================================
# Config
# ============================================================

OLLAMA_API_URL = "https://ollama.com/api/chat"
OLLAMA_API_KEY = "7d30048207d541afa72fceb4a639852f._kuPlqyToP_iFGGYEek_UIcA"

MODELS = [
    ("gpt-oss:20b-cloud", "GPT-OSS-20B"),
    ("deepseek-v4-flash:cloud", "DeepSeek-V4-Flash-158B"),
    ("gpt-oss:120b-cloud", "GPT-OSS-120B"),
    ("glm-4.7:cloud", "GLM-4.7-357B"),
    ("glm-5.2:cloud", "GLM-5.2-756B"),
]

NUM_QUESTIONS_PER_BENCHMARK = 50  # 50 MMLU STEM + 50 ARC = 100 total
OUTPUT_DIR = "experiment_v2_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# Load Question Sets
# ============================================================

def load_mmlu_stem():
    """Load MMLU STEM questions (math, physics, stats, logic)."""
    from datasets import load_dataset
    ds = load_dataset('cais/mmlu', 'all', split='test')
    
    # Pick STEM subjects
    stem_subjects = [
        'high_school_mathematics', 'college_mathematics', 'abstract_algebra',
        'high_school_statistics', 'probability', 'formal_logic',
        'high_school_physics', 'college_physics', 'machine_learning',
    ]
    
    questions = []
    for i, row in enumerate(ds):
        if row['subject'] in stem_subjects:
            questions.append({
                "id": f"MMLU_{row['subject']}_{i}",
                "benchmark": "MMLU_STEM",
                "subject": row['subject'],
                "question": row['question'],
                "choices": row['choices'],
                "answer_index": row['answer'],  # 0-3
                "answer_letter": chr(65 + row['answer']),  # A-D
                "answer_text": row['choices'][row['answer']],
            })
    
    # Sample 50, balanced across subjects
    random.seed(42)
    random.shuffle(questions)
    
    # Try to balance across subjects
    by_subject = {}
    for q in questions:
        by_subject.setdefault(q['subject'], []).append(q)
    
    selected = []
    per_subject = NUM_QUESTIONS_PER_BENCHMARK // len(by_subject)
    for subj, qs in by_subject.items():
        selected.extend(qs[:per_subject])
    
    # Fill remaining if needed
    if len(selected) < NUM_QUESTIONS_PER_BENCHMARK:
        remaining = [q for q in questions if q not in selected]
        selected.extend(remaining[:NUM_QUESTIONS_PER_BENCHMARK - len(selected)])
    
    return selected[:NUM_QUESTIONS_PER_BENCHMARK]

def load_arc_challenge():
    """Load ARC Challenge questions."""
    from datasets import load_dataset
    ds = load_dataset('allenai/ai2_arc', 'ARC-Challenge', split='test')
    
    questions = []
    for i, row in enumerate(ds):
        choices = row['choices']
        answer_key = row['answerKey']
        
        # Find answer index
        answer_idx = None
        for j, label in enumerate(choices['label']):
            if label == answer_key:
                answer_idx = j
                break
        
        if answer_idx is None:
            continue
        
        questions.append({
            "id": f"ARC_{row['id']}",
            "benchmark": "ARC_Challenge",
            "subject": "science",
            "question": row['question'],
            "choices": choices['text'],
            "answer_index": answer_idx,
            "answer_letter": answer_key,
            "answer_text": choices['text'][answer_idx],
        })
    
    random.seed(42)
    random.shuffle(questions)
    return questions[:NUM_QUESTIONS_PER_BENCHMARK]

# ============================================================
# API Call
# ============================================================

def call_ollama_api(model, prompt):
    """Call ollama cloud via HTTP API."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode()
    
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
        },
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
            elapsed = time.time() - start
            
            content = data.get("message", {}).get("content", "")
            thinking = data.get("message", {}).get("thinking", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            
            return {
                "response": content,
                "thinking": thinking,
                "elapsed": elapsed,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read().decode() if e.readable() else ""
        return {
            "response": "", "thinking": "", "elapsed": elapsed,
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "error": f"HTTP {e.code}: {body[:200]}",
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "response": "", "thinking": "", "elapsed": elapsed,
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "error": str(e),
        }

# ============================================================
# Experiment
# ============================================================

def make_reasoning_prompt(q):
    """Create prompt for reasoning question."""
    choices_str = "\n".join(
        f"  {chr(65+i)}. {choice}" for i, choice in enumerate(q['choices'])
    )
    return f"""Solve this problem step by step. Show your reasoning clearly.

Question: {q['question']}

Choices:
{choices_str}

Think step by step, then give your answer as a single letter (A, B, C, or D) after 'Answer:'."""

def make_confidence_prompt(answer):
    """Create prompt for self-assessment."""
    return f"""You just answered: {answer}

How confident are you that this answer is correct? Give a single number from 0 to 100 (0 = completely unsure, 100 = absolutely certain).

Confidence:"""

def extract_answer(response, q):
    """Extract answer letter from response."""
    # Try "Answer: X" pattern
    answer_match = re.findall(r'[Aa]nswer[:\s]*([A-Da-d])\b', response)
    if answer_match:
        return answer_match[-1].upper()
    
    # Try "The answer is X"
    answer_match = re.findall(r'(?:answer is|correct answer is|answer:)\s*([A-Da-d])\b', response, re.I)
    if answer_match:
        return answer_match[-1].upper()
    
    # Try last standalone letter
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            return line
    
    # Try "(X)" pattern
    answer_match = re.findall(r'\(([A-Da-d])\)', response)
    if answer_match:
        return answer_match[-1].upper()
    
    return None

def extract_confidence(response):
    """Extract confidence score from response."""
    numbers = re.findall(r'\b(\d{1,3})\b', response)
    if numbers:
        val = int(numbers[-1])
        if 0 <= val <= 100:
            return val
    return None

def run_experiment(questions):
    """Run the full experiment."""
    results_file = f"{OUTPUT_DIR}/raw_responses.json"
    
    if os.path.exists(results_file):
        with open(results_file) as f:
            all_results = json.load(f)
    else:
        all_results = {}
    
    for model_id, model_name in MODELS:
        print(f"\n=== {model_name} ({model_id}) ===")
        
        if model_name not in all_results:
            all_results[model_name] = []
        
        done = len(all_results[model_name])
        if done >= len(questions):
            print(f"  Already complete ({done} questions)")
            continue
        
        for i in range(done, len(questions)):
            q = questions[i]
            prompt = make_reasoning_prompt(q)
            
            print(f"  [{i+1}/{len(questions)}] {q['benchmark']}... ", end="", flush=True)
            
            # Step 1: Answer the question
            result = call_ollama_api(model_id, prompt)
            
            if result["error"]:
                print(f"ERROR: {result['error'][:50]}")
                all_results[model_name].append({
                    "model": model_name, "model_id": model_id,
                    "question_id": q['id'], "benchmark": q['benchmark'],
                    "question": q['question'], "choices": q['choices'],
                    "correct_letter": q['answer_letter'],
                    "predicted_letter": None, "correct": False,
                    "response": "", "thinking": "",
                    "confidence": None,
                    "elapsed": result["elapsed"],
                    "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                    "error": result["error"],
                })
                with open(results_file, "w") as f:
                    json.dump(all_results, f, indent=2)
                continue
            
            predicted = extract_answer(result["response"], q)
            correct = (predicted == q['answer_letter']) if predicted else False
            
            # Step 2: Ask for confidence
            conf_prompt = make_confidence_prompt(predicted or "unknown")
            conf_result = call_ollama_api(model_id, conf_prompt)
            confidence = extract_confidence(conf_result["response"])
            
            entry = {
                "model": model_name, "model_id": model_id,
                "question_id": q['id'], "benchmark": q['benchmark'],
                "subject": q.get('subject', ''),
                "question": q['question'], "choices": q['choices'],
                "correct_letter": q['answer_letter'],
                "correct_text": q['answer_text'],
                "predicted_letter": predicted,
                "correct": correct,
                "response": result["response"],
                "thinking": result["thinking"],
                "confidence": confidence,
                "elapsed": round(result["elapsed"], 2),
                "total_tokens": result["total_tokens"],
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "confidence_tokens": conf_result.get("total_tokens", 0),
                "error": result["error"],
            }
            all_results[model_name].append(entry)
            
            status = "OK" if correct else "X"
            conf_str = f" conf={confidence}%" if confidence is not None else " conf=?"
            print(f"{status} ({result['elapsed']:.1f}s, {result['total_tokens']}tok{conf_str})")
            
            # Save incrementally
            with open(results_file, "w") as f:
                json.dump(all_results, f, indent=2)
    
    return all_results

# ============================================================
# Step Segmentation & Labeling (same as v1)
# ============================================================

def segment_cot(response):
    lines = response.split("\n")
    steps = []
    current_step = ""
    for line in lines:
        line = line.strip()
        if not line:
            if current_step:
                steps.append(current_step)
                current_step = ""
            continue
        starts_new = (
            re.match(r'^\d+[\.\)]\s', line) or
            re.match(r'^[-*]\s', line) or
            re.match(r'^(Step|First|Second|Third|Then|Next|Now|So|Finally|Therefore|Let me|Let\'s|I need|To find|We need)', line, re.I)
        )
        if starts_new and current_step:
            steps.append(current_step)
            current_step = line
        else:
            current_step = (current_step + " " + line).strip() if current_step else line
    if current_step:
        steps.append(current_step)
    steps = [s for s in steps if not re.match(r'^[Aa]nswer[:\s]', s)]
    return steps

def label_step(step_text):
    text_lower = step_text.lower()
    if re.search(r'[Aa]nswer[:\s]*[A-Da-d]\b', step_text):
        return "answer"
    if re.search(r'[Aa]nswer[:\s]*\$?[\d,.]+', step_text) or re.search(r'(?:is|=)\s*\$?[\d,.]+\s*$', step_text.strip()):
        return "answer"
    if any(w in text_lower for w in ["understand", "problem says", "need to find", "given", "we have", "the problem", "need to determine", "looking for"]):
        return "understand"
    if any(w in text_lower for w in ["recall", "know that", "formula", "remember", "the rule", "by definition"]):
        return "recall"
    if any(w in text_lower for w in ["plan", "strategy", "approach", "first.*then", "let's break"]):
        return "plan"
    if any(w in text_lower for w in ["calculate", "compute", "multiply", "divide", "add", "subtract", "times", "+", "x", "/", "sum", "total", "equals"]):
        return "calculate"
    if any(w in text_lower for w in ["because", "since", "so", "therefore", "thus", "which means", "this gives", "that means", "implies", "hence"]):
        return "reason"
    if any(w in text_lower for w in ["check", "verify", "let's see", "confirm", "double-check", "makes sense"]):
        return "verify"
    if any(w in text_lower for w in ["wait", "no,", "actually", "reconsider", "let me redo", "mistake", "incorrect", "wrong"]):
        return "reconsider"
    if any(w in text_lower for w in ["option", "choice", "eliminate", "not correct", "cannot be", "must be"]):
        return "evaluate"
    if re.search(r'\d+.*[+\-*/].*\d+', text_lower):
        return "calculate"
    return "reason"

def build_traces(all_results):
    all_traces = {}
    for model_name, responses in all_results.items():
        all_traces[model_name] = []
        for resp in responses:
            full_cot = ""
            if resp.get("thinking"):
                full_cot += resp["thinking"] + "\n\n"
            full_cot += resp["response"]
            
            steps = segment_cot(full_cot)
            trace = [label_step(s) for s in steps]
            
            if not trace or trace[-1] != "answer":
                trace.append("answer")
            if not trace or trace[0] != "understand":
                trace.insert(0, "understand")
            
            all_traces[model_name].append({
                "case_id": f"{model_name}_{resp['question_id']}",
                "model": model_name,
                "question_id": resp["question_id"],
                "benchmark": resp.get("benchmark", ""),
                "trace": trace,
                "num_steps": len(trace),
                "num_loops": trace.count("reconsider"),
                "has_verify": "verify" in trace,
                "correct": resp["correct"],
                "elapsed": resp["elapsed"],
                "total_tokens": resp.get("total_tokens", 0),
                "confidence": resp.get("confidence"),
            })
    return all_traces

# ============================================================
# PM Analysis
# ============================================================

def build_event_log(all_traces):
    events = []
    for model_traces in all_traces.values():
        for case in model_traces:
            for idx, activity in enumerate(case["trace"]):
                events.append({
                    "case:concept:name": case["case_id"],
                    "concept:name": activity,
                    "time:timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(seconds=idx),
                    "model": case["model"],
                    "benchmark": case.get("benchmark", ""),
                    "question_id": str(case["question_id"]),
                    "correct": str(case["correct"]),
                })
    df = pd.DataFrame(events)
    df["case:concept:name"] = df["case:concept:name"].astype(str)
    df["concept:name"] = df["concept:name"].astype(str)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
    log = pm4py.convert_to_event_log(df, case_id_key="case:concept:name")
    return log, df

def run_pm_analysis(all_traces, log_df):
    discovery_results = {}
    for model_name in all_traces.keys():
        model_df = log_df[log_df["model"] == model_name].copy()
        model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
        try:
            net, im, fm = pm4py.discover_petri_net_inductive(model_log)
            tree = pm4py.discover_process_tree_inductive(model_log)
            variants = pm4py.get_variants(model_log)
            discovery_results[model_name] = {"net": net, "im": im, "fm": fm, "tree": tree, "variants": len(variants)}
        except Exception as e:
            print(f"  Discovery failed for {model_name}: {e}")
            discovery_results[model_name] = None
    
    accuracy_by_model = {m: sum(1 for t in ts if t["correct"])/len(ts) for m, ts in all_traces.items()}
    ref_model = max(accuracy_by_model, key=accuracy_by_model.get)
    print(f"\n  Reference model: {ref_model} (accuracy={accuracy_by_model[ref_model]:.0%})")
    
    conformance_results = {}
    if discovery_results.get(ref_model):
        ref_net = discovery_results[ref_model]["net"]
        ref_im = discovery_results[ref_model]["im"]
        ref_fm = discovery_results[ref_model]["fm"]
        for model_name in all_traces.keys():
            model_df = log_df[log_df["model"] == model_name].copy()
            model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
            try:
                fitness = pm4py.conformance_diagnostics_token_based_replay(model_log, ref_net, ref_im, ref_fm)
                avg_fitness = sum(t["trace_fitness"] for t in fitness) / len(fitness)
                alignments = pm4py.conformance_diagnostics_alignments(model_log, ref_net, ref_im, ref_fm)
                total_dev = sum(
                    1 for a in alignments for move in a["alignment"]
                    if (move[0] != ">>" and move[1] == ">>") or (move[0] == ">>" and move[1] != ">>")
                )
                conformance_results[model_name] = {"avg_fitness": avg_fitness, "total_deviations": total_dev}
            except Exception as e:
                print(f"  Conformance failed for {model_name}: {e}")
                conformance_results[model_name] = {"avg_fitness": None, "total_deviations": None, "error": str(e)}
    
    return discovery_results, conformance_results, accuracy_by_model

# ============================================================
# LCAE-like Analysis (simplified)
# ============================================================

def compute_calibration_metrics(all_results):
    """Compute simplified calibration metrics (Brier score, accuracy vs confidence)."""
    calibration = {}
    for model_name, responses in all_results.items():
        # Filter out entries without confidence
        valid = [r for r in responses if r.get("confidence") is not None and not r.get("error")]
        if not valid:
            calibration[model_name] = {"brier": None, "avg_confidence": None, "confidence_correct": None, "confidence_wrong": None}
            continue
        
        # Brier score: (confidence/100 - correct)^2
        brier_scores = []
        conf_correct = []
        conf_wrong = []
        for r in valid:
            conf = r["confidence"] / 100.0
            outcome = 1.0 if r["correct"] else 0.0
            brier_scores.append((conf - outcome) ** 2)
            if r["correct"]:
                conf_correct.append(r["confidence"])
            else:
                conf_wrong.append(r["confidence"])
        
        calibration[model_name] = {
            "brier_score": sum(brier_scores) / len(brier_scores),
            "brier_count": len(brier_scores),
            "avg_confidence": sum(r["confidence"] for r in valid) / len(valid),
            "confidence_correct": sum(conf_correct)/len(conf_correct) if conf_correct else None,
            "confidence_wrong": sum(conf_wrong)/len(conf_wrong) if conf_wrong else None,
            "confidence_gap": (sum(conf_correct)/len(conf_correct) - sum(conf_wrong)/len(conf_wrong)) if conf_correct and conf_wrong else None,
        }
    return calibration

# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("PM x LLM Reasoning Trace Experiment v2")
    print("Harder benchmarks + self-assessment")
    print("=" * 60)
    
    # Load questions
    print("\n[Step 0] Loading question sets...")
    mmlu_qs = load_mmlu_stem()
    arc_qs = load_arc_challenge()
    questions = mmlu_qs + arc_qs
    print(f"  MMLU STEM: {len(mmlu_qs)} questions")
    print(f"  ARC Challenge: {len(arc_qs)} questions")
    print(f"  Total: {len(questions)} questions")
    
    # Step 1: Run experiment
    print("\n[Step 1] Calling models via Ollama Cloud API...")
    all_results = run_experiment(questions)
    
    # Stats
    print("\n[Step 1 Results]")
    for model_name, responses in all_results.items():
        if not responses:
            continue
        correct = sum(1 for r in responses if r["correct"])
        errors = sum(1 for r in responses if r.get("error"))
        valid_conf = [r for r in responses if r.get("confidence") is not None]
        avg_time = sum(r["elapsed"] for r in responses) / len(responses)
        avg_tok = sum(r.get("total_tokens", 0) for r in responses) / len(responses)
        avg_conf = sum(r["confidence"] for r in valid_conf) / len(valid_conf) if valid_conf else 0
        print(f"  {model_name}: {correct}/{len(responses)} correct ({correct/len(responses):.0%}), "
              f"avg {avg_time:.1f}s, {avg_tok:.0f}tok, conf={avg_conf:.0f}%, {errors} errors")
    
    # Step 2: Segmentation
    print("\n[Step 2] Segmenting CoT traces...")
    all_traces = build_traces(all_results)
    
    for model_name, traces in all_traces.items():
        avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
        avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
        verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
        avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
        print(f"  {model_name}: avg {avg_steps:.1f} steps, {avg_loops:.1f} loops, verify {verify_rate:.0%}, {avg_tokens:.0f} tok")
    
    # Step 3: Calibration
    print("\n[Step 3] Computing calibration metrics...")
    calibration = compute_calibration_metrics(all_results)
    for model_name, cal in calibration.items():
        print(f"  {model_name}: Brier={cal['brier_score']:.4f}, "
              f"avg_conf={cal['avg_confidence']:.0f}%, "
              f"conf_correct={cal['confidence_correct']}, conf_wrong={cal['confidence_wrong']}, "
              f"gap={cal['confidence_gap']}")
    
    # Step 4: PM analysis
    print("\n[Step 4] PM analysis...")
    log, log_df = build_event_log(all_traces)
    print(f"  Event log: {len(log)} cases, {len(log_df)} events")
    print(f"  Activities: {sorted(log_df['concept:name'].unique())}")
    
    discovery_results, conformance_results, accuracy = run_pm_analysis(all_traces, log_df)
    
    # Step 5: Summary
    print("\n[Step 5] Full Summary")
    print("-" * 130)
    
    metrics = []
    for model_name in all_traces.keys():
        traces = all_traces[model_name]
        avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
        avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
        verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
        avg_time = sum(t["elapsed"] for t in traces) / len(traces)
        avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
        conf = conformance_results.get(model_name, {})
        disc = discovery_results.get(model_name, {})
        cal = calibration.get(model_name, {})
        
        metrics.append({
            "Model": model_name,
            "Accuracy": f"{accuracy.get(model_name, 0):.0%}",
            "Avg_Steps": round(avg_steps, 1),
            "Avg_Loops": round(avg_loops, 2),
            "Verify": f"{verify_rate:.0%}",
            "Variants": disc.get("variants", "?") if disc else "?",
            "Avg_Time_s": round(avg_time, 1),
            "Avg_Tokens": round(avg_tokens, 0),
            "Tok/Step": round(avg_tokens / avg_steps, 1) if avg_steps > 0 else 0,
            "Brier": round(cal.get("brier_score", 0), 4) if cal.get("brier_score") else "N/A",
            "Avg_Conf": f"{cal.get('avg_confidence', 0):.0f}%" if cal.get("avg_confidence") else "N/A",
            "Conf_Gap": round(cal.get("confidence_gap", 0), 1) if cal.get("confidence_gap") else "N/A",
            "Fitness": round(conf.get("avg_fitness", 0), 4) if conf.get("avg_fitness") else "N/A",
            "Deviations": conf.get("total_deviations", "N/A"),
        })
    
    metrics_df = pd.DataFrame(metrics)
    print(metrics_df.to_string(index=False))
    
    # Save
    metrics_df.to_csv(f"{OUTPUT_DIR}/full_metrics.csv", index=False)
    with open(f"{OUTPUT_DIR}/traces.json", "w") as f:
        json.dump({k: [{kk: vv for kk, vv in v.items()} for v in vs] for k, vs in all_traces.items()}, f, indent=2)
    with open(f"{OUTPUT_DIR}/conformance.json", "w") as f:
        json.dump({k: v for k, v in conformance_results.items()}, f, indent=2, default=str)
    with open(f"{OUTPUT_DIR}/calibration.json", "w") as f:
        json.dump(calibration, f, indent=2)
    
    # Save visualizations
    for model_name, result in discovery_results.items():
        if result:
            safe = model_name.replace(" ", "_").replace("/", "_")
            try:
                pm4py.save_vis_petri_net(result["net"], result["im"], result["fm"], f"{OUTPUT_DIR}/petri_net_{safe}.png")
                pm4py.save_vis_process_tree(result["tree"], f"{OUTPUT_DIR}/process_tree_{safe}.png")
                print(f"  Saved: {safe}.png")
            except Exception as e:
                print(f"  Viz failed for {model_name}: {e}")
    
    print(f"\nResults saved to {OUTPUT_DIR}/")
    print("Experiment v2 complete!")

if __name__ == "__main__":
    main()