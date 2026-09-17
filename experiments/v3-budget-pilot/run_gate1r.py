#!/usr/bin/env python3
"""Gate 1R: Branch protocol smoke test. 5 GPT empty_unfinished cases × 2 branches = ~10 calls."""
import json, os, time, urllib.request, urllib.error, sys
from pathlib import Path
sys.path.insert(0, 'experiments/v3-budget-pilot')
from answer_utils import extract_boxed, is_correct

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")

EMPTY_CASES = [
    "test/counting_and_probability/282.json",
    "test/intermediate_algebra/607.json",
    "test/intermediate_algebra/1000.json",
    "test/prealgebra/378.json",
    "test/intermediate_algebra/1779.json",
]

def load_questions():
    with open('experiments/v3-budget-pilot/data/process_stage2_questions.json') as f:
        data = json.load(f)
    all_qs = []
    for split in data['splits'].values():
        all_qs.extend(split)
    return [q for q in all_qs if q['id'] in EMPTY_CASES]

def call(model, prompt, budget=256):
    think = "low" if model == "GPT-OSS-120B" else False
    payload = {
        "model": "gpt-oss:120b-cloud" if model == "GPT-OSS-120B" else "deepseek-v4-flash:cloud",
        "messages": [{"role": "user", "content": prompt}],
        "think": think,
        "options": {"num_predict": budget, "temperature": 0.7},
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
            msg = body.get("message", {})
            return msg.get("content",""), body.get("eval_count",0), body.get("done_reason"), None
    except Exception as e:
        return "", 0, None, str(e)

def main():
    questions = load_questions()
    results = []
    count = 0
    total = len(questions) * 2 * 2  # 2 budgets × 2 budgets
    
    for q in questions:
        for budget in [128, 256]:
            prompt = f"Solve concisely. Keep reasoning brief. End with \\boxed{{answer}}.\n\n{q['problem']}"
            content, ct, dr, err = call("GPT-OSS-120B", prompt, budget)
            count += 1
            boxed = extract_boxed(content) if content else None
            correct = is_correct(boxed, q['answer']) if boxed else False
            results.append({
                "model": "GPT-OSS-120B", "question_id": q['id'],
                "budget": budget, "content": content[:500],
                "completion_tokens": ct, "done_reason": dr,
                "parsed_answer": boxed or "", "correct": correct,
                "expected_answer": q['answer'], "error": err,
            })
            status = f"{'✓' if boxed else '✗'} parsed={boxed is not None} tok={ct}"
            print(f"[{count}/{total}] GPT b={budget} q={q['id'][:30]} {status}")
            time.sleep(0.3)

    # Summary
    print("\n=== GATE 1R RESULTS ===")
    for budget in [128, 256]:
        rr = [r for r in results if r['budget'] == budget]
        n = len(rr)
        parsed = sum(1 for r in rr if r['parsed_answer'])
        pct = parsed/n*100 if n else 0
        print(f"Budget {budget}: n={n} parsed={parsed}/{n}={pct:.0f}%")

    out = RESULTS_DIR / "process_stage2_gate1r.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out}")

if __name__ == "__main__":
    main()