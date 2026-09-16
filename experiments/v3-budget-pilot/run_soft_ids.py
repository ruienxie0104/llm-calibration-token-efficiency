#!/usr/bin/env python3
"""
Soft + IDS Experiment.
Combines soft constraint (prompt budget) with IDS (difficulty signal).

Conditions:
- Soft QOQ: budget instruction only (already have this from soft pilot)
- Soft IDS: budget instruction + difficulty signal (new)

Total new calls: 2 models × 1 condition × 2 budgets × 3 reps × 30 questions × 2 = 360 calls
(Soft QOQ already exists from soft pilot)
"""
import json, os, time, urllib.request, urllib.error, re, random, math
from pathlib import Path
from collections import Counter, defaultdict

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")

MODELS = ["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"]
MODEL_MAP = {
    "GPT-OSS-20B": "gpt-oss:20b-cloud",
    "GPT-OSS-120B": "gpt-oss:120b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
    "GLM-5.2-756B": "glm-5.2:cloud",
}
BUDGETS = [256, 512]
REPLICATES = 3
SEED = 42
QUESTIONS = 30

LEVELS = {1: "very easy", 2: "easy", 3: "moderate", 4: "difficult", 5: "very difficult"}

def load_questions():
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    candidates = [q for q in pool if q["level"] in [3, 4]]
    return rng.sample(candidates, QUESTIONS)

def compute_difficulty(questions):
    # Load IRT beta from Phase 3
    irt_path = RESULTS_DIR / "irt_phase3.json"
    if not irt_path.exists():
        for q in questions:
            q["beta"] = 3; q["beta_label"] = "moderate"
        return
    with open(irt_path) as f:
        irt = json.load(f)
    beta_all = irt.get("beta", {})
    vals = [float(v) for v in beta_all.values()]
    min_b, max_b = min(vals), max(vals)
    for q in questions:
        b = float(beta_all.get(q["id"], 0))
        l = round((b - min_b) / (max_b - min_b) * 4 + 1)
        l = max(1, min(5, l))
        q["beta"] = l
        q["beta_label"] = LEVELS[l]
    print("Difficulty dist:", dict(Counter(q["beta"] for q in questions)))

def make_prompt(problem, budget, beta_label=""):
    prompt = problem
    if beta_label:
        prompt = f"This problem is rated {beta_label}.\n\n{prompt}"
    return f"Please complete your reasoning within approximately {budget} tokens, then give the final answer in \\boxed{{}}.\n\n{prompt}"

def call_ollama(model_name, messages):
    payload = {"model": MODEL_MAP[model_name], "messages": messages, "stream": False}
    payload["options"] = {"num_predict": 4096, "temperature": 0.0}
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
    a = re.sub(r'\\[a-z]+', '', a.strip()); a = re.sub(r'[{}]', '', a)
    return a.replace(' ', '').lower()

def is_correct(pred, exp):
    if not pred: return False
    if normalize(pred) == normalize(exp): return True
    try:
        import ast
        def safe_eval(s):
            s = s.replace('\\frac','').replace('{','(').replace('}',')').replace('\\pi','3.14159')
            t = ast.parse(s, mode='eval')
            for n in ast.walk(t):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)):
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

def main():
    questions = load_questions()
    compute_difficulty(questions)
    with open(DATA_DIR / "soft_ids_questions.json", "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Loaded {len(questions)} questions")

    total_calls = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES * 2
    print(f"Soft IDS only: {total_calls} calls ({total_calls//2} answer + {total_calls//2} confidence)")
    print()

    checkpoint = RESULTS_DIR / "soft_ids_raw.json"
    existing = []
    if checkpoint.exists():
        try:
            with open(checkpoint) as f:
                existing = json.load(f)
            print(f"Checkpoint: {len(existing)} calls")
        except: pass

    done_set = set()
    for r in existing:
        done_set.add((r["model"], r["budget"], r["replicate"], r["question_id"], r["call_type"]))

    results = list(existing)
    call_count = len(existing)
    start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    ak = (model, budget, rep, q["id"], "answer")
                    if ak in done_set:
                        continue
                    call_count += 1
                    prompt = make_prompt(q["problem"], budget, q.get("beta_label", ""))
                    msg = [{"role": "user", "content": prompt}]
                    content, pt, ct, elap, err = call_ollama(model, msg)
                    if err:
                        print(f"[{call_count}/{total_calls}] ERR: {err}")
                        continue
                    boxed = extract_boxed(content) if content else None
                    correct = is_correct(boxed, q["answer"])
                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"],
                        "subject": q["subject"], "call_type": "answer",
                        "prompt_type": "soft_ids", "ids_level": q.get("beta"),
                        "prompt": prompt[:200], "response": content[:500],
                        "prompt_tokens": pt, "completion_tokens": ct,
                        "correct": correct, "parsed_answer": boxed or "",
                        "expected_answer": q["answer"], "elapsed": elap,
                    })
                    print(f"[{call_count}/{total_calls}] {model} b={budget} r={rep} {'✓' if correct else '✗'} tok={ct}", end="")

                    ck = (model, budget, rep, q["id"], "confidence")
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
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "call_type": "confidence",
                        "prompt_type": "soft_ids", "ids_level": q.get("beta"),
                        "correct": correct, "confidence_value": conf_val,
                        "confidence_raw": conf or "", "prompt_tokens": pt2,
                        "completion_tokens": ct2, "elapsed": elap2,
                    })
                    print(f" conf={conf_val} tok={ct2}")

                    if call_count % 50 == 0:
                        with open(checkpoint, "w") as f:
                            json.dump(results, f, indent=2)
                    time.sleep(0.25)

    with open(checkpoint, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDone in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()