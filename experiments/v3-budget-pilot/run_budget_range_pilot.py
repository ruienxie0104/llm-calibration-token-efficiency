#!/usr/bin/env python3
"""
Budget-range pilot: scan 6 Soft budget levels. 360 answer calls, no confidence.
"""
import json, os, time, urllib.request, urllib.error, re, random, sys
from pathlib import Path
sys.path.insert(0, 'experiments/v3-budget-pilot')
from answer_utils import extract_boxed, is_correct

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")
MODELS = ["GPT-OSS-120B"]
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud"}
BUDGETS = [64, 128, 256, 512, 1024, 2048]
REPLICATES = 2; SEED = 42; QUESTIONS = 30

def load_questions():
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    return rng.sample([q for q in pool if q["level"] in [3, 4]], QUESTIONS)

def call_ollama(model, problem, budget):
    prompt = f"Please complete your reasoning within approximately {budget} tokens, then give the final answer in \\boxed{{}}.\n\n{problem}"
    payload = {"model": MODEL_MAP[model], "messages": [{"role": "user", "content": prompt}],
               "options": {"num_predict": 4096, "temperature": 0.0}, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
            msg = body.get("message", {})
            return (msg.get("content", ""), body.get("prompt_eval_count", 0),
                    body.get("eval_count", 0), body.get("done_reason"), prompt, None)
    except Exception as e:
        return None, 0, 0, None, "", str(e)

def main():
    questions = load_questions()
    total = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    print(f"Total: {total} answer calls")
    
    chk = RESULTS_DIR / "budget_range_raw.json"
    existing = []
    if chk.exists():
        with open(chk) as f: existing = json.load(f)
        print(f"Checkpoint: {len(existing)} calls")
    done = set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in existing)
    results = list(existing); count = len(existing); start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    key = (model, budget, rep, q["id"])
                    if key in done: continue
                    count += 1
                    content, pt, ct, dr, prompt, err = call_ollama(model, q["problem"], budget)
                    if err:
                        print(f"[{count}/{total}] ERR: {err}"); continue
                    boxed = extract_boxed(content) if content else None
                    correct = is_correct(boxed, q["answer"])
                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"],
                        "prompt": prompt[:200], "content": content,
                        "prompt_tokens": pt, "completion_tokens": ct,
                        "done_reason": dr, "correct": correct,
                        "parsed_answer": boxed or "", "expected_answer": q["answer"],
                    })
                    # Atomic checkpoint after every call
                    tmp = chk.with_suffix(".tmp")
                    with open(tmp, "w") as f: json.dump(results, f, indent=2)
                    tmp.replace(chk)
                    print(f"[{count}/{total}] {model} b={budget} r={rep} {'✓' if correct else '✗'} tok={ct} {dr if dr else ''}")
                    time.sleep(0.25)

    # Verify completeness
    observed = len(set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in results))
    if observed != total:
        print(f"ERROR: Expected {total} calls, got {observed}")
        for model in MODELS:
            for budget in BUDGETS:
                for rep in range(1, REPLICATES + 1):
                    for q in questions:
                        if (model, budget, rep, q["id"]) not in set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in results):
                            print(f"  MISSING: {model} b={budget} r={rep} q={q['id']}")
        sys.exit(1)
    print(f"\nDone. {observed}/{total} calls in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()