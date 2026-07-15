#!/usr/bin/env python3
"""
PM × LLM Reasoning Trace Pilot (Real API via Ollama Cloud HTTP API)
Uses OpenClaw's API key to call ollama cloud directly.
"""

import subprocess
import json
import time
import os
import re
import urllib.request
import urllib.error
from collections import Counter, defaultdict

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

NUM_QUESTIONS = 20
OUTPUT_DIR = "pilot_real_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# GSM8K sample questions
GSM8K_QUESTIONS = [
    {"id": 1, "question": "Janet's ducks lay 16 eggs per day. She eats 3 for breakfast and bakes muffins with 4. She sells the remainder at $2 each. How much does she make per day?", "answer": 18},
    {"id": 2, "question": "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total?", "answer": 3},
    {"id": 3, "question": "Josh decides to try flipping a house. He buys it for $80,000 and puts in $50,000 worth of repairs. The value increases by 150%. How much profit does he make?", "answer": 70000},
    {"id": 4, "question": "James writes a 3-page letter to 2 different friends twice a week. How many pages does he write per year?", "answer": 624},
    {"id": 5, "question": "Mark has a garden with flowers. He has 5 rows of 6 flowers each. If he picks half of them, how many flowers remain?", "answer": 15},
    {"id": 6, "question": "A pizza is cut into 8 slices. If 3 people eat 2 slices each, how many slices are left?", "answer": 2},
    {"id": 7, "question": "A train travels 60 km/h for 2.5 hours, then 80 km/h for 1.5 hours. What is the total distance?", "answer": 270},
    {"id": 8, "question": "A store sells pencils at 3 for $1. How much would 18 pencils cost?", "answer": 6},
    {"id": 9, "question": "Tom has 5 toy cars. He gets 3 more for his birthday and gives 2 to his sister. How many does he have now?", "answer": 6},
    {"id": 10, "question": "A recipe needs 2 cups of flour for 4 servings. How many cups for 10 servings?", "answer": 5},
    {"id": 11, "question": "A book has 240 pages. If you read 30 pages per day, how many days to finish?", "answer": 8},
    {"id": 12, "question": "A box has 24 chocolates. If 1/4 are dark, 1/3 are milk, and the rest are white, how many are white?", "answer": 10},
    {"id": 13, "question": "Lisa earns $15/hour and works 8 hours Monday through Friday. How much does she earn in a week?", "answer": 600},
    {"id": 14, "question": "A rectangle has length 12cm and width 5cm. What is its perimeter?", "answer": 34},
    {"id": 15, "question": "If 5 workers can build a wall in 10 days, how long would 2 workers take?", "answer": 25},
    {"id": 16, "question": "A school has 450 students. 2/5 are boys. How many girls are there?", "answer": 270},
    {"id": 17, "question": "A car uses 8 liters per 100km. How much fuel for 350km?", "answer": 28},
    {"id": 18, "question": "A shirt costs $40. It's on sale for 25% off. What's the sale price?", "answer": 30},
    {"id": 19, "question": "A bag has red, blue, and green marbles in ratio 2:3:5. If there are 40 green marbles, how many total?", "answer": 80},
    {"id": 20, "question": "A clock shows 3:15. What is the angle between the hour and minute hands?", "answer": 7.5},
]

# ============================================================
# Step 1: Call models via HTTP API
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
        with urllib.request.urlopen(req, timeout=120) as resp:
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
            "response": "",
            "thinking": "",
            "elapsed": elapsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error": f"HTTP {e.code}: {body[:200]}",
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "response": "",
            "thinking": "",
            "elapsed": elapsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error": str(e),
        }

def run_experiment():
    """Call all models on all questions."""
    results_file = f"{OUTPUT_DIR}/raw_responses.json"
    
    if os.path.exists(results_file):
        with open(results_file) as f:
            existing = json.load(f)
        # Check if all models are done
        all_done = all(
            model_name in existing and len(existing[model_name]) >= NUM_QUESTIONS
            for _, model_name in MODELS
        )
        if all_done:
            print("  All models already done, loading cached results.")
            return existing
        # Otherwise, keep partial results and continue
        all_results = existing
    else:
        all_results = {}
    
    for model_id, model_name in MODELS:
        print(f"\n=== Calling {model_name} ({model_id}) ===")
        
        if model_name not in all_results:
            all_results[model_name] = []
        
        # Skip already completed questions
        done_count = len(all_results[model_name])
        if done_count >= NUM_QUESTIONS:
            print(f"  Already complete ({done_count} questions)")
            continue
        
        for i in range(done_count, NUM_QUESTIONS):
            q = GSM8K_QUESTIONS[i]
            prompt = f"""Solve this math problem step by step. Show your reasoning clearly.

Problem: {q['question']}

Think step by step and give your final answer as a number after 'Answer:'."""
            
            print(f"  Q{q['id']}/20...", end=" ", flush=True)
            result = call_ollama_api(model_id, prompt)
            
            # Extract numeric answer
            response = result["response"]
            answer_match = re.findall(r'[Aa]nswer[:\s]*\$?([\d,.]+)', response)
            if answer_match:
                try:
                    predicted = float(answer_match[-1].replace(",", ""))
                    if predicted == int(predicted):
                        predicted = int(predicted)
                except:
                    predicted = None
            else:
                numbers = re.findall(r'[\d,.]+', response)
                try:
                    predicted = float(numbers[-1].replace(",", "")) if numbers else None
                    if predicted is not None and predicted == int(predicted):
                        predicted = int(predicted)
                except:
                    predicted = None
            
            entry = {
                "model": model_name,
                "model_id": model_id,
                "question_id": q["id"],
                "question": q["question"],
                "correct_answer": q["answer"],
                "predicted_answer": predicted,
                "correct": predicted == q["answer"] if predicted is not None else False,
                "response": response,
                "thinking": result["thinking"],
                "elapsed": round(result["elapsed"], 2),
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["total_tokens"],
                "error": result["error"],
            }
            all_results[model_name].append(entry)
            
            status = "OK" if entry["correct"] else "X"
            print(f"{status} ({result['elapsed']:.1f}s, {result['total_tokens']} tok)")
            
            # Save incrementally
            with open(results_file, "w") as f:
                json.dump(all_results, f, indent=2)
    
    return all_results

# ============================================================
# Step 2: Segment CoT into semantic steps
# ============================================================

def segment_cot(response):
    """Segment a CoT response into semantic steps."""
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
    """Label a step with an activity type."""
    text_lower = step_text.lower()
    
    if re.search(r'[Aa]nswer[:\s]*\$?[\d,.]+', step_text) or re.search(r'(?:is|=)\s*\$?[\d,.]+\s*$', step_text.strip()):
        return "answer"
    if any(w in text_lower for w in ["understand", "problem says", "need to find", "given", "we have", "the problem"]):
        return "understand"
    if any(w in text_lower for w in ["recall", "know that", "formula", "remember", "the rule"]):
        return "recall"
    if any(w in text_lower for w in ["plan", "strategy", "approach", "first.*then", "let's break"]):
        return "plan"
    if any(w in text_lower for w in ["calculate", "compute", "multiply", "divide", "add", "subtract", "times", "+", "x", "/", "sum", "total"]):
        return "calculate"
    if any(w in text_lower for w in ["because", "since", "so", "therefore", "thus", "which means", "this gives"]):
        return "reason"
    if any(w in text_lower for w in ["check", "verify", "let's see", "confirm", "double-check"]):
        return "verify"
    if any(w in text_lower for w in ["wait", "no,", "actually", "reconsider", "let me redo", "mistake"]):
        return "reconsider"
    if re.search(r'\d+.*[+\-*/].*\d+', text_lower):
        return "calculate"
    return "reason"

def build_traces(all_results):
    """Build PM event log from raw responses."""
    all_traces = {}
    
    for model_name, responses in all_results.items():
        all_traces[model_name] = []
        
        for resp in responses:
            # Combine thinking + response as the full CoT
            full_cot = ""
            if resp.get("thinking"):
                full_cot += resp["thinking"] + "\n\n"
            full_cot += resp["response"]
            
            steps = segment_cot(full_cot)
            
            trace = []
            for step in steps:
                activity = label_step(step)
                trace.append(activity)
            
            if not trace or trace[-1] != "answer":
                trace.append("answer")
            if not trace or trace[0] != "understand":
                trace.insert(0, "understand")
            
            all_traces[model_name].append({
                "case_id": f"{model_name}_Q{resp['question_id']}",
                "model": model_name,
                "question_id": resp["question_id"],
                "trace": trace,
                "num_steps": len(trace),
                "num_loops": trace.count("reconsider"),
                "has_verify": "verify" in trace,
                "correct": resp["correct"],
                "elapsed": resp["elapsed"],
                "total_tokens": resp.get("total_tokens", 0),
                "completion_tokens": resp.get("completion_tokens", 0),
                "raw_steps": steps,
            })
    
    return all_traces

# ============================================================
# Step 3: PM Analysis
# ============================================================

def build_event_log(all_traces):
    """Convert traces to PM4Py event log."""
    events = []
    for model_traces in all_traces.values():
        for case in model_traces:
            for idx, activity in enumerate(case["trace"]):
                events.append({
                    "case:concept:name": case["case_id"],
                    "concept:name": activity,
                    "time:timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(seconds=idx),
                    "model": case["model"],
                    "question_id": str(case["question_id"]),
                    "step_order": idx,
                    "correct": str(case["correct"]),
                })
    
    df = pd.DataFrame(events)
    df["case:concept:name"] = df["case:concept:name"].astype(str)
    df["concept:name"] = df["concept:name"].astype(str)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
    
    log = pm4py.convert_to_event_log(df, case_id_key="case:concept:name")
    return log, df

def run_pm_analysis(all_traces, log_df):
    """Run process discovery and conformance checking."""
    discovery_results = {}
    
    for model_name in all_traces.keys():
        model_df = log_df[log_df["model"] == model_name].copy()
        model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
        
        try:
            net, im, fm = pm4py.discover_petri_net_inductive(model_log)
            tree = pm4py.discover_process_tree_inductive(model_log)
            variants = pm4py.get_variants(model_log)
            
            discovery_results[model_name] = {
                "net": net, "im": im, "fm": fm,
                "tree": tree,
                "variants": len(variants),
            }
        except Exception as e:
            print(f"  Discovery failed for {model_name}: {e}")
            discovery_results[model_name] = None
    
    accuracy_by_model = {}
    for model_name, traces in all_traces.items():
        correct = sum(1 for t in traces if t["correct"])
        accuracy_by_model[model_name] = correct / len(traces)
    
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
                fitness = pm4py.conformance_diagnostics_token_based_replay(
                    model_log, ref_net, ref_im, ref_fm
                )
                alignments = pm4py.conformance_diagnostics_alignments(
                    model_log, ref_net, ref_im, ref_fm
                )
                
                avg_fitness = sum(t["trace_fitness"] for t in fitness) / len(fitness)
                
                total_log_moves = 0
                total_model_moves = 0
                for a in alignments:
                    for move in a["alignment"]:
                        if move[0] != ">>" and move[1] == ">>":
                            total_log_moves += 1
                        elif move[0] == ">>" and move[1] != ">>":
                            total_model_moves += 1
                
                conformance_results[model_name] = {
                    "avg_fitness": avg_fitness,
                    "log_moves": total_log_moves,
                    "model_moves": total_model_moves,
                    "total_deviations": total_log_moves + total_model_moves,
                }
            except Exception as e:
                print(f"  Conformance failed for {model_name}: {e}")
                conformance_results[model_name] = {
                    "avg_fitness": None,
                    "log_moves": None,
                    "model_moves": None,
                    "total_deviations": None,
                    "error": str(e),
                }
    
    return discovery_results, conformance_results, accuracy_by_model

# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("PM x LLM Reasoning Trace Pilot (Real API)")
    print("=" * 60)
    
    # Step 1: Collect responses
    print("\n[Step 1] Calling models via Ollama Cloud API...")
    all_results = run_experiment()
    
    # Stats
    print("\n[Step 1 Results]")
    for model_name, responses in all_results.items():
        if not responses:
            continue
        correct = sum(1 for r in responses if r["correct"])
        avg_time = sum(r["elapsed"] for r in responses) / len(responses)
        total_time = sum(r["elapsed"] for r in responses)
        avg_tokens = sum(r.get("total_tokens", 0) for r in responses) / len(responses)
        errors = sum(1 for r in responses if r.get("error"))
        print(f"  {model_name}: {correct}/{len(responses)} correct ({correct/len(responses):.0%}), avg {avg_time:.1f}s/qa, avg {avg_tokens:.0f} tokens, {errors} errors")
    
    # Step 2: Segment and label
    print("\n[Step 2] Segmenting CoT traces...")
    all_traces = build_traces(all_results)
    
    for model_name, traces in all_traces.items():
        avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
        avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
        verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
        avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
        print(f"  {model_name}: avg {avg_steps:.1f} steps, {avg_loops:.1f} loops, verify {verify_rate:.0%}, avg {avg_tokens:.0f} tokens")
    
    # Step 3: PM analysis
    print("\n[Step 3] Building event log and running PM analysis...")
    log, log_df = build_event_log(all_traces)
    print(f"  Event log: {len(log)} cases, {len(log_df)} events")
    print(f"  Activities: {sorted(log_df['concept:name'].unique())}")
    
    discovery_results, conformance_results, accuracy = run_pm_analysis(all_traces, log_df)
    
    # Step 4: Summary
    print("\n[Step 4] Path Quality Metrics Summary")
    print("-" * 120)
    
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
        
        metrics.append({
            "Model": model_name,
            "Accuracy": f"{accuracy.get(model_name, 0):.0%}",
            "Avg_Steps": round(avg_steps, 1),
            "Avg_Loops": round(avg_loops, 2),
            "Verify_Rate": f"{verify_rate:.0%}",
            "Variants": disc.get("variants", "?") if disc else "?",
            "Avg_Time_s": round(avg_time, 1),
            "Avg_Tokens": round(avg_tokens, 0),
            "Tokens_per_Step": round(avg_tokens / avg_steps, 1) if avg_steps > 0 else 0,
            "Fitness": round(conf.get("avg_fitness", 0), 4) if conf.get("avg_fitness") else "N/A",
            "Deviations": conf.get("total_deviations", "N/A"),
        })
    
    metrics_df = pd.DataFrame(metrics)
    print(metrics_df.to_string(index=False))
    
    # Save everything
    metrics_df.to_csv(f"{OUTPUT_DIR}/path_quality_metrics.csv", index=False)
    
    with open(f"{OUTPUT_DIR}/traces.json", "w") as f:
        json.dump({k: [{kk: vv for kk, vv in v.items() if kk != "raw_steps"} 
                       for v in vs] for k, vs in all_traces.items()}, f, indent=2)
    
    conf_save = {k: {kk: vv for kk, vv in v.items()} 
                 for k, v in conformance_results.items()}
    with open(f"{OUTPUT_DIR}/conformance.json", "w") as f:
        json.dump(conf_save, f, indent=2, default=str)
    
    # Save visualizations
    for model_name, result in discovery_results.items():
        if result:
            safe = model_name.replace(" ", "_").replace("/", "_")
            try:
                pm4py.save_vis_petri_net(result["net"], result["im"], result["fm"],
                                          f"{OUTPUT_DIR}/petri_net_{safe}.png")
                pm4py.save_vis_process_tree(result["tree"],
                                             f"{OUTPUT_DIR}/process_tree_{safe}.png")
                print(f"  Saved: {safe}.png")
            except Exception as e:
                print(f"  Viz failed for {model_name}: {e}")
    
    print(f"\nResults saved to {OUTPUT_DIR}/")
    print("Pilot complete!")

if __name__ == "__main__":
    main()