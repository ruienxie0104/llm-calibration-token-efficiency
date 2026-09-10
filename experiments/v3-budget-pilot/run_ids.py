#!/usr/bin/env python3
"""
IDS Intervention Experiment.
2 models × 2 conditions (QOQ vs IDS) × 2 budgets × 3 reps × 30 questions.
= 720 answer + 720 confidence = 1440 API calls.
"""
import json, os, time, urllib.request, urllib.error, re, random
from pathlib import Path
from collections import defaultdict
from datasets import load_dataset

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"]
MODEL_MAP = {
    "GPT-OSS-20B": "gpt-oss:20b-cloud",
    "GPT-OSS-120B": "gpt-oss:120b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
    "GLM-5.2-756B": "glm-5.2:cloud",
}
BUDGETS = [256, 512]
CONDITIONS = ["qoq", "ids"]
REPLICATES = 3
SEED = 42
QUESTIONS = 30

def load_questions():
    rng = random.Random(SEED)
    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    candidates = [d for d in ds if d["level"] in [3, 4]]
    chosen = rng.sample(candidates, QUESTIONS)
    return [{"id": c["unique_id"], "problem": c["problem"], "answer": c["answer"],
             "level": c["level"], "subject": c["subject"]} for c in chosen]

def compute_difficulty(questions):
    import math
    # Fallback: use problem level as proxy if no precomputed beta
    for q in questions:
        q["beta"] = (q["level"] - 3)  # L3→0, L4→1

def call_ollama(model_name, messages, max_tokens=0):
    payload = {
        "model": MODEL_MAP[model_name],
        "messages": messages,
        "stream": False,
    }
    if max_tokens > 0:
        payload["options"] = {"num_predict": max_tokens, "temperature": 0.0}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"},
    )
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
            content = body.get("message", {}).get("content", "")
            pt = body.get("prompt_eval_count", 0)
            ct = body.get("eval_count", 0)
            return content, pt, ct, time.time() - start, None
    except urllib.error.HTTPError as e:
        return None, 0, 0, 0, f"HTTP {e.code}"
    except Exception as e:
        return None, 0, 0, 0, str(e)

def extract_boxed(text):
    if not text: return None
    m = re.findall(r'\\boxed\{(.*?)\}', text, re.DOTALL)
    return m[-1].strip() if m else None

def normalize(a):
    if not a: return ""
    a = re.sub(r'\\[a-z]+', '', a.strip())
    a = re.sub(r'[{}]', '', a)
    return a.replace(' ', '').lower()

def is_correct(pred, exp):
    if not pred: return False
    if normalize(pred) == normalize(exp): return True
    try:
        import ast
        def safe_eval(s):
            s = s.replace('\\frac','').replace('{','(').replace('}',')')
            s = s.replace('\\pi','3.141592653589793')
            t = ast.parse(s, mode='eval')
            for n in ast.walk(t):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub,
                                      ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)):
                    return None
            return eval(compile(t, '', 'eval'))
        pv, ev = safe_eval(pred), safe_eval(exp)
        if pv is not None and ev is not None and abs(pv-ev) < 1e-6: return True
    except: pass
    return False

def parse_confidence(text):
    if not text: return None
    nums = re.findall(r'(\d+)', text.strip())
    return min(100, max(0, int(nums[0]))) if nums else None

def make_ids_prompt(beta, problem):
    # Beta normalized to 1-5 scale
    level = max(1, min(5, round(beta + 1)))
    levels = {1: "very easy", 2: "easy", 3: "moderate", 4: "difficult", 5: "very difficult"}
    return f"This problem is rated difficulty {level} ({levels[level]}).\n\n{problem}"

def make_answer_prompt(problem, condition, beta=0):
    prompt = problem
    if condition == "ids":
        prompt = make_ids_prompt(beta, problem)
    return f"Solve the math problem step by step, then give the final answer in \\boxed{{}}.\n\n{prompt}"

def main():
    questions = load_questions()
    compute_difficulty(questions)
    with open(DATA_DIR / "ids_questions.json", "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Loaded {len(questions)} questions")

    total_calls = len(questions) * len(MODELS) * len(CONDITIONS) * len(BUDGETS) * REPLICATES * 2
    print(f"Total: {total_calls} API calls ({total_calls//2} answer + {total_calls//2} confidence)")
    print()

    checkpoint = RESULTS_DIR / "ids_raw.json"
    existing = []
    if checkpoint.exists():
        try:
            with open(checkpoint) as f:
                existing = json.load(f)
            print(f"Checkpoint: {len(existing)} existing calls")
        except: pass

    done_set = set()
    for r in existing:
        done_set.add((r["model"], r["condition"], r["budget"], r["replicate"], r["question_id"], r["call_type"]))

    results = list(existing)
    call_count = len(existing)
    start_time = time.time()

    for model in MODELS:
        for condition in CONDITIONS:
            for budget in BUDGETS:
                for rep in range(1, REPLICATES + 1):
                    for q in questions:
                        ak = (model, condition, budget, rep, q["id"], "answer")
                        if ak in done_set:
                            continue
                        call_count += 1
                        print(f"[{call_count}/{total_calls}] {model} | {condition} | b={budget} | r={rep} | q={q['id'][:20]}", end=" ... ", flush=True)

                        prompt = make_answer_prompt(q["problem"], condition, q.get("beta", 0))
                        msg = [{"role": "user", "content": prompt}]
                        content, pt, ct, elap, err = call_ollama(model, msg, max_tokens=budget)
                        if err:
                            print(f"ERR: {err}")
                            continue
                        boxed = extract_boxed(content) if content else None
                        correct = is_correct(boxed, q["answer"])
                        results.append({
                            "model": model, "condition": condition, "budget": budget,
                            "replicate": rep, "question_id": q["id"], "level": q["level"],
                            "subject": q["subject"], "call_type": "answer",
                            "prompt": prompt,
                            "response": content, "prompt_tokens": pt, "completion_tokens": ct,
                            "correct": correct, "parsed_answer": boxed or "",
                            "expected_answer": q["answer"], "elapsed": elap,
                        })
                        print(f"{'✓' if correct else '✗'} tok={ct}")

                        # Confidence
                        ck = (model, condition, budget, rep, q["id"], "confidence")
                        if ck in done_set:
                            continue
                        call_count += 1
                        conf_msg = [
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": content or ""},
                            {"role": "user", "content": "Based on your reasoning above, how confident are you that your answer is correct? Give ONLY a single number from 0 to 100."},
                        ]
                        conf, pt2, ct2, elap2, err2 = call_ollama(model, conf_msg)
                        conf_val = parse_confidence(conf)
                        results.append({
                            "model": model, "condition": condition, "budget": budget,
                            "replicate": rep, "question_id": q["id"], "call_type": "confidence",
                            "correct": correct, "confidence_value": conf_val,
                            "confidence_raw": conf or "", "prompt_tokens": pt2,
                            "completion_tokens": ct2, "elapsed": elap2,
                        })
                        print(f"  [{call_count}/{total_calls}] conf={conf_val} tok={ct2}")

                        if call_count % 50 == 0:
                            with open(checkpoint, "w") as f:
                                json.dump(results, f, indent=2)
                        time.sleep(0.25)

    with open(checkpoint, "w") as f:
        json.dump(results, f, indent=2)

    # Analysis
    ans_calls = [r for r in results if r["call_type"] == "answer"]
    conf_calls = [r for r in results if r["call_type"] == "confidence"]

    print("\n\n=== IDS INTERVENTION RESULTS ===")
    for model in MODELS:
        for condition in CONDITIONS:
            print(f"\n--- {model} | {condition} ---")
            for budget in BUDGETS:
                rr = [r for r in ans_calls if r["model"] == model and r["condition"] == condition and r["budget"] == budget]
                if not rr: continue
                c = sum(1 for r in rr if r["correct"])
                avg_tok = sum(r["completion_tokens"] for r in rr) / len(rr)
                cc = [r for r in conf_calls if r["model"] == model and r["condition"] == condition and r["budget"] == budget]
                confs = [r["confidence_value"] for r in cc if r["confidence_value"] is not None]
                avg_conf = sum(confs)/len(confs) if confs else 0
                print(f"  Budget {budget}: acc={c}/{len(rr)}={c/len(rr)*100:.1f}% avg_tok={avg_tok:.0f} avg_conf={avg_conf:.0f}")

    print(f"\nDone in {time.time()-start_time:.0f}s")

if __name__ == "__main__":
    main()