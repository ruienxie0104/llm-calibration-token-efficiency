#!/usr/bin/env python3
"""B: Confidence test — verify confidence prompt works under budget constraints.
2 models × 10 questions (L3+L4) × 2 budgets × 1 rep = 40 answer calls + 40 confidence calls.
"""
import json, os, time, urllib.request, urllib.error, re
from pathlib import Path
from datasets import load_dataset

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")

MODEL_MAP = {
    "GPT-OSS-20B": "gpt-oss:20b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
}
MODELS = ["GPT-OSS-20B", "DeepSeek-V4-Flash-158B"]
BUDGETS = [256, 512]
SEED = 42

def load_questions():
    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    rng = __import__("random").Random(SEED)
    selected = []
    for level in [3, 4]:
        candidates = [d for d in ds if d["level"] == level]
        chosen = rng.sample(candidates, 5)  # 5 per level
        selected.extend([{
            "id": d["unique_id"], "problem": d["problem"],
            "answer": d["answer"], "level": d["level"], "subject": d["subject"]
        } for d in chosen])
    return selected

def call_ollama(model, messages, max_tokens=0):
    """Call Ollama. If max_tokens > 0, apply budget limit."""
    payload = {
        "model": MODEL_MAP[model],
        "messages": messages,
        "stream": False,
    }
    if max_tokens > 0:
        payload["options"] = {"num_predict": max_tokens, "temperature": 0.0}

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            return content, prompt_tokens, completion_tokens, None
    except urllib.error.HTTPError as e:
        return None, 0, 0, f"HTTP {e.code}"
    except Exception as e:
        return None, 0, 0, str(e)

def extract_boxed(text):
    if not text: return None
    m = re.findall(r'\\boxed\{(.*?)\}', text, re.DOTALL)
    return m[-1].strip() if m else None

def normalize(a):
    if not a: return ""
    a = re.sub(r'\\[a-z]+', '', a.strip())
    a = re.sub(r'[{}]', '', a)
    return a.replace(' ', '').lower()

def is_correct(p, e):
    if not p: return False
    if normalize(p) == normalize(e): return True
    try:
        import ast
        def safe(s):
            s = s.replace('\\frac','').replace('{','(').replace('}',')').replace('\\pi','3.14159')
            t = ast.parse(s, mode='eval')
            for n in ast.walk(t):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)):
                    return None
            return eval(compile(t, '', 'eval'))
        pv, ev = safe(p), safe(e)
        if pv is not None and ev is not None and abs(pv - ev) < 1e-6: return True
    except: pass
    return False

def main():
    questions = load_questions()
    all_results = []
    total_calls = len(questions) * len(MODELS) * len(BUDGETS)
    call_n = 0
    start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for q in questions:
                call_n += 1
                # --- Step 1: Answer call with budget ---
                print(f"[{call_n}/{total_calls}] {model} b={budget} q={q['id']} (L{q['level']})", end=" ... ", flush=True)
                msg = [{"role": "user", "content": f"Solve the math problem step by step, then give the final answer in \\boxed{{}}.\n\n{q['problem']}"}]
                ans, pt, ct, err = call_ollama(model, msg, max_tokens=budget)
                if err:
                    print(f"ERROR: {err}")
                    continue

                boxed = extract_boxed(ans) if ans else None
                correct = is_correct(boxed, q["answer"])

                # --- Step 2: Confidence call (no budget limit) ---
                conf_msg = [
                    {"role": "user", "content": f"Solve the math problem step by step, then give the final answer in \\boxed{{}}.\n\n{q['problem']}"},
                    {"role": "assistant", "content": ans},
                    {"role": "user", "content": f"Based on your reasoning above, how confident are you that your answer is correct? Give ONLY a single number from 0 to 100. Do not include any other text."},
                ]
                conf, pt2, ct2, err2 = call_ollama(model, conf_msg)
                # Parse confidence number
                conf_val = None
                if conf:
                    nums = re.findall(r'(\d+)', conf.strip())
                    if nums:
                        conf_val = min(100, max(0, int(nums[0])))

                print(f"acc={'✓' if correct else '✗'} conf={conf_val} tok={ct}/{pt+ct2}")
                
                all_results.append({
                    "model": model, "budget": budget,
                    "question_id": q["id"], "level": q["level"],
                    "subject": q["subject"],
                    "correct": correct, "parsed_answer": boxed or "",
                    "expected_answer": q["answer"],
                    "confidence_raw": conf or "",
                    "confidence_value": conf_val,
                    "answer_tokens": ct,
                    "conf_prompt_tokens": pt2,
                    "conf_completion_tokens": ct2,
                })

                # Incremental save
                if call_n % 10 == 0:
                    with open(RESULTS_DIR / "confidence_test.json", "w") as f:
                        json.dump(all_results, f, indent=2)

                time.sleep(0.3)

    # Final save
    with open(RESULTS_DIR / "confidence_test.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Summary
    print("\n\n=== CONFIDENCE TEST RESULTS ===")
    for model in MODELS:
        print(f"\n--- {model} ---")
        for budget in BUDGETS:
            rr = [r for r in all_results if r["model"] == model and r["budget"] == budget]
            n = len(rr)
            c = sum(1 for r in rr if r["correct"])
            confs = [r["confidence_value"] for r in rr if r["confidence_value"] is not None]
            avg_conf = sum(confs) / len(confs) if confs else 0
            correct_confs = [r["confidence_value"] for r in rr if r["correct"] and r["confidence_value"] is not None]
            wrong_confs = [r["confidence_value"] for r in rr if not r["correct"] and r["confidence_value"] is not None]
            avg_c = sum(correct_confs) / len(correct_confs) if correct_confs else 0
            avg_w = sum(wrong_confs) / len(wrong_confs) if wrong_confs else 0
            print(f"  Budget {budget}: acc={c}/{n}={c/n*100:.0f}% avg_conf={avg_conf:.0f} correct_conf={avg_c:.0f} wrong_conf={avg_w:.0f}")

    print(f"\nDone in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()