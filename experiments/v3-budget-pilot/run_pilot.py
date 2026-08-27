#!/usr/bin/env python3
"""V3 Budget Sensitivity Pilot: MATH-500 Level 3-5, 2 models, 4 budgets, 2 reps."""
import json
import os
import sys
import time
import random
import re
import urllib.request
import urllib.error
from pathlib import Path

from datasets import load_dataset

# --- Config ---
DATA_DIR = Path("experiments/v3-budget-pilot/data")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    "GPT-OSS-20B",
    "DeepSeek-V4-Flash-158B"
]

BUDGETS = [128, 256, 512, 1024]

REPLICATES = 2
SEED = 42
QUESTIONS_PER_LEVEL = 10  # Level 3, 4, 5 each → 30 total
MAX_LEVELS = [3, 4, 5]

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")

MODEL_MAP = {
    "GPT-OSS-20B": "gpt-oss:20b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
}

# --- Load and sample questions ---
def load_questions():
    rng = random.Random(SEED)
    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    selected = []
    for level in MAX_LEVELS:
        candidates = [d for d in ds if d["level"] == level]
        chosen = rng.sample(candidates, QUESTIONS_PER_LEVEL)
        for c in chosen:
            selected.append({
                "id": c["unique_id"],
                "problem": c["problem"],
                "answer": c["answer"],
                "level": c["level"],
                "subject": c["subject"],
            })
    return selected

# --- Ollama API call ---
def call_ollama(model_name, problem, max_tokens):
    """Call Ollama with budget control via num_predict."""
    payload = json.dumps({
        "model": MODEL_MAP[model_name],
        "messages": [
            {
                "role": "user",
                "content": f"Solve the following math problem step by step, then give the final answer in \\boxed{{}}.\n\n{problem}"
            }
        ],
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.0
        },
        "stream": False
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OLLAMA_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            return content, prompt_tokens, completion_tokens
    except Exception:
        return None, 0, 0

# --- Answer parsing ---
def extract_boxed(text):
    """Extract content from \\boxed{...}."""
    if not text:
        return None
    matches = re.findall(r'\\boxed\{(.*?)\}', text, re.DOTALL)
    if matches:
        return matches[-1].strip()
    return None

def normalize_answer(ans):
    """Normalize answer for comparison (remove spaces, lower)."""
    if not ans:
        return ""
    ans = ans.strip()
    ans = re.sub(r'\\[a-z]+', '', ans)
    ans = re.sub(r'[{}]', '', ans)
    ans = ans.replace(' ', '').lower()
    return ans

def is_correct(predicted, expected):
    """Compare predicted vs expected answer."""
    if not predicted:
        return False
    p_norm = normalize_answer(predicted)
    e_norm = normalize_answer(expected)
    if p_norm == e_norm:
        return True
    # Try numeric comparison
    try:
        import ast
        def safe_eval(expr):
            expr = re.sub(r'\\boxed\{\s*', '', expr)
            expr = re.sub(r'\s*\}', '', expr)
            expr = expr.replace('\\frac', '').replace('{', '(').replace('}', ')')
            expr = expr.replace('\\pi', str(3.141592653589793))
            tree = ast.parse(expr, mode='eval')
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Expression, ast.Constant,
                                         ast.Add, ast.Sub, ast.Mult, ast.Div,
                                         ast.Pow, ast.UnaryOp, ast.USub,
                                         ast.BinOp)):
                    return False
            return eval(compile(tree, '', 'eval'))
        p_val = safe_eval(predicted)
        e_val = safe_eval(expected)
        if abs(p_val - e_val) < 1e-6:
            return True
    except:
        pass
    return False

# --- Main ---
def main():
    # Load existing results if resuming
    start_results = []
    checkpoint_path = RESULTS_DIR / "results_incremental.json"
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path) as f:
                start_results = json.load(f)
            print(f"Resuming from checkpoint: {len(start_results)} existing results")
        except:
            pass
    
    questions = load_questions()
    with open(DATA_DIR / "sampled_questions.json", "w") as f:
        json.dump(questions, f, indent=2)

    print(f"Loaded {len(questions)} questions")
    print(f"Levels: {sorted([q['level'] for q in questions])}")

    total_calls = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    print(f"Total API calls: {total_calls}")
    print()

    # Build set of already-done calls
    done_set = set()
    for r in start_results:
        key = (r["model"], r["budget"], r["replicate"], r["question_id"])
        done_set.add(key)
    
    results = list(start_results)
    call_count = len(start_results)
    start_time = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    key = (model, budget, rep, q["id"])
                    if key in done_set:
                        continue
                    call_count += 1
                    remaining = total_calls - len(done_set)
                    elapsed = time.time() - start_time
                    rate = call_count / elapsed if elapsed > 0 else 0
                    rate = (call_count - len(start_results)) / elapsed if elapsed > 0 else 0  # rate since resume
                    eta = remaining / rate if rate > 0 else 0
                    done_now = call_count - len(start_results)
                    pct = done_now / remaining * 100 if remaining > 0 else 0

                    print(f"[resume {done_now}/{remaining}] {model} | b={budget} | r={rep} | q{q['id']}(L{q['level']}) | ETA:{eta:.0f}s")

                    content, prompt_tok, comp_tok = call_ollama(model, q["problem"], budget)

                    boxed = extract_boxed(content) if content else None
                    correct = is_correct(boxed, q["answer"])

                    result = {
                        "model": model,
                        "budget": budget,
                        "replicate": rep,
                        "question_id": q["id"],
                        "level": q["level"],
                        "subject": q["subject"],
                        "prompt_tokens": prompt_tok,
                        "completion_tokens": comp_tok,
                        "correct": correct,
                        "parsed_answer": boxed or "",
                        "expected_answer": q["answer"],
                        "content_preview": (content[:200] + "...") if content and len(content) > 200 else (content or ""),
                        "truncated": comp_tok >= (budget * 0.9) if comp_tok else False,
                    }
                    results.append(result)

                    # Incremental save every 10 calls
                    if call_count % 10 == 0:
                        with open(RESULTS_DIR / "results_incremental.json", "w") as f:
                            json.dump(results, f, indent=2)

                    time.sleep(0.3)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    for model in MODELS:
        print(f"\n--- {model} ---")
        mr = [r for r in results if r["model"] == model]
        for budget in BUDGETS:
            br = [r for r in mr if r["budget"] == budget]
            total = len(br)
            correct = sum(1 for r in br if r["correct"])
            avg_tok = sum(r["completion_tokens"] for r in br) / total if total else 0
            truncated = sum(1 for r in br if r["truncated"])
            print(f"  Budget {budget:5d}: acc={correct}/{total}={correct/total*100:.1f}% | avg_tok={avg_tok:.0f} | truncated={truncated}")

    # Final save
    with open(RESULTS_DIR / "results_final.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {RESULTS_DIR / 'results_final.json'}")

    # Go/No-Go: are low budgets saturated?
    print("\n--- Go/No-Go ---")
    saturated = True
    for budget in [128, 256]:
        for model in MODELS:
            br = [r for r in results if r["model"] == model and r["budget"] == budget]
            acc = sum(1 for r in br if r["correct"]) / len(br) if br else 1
            flag = "SATURATED" if acc >= 0.9 else "OK"
            print(f"  {model} @ {budget}: {acc*100:.1f}% [{flag}]")
            if acc >= 0.9:
                saturated = saturated and True

    if saturated:
        print("\n⚠️  No-Go: Too easy, need harder questions")
    else:
        print("\n✅ Go: Budget sensitivity detected, proceed to Phase 3")

    print(f"\nDone. {call_count} calls in {time.time()-start_time:.0f}s")

if __name__ == "__main__":
    main()