#!/usr/bin/env python3
"""
Budget-range pilot: scan 6 Soft budget levels to find effective L/H pair.
1 model × 30 questions × 6 budgets × 2 reps = 360 answer calls.
NO confidence calls — this round only checks whether Soft can control cost.
"""
import json, os, time, urllib.request, urllib.error, re, random
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")

MODELS = ["GPT-OSS-120B"]
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud"}
BUDGETS = [64, 128, 256, 512, 1024, 2048]
REPLICATES = 2
SEED = 42
QUESTIONS = 30

def load_questions():
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    return rng.sample([q for q in pool if q["level"] in [3, 4]], QUESTIONS)

def call_ollama(model, problem, budget):
    prompt = f"Please complete your reasoning within approximately {budget} tokens, then give the final answer in \\boxed{{}}.\n\n{problem}"
    payload = {
        "model": MODEL_MAP[model],
        "messages": [{"role": "user", "content": prompt}],
        "options": {"num_predict": 4096, "temperature": 0.0},
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
            content = body.get("message", {}).get("content", "")
            pt = body.get("prompt_eval_count", 0)
            ct = body.get("eval_count", 0)
            return content, pt, ct, prompt, None
    except urllib.error.HTTPError as e:
        return None, 0, 0, "", f"HTTP {e.code}"
    except Exception as e:
        return None, 0, 0, "", str(e)

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
        def safe(s):
            s = s.replace('\\frac','').replace('{','(').replace('}',')').replace('\\pi','3.14159')
            t = ast.parse(s, mode='eval')
            for n in ast.walk(t):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub,
                                      ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)): return None
            return eval(compile(t, '', 'eval'))
        pv, ev = safe(pred), safe(exp)
        if pv is not None and ev is not None and abs(pv-ev) < 1e-6: return True
    except: pass
    return False

def main():
    questions = load_questions()
    total = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    print(f"Total: {total} answer calls (no confidence calls)")

    chk = RESULTS_DIR / "budget_range_raw.json"
    existing = []
    if chk.exists():
        with open(chk) as f: existing = json.load(f)
        print(f"Checkpoint: {len(existing)} calls")
    done = set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in existing)
    results = list(existing)
    count = len(existing)
    start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    key = (model, budget, rep, q["id"])
                    if key in done: continue
                    count += 1
                    content, pt, ct, prompt, err = call_ollama(model, q["problem"], budget)
                    if err:
                        print(f"[{count}/{total}] ERR: {err}")
                        continue
                    boxed = extract_boxed(content) if content else None
                    correct = is_correct(boxed, q["answer"])
                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"],
                        "prompt": prompt[:200],
                        "content": content[:500],  # Full content saved for PM analysis
                        "full_content": content,   # Store full response
                        "prompt_tokens": pt, "completion_tokens": ct,
                        "correct": correct, "parsed_answer": boxed or "",
                        "expected_answer": q["answer"],
                    })
                    print(f"[{count}/{total}] {model} b={budget} r={rep} {'✓' if correct else '✗'} tok={ct}")
                    if count % 50 == 0:
                        with open(chk, "w") as f: json.dump(results, f, indent=2)
                    time.sleep(0.25)

    with open(chk, "w") as f: json.dump(results, f, indent=2)
    print(f"\nDone in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()