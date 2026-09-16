#!/usr/bin/env python3
"""
Prospective Confidence Pilot.
Ask confidence BEFORE reasoning (independent context), then match with existing Soft QOQ answers.
2 models × 30 questions × 2 budgets × 3 reps = 360 confidence calls (no answer calls needed).
"""
import json, os, time, urllib.request, urllib.error, re, random, math
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")

MODELS = ["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"]
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud", "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud"}
BUDGETS = [256, 512]
REPLICATES = 3
SEED = 42
QUESTIONS = 30

def load_questions():
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    return rng.sample([q for q in pool if q["level"] in [3, 4]], QUESTIONS)

def call_ollama(model, msg):
    payload = {"model": MODEL_MAP[model], "messages": msg, "options": {"num_predict": 64, "temperature": 0.0}, "stream": False}
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            content = body.get("message", {}).get("content", "")
            pt = body.get("prompt_eval_count", 0)
            ct = body.get("eval_count", 0)
            return content, pt, ct, None
    except Exception as e:
        return None, 0, 0, str(e)

def parse_confidence(text):
    if not text: return None
    nums = re.findall(r'(\d+)', text.strip())
    return min(100, max(0, int(nums[0]))) if nums else None

def main():
    questions = load_questions()
    print(f"Loaded {len(questions)} questions")
    total = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    print(f"Total: {total} prospective confidence calls")
    
    chk = RESULTS_DIR / "prospective_conf_raw.json"
    existing = []
    if chk.exists():
        with open(chk) as f: existing = json.load(f)
        print(f"Checkpoint: {len(existing)} calls")
    done = set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in existing)
    results = list(existing)
    count = len(existing)
    start = time.time()
    
    PROMPT_TEMPLATE = "You are about to solve a math problem. Without solving it yet, what is your best estimate of how likely you are to answer correctly?\nGive ONLY a single number from 0 to 100 (where 0 = definitely wrong, 100 = definitely correct).\n\n{budget_ctx}Problem: {problem}"
    
    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    if (model, budget, rep, q["id"]) in done: continue
                    count += 1
                    budget_ctx = f"You need to solve this within approximately {budget} tokens.\n\n" if budget else ""
                    prompt = PROMPT_TEMPLATE.format(budget_ctx=budget_ctx, problem=q["problem"])
                    msg = [{"role": "user", "content": prompt}]
                    conf_text, pt, ct, err = call_ollama(model, msg)
                    conf_val = parse_confidence(conf_text)
                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "prospective_confidence": conf_val,
                        "prompt_tokens": pt, "completion_tokens": ct, "error": err,
                        "raw_response": conf_text[:100] if conf_text else ""
                    })
                    if count % 50 == 0:
                        with open(chk, "w") as f: json.dump(results, f, indent=2)
                    print(f"[{count}/{total}] {model} b={budget} r={rep} conf={conf_val}")
                    time.sleep(0.25)
    
    with open(chk, "w") as f: json.dump(results, f, indent=2)
    print(f"\nDone in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()