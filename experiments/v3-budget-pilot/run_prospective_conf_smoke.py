#!/usr/bin/env python3
"""
Prospective Confidence Smoke Test (20 calls).
Tests whether confidence can be reliably extracted with higher num_predict + think settings.
"""
import json, os, time, urllib.request, urllib.error, re
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"]
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud", "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud"}
THINK_SETTINGS = {"GPT-OSS-120B": "low", "DeepSeek-V4-Flash-158B": False}
BUDGETS = [256, 512]
SMOKE_QUESTIONS = 5
SEED = 42

def load_questions():
    import random
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    return rng.sample([q for q in pool if q["level"] in [3, 4]], SMOKE_QUESTIONS)

def call_ollama(model, messages):
    think = THINK_SETTINGS[model]
    payload = {
        "model": MODEL_MAP[model],
        "messages": messages,
        "think": think,
        "options": {"num_predict": 256, "temperature": 0.0},
        "stream": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
            msg = body.get("message", {})
            return {
                "content": msg.get("content", ""),
                "thinking": msg.get("thinking", ""),
                "done_reason": body.get("done_reason"),
                "prompt_tokens": body.get("prompt_eval_count", 0),
                "completion_tokens": body.get("eval_count", 0),
                "error": None,
            }
    except Exception as e:
        return {"content": "", "thinking": "", "done_reason": None,
                "prompt_tokens": 0, "completion_tokens": 0, "error": str(e)}

def parse_confidence(content):
    if not content: return None, False
    exact = re.fullmatch(r"CONFIDENCE\s*=\s*(\d{1,3})", content.strip(), flags=re.IGNORECASE)
    if exact:
        v = int(exact.group(1))
        if 0 <= v <= 100: return v, True
    fallback = re.search(r"CONFIDENCE\s*[:=]\s*(\d{1,3})", content.strip(), flags=re.IGNORECASE)
    if fallback:
        v = int(fallback.group(1))
        if 0 <= v <= 100: return v, False
    return None, False

PROMPT_TEMPLATE = """You will later solve the following math problem under an approximate reasoning budget of {budget} tokens.

Do not solve the problem now. Make only a quick estimate of your probability of eventually producing the correct final answer.

Your visible response must contain exactly one line in this format:

CONFIDENCE=<integer from 0 to 100>

Do not include explanations, words, Markdown, or the solution in the visible response.

Problem:
{problem}"""

def main():
    questions = load_questions()
    results = []
    total = len(questions) * len(MODELS) * len(BUDGETS)
    count = 0
    start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for q in questions:
                count += 1
                prompt = PROMPT_TEMPLATE.format(budget=budget, problem=q["problem"])
                msg = [{"role": "user", "content": prompt}]
                resp = call_ollama(model, msg)
                conf, exact = parse_confidence(resp["content"])
                results.append({
                    "model": model, "budget": budget, "question_id": q["id"],
                    "prospective_confidence": conf, "exact_format": exact,
                    "content": resp["content"], "thinking": resp["thinking"],
                    "thinking_chars": len(resp.get("thinking", "")),
                    "done_reason": resp["done_reason"],
                    "prompt_tokens": resp["prompt_tokens"],
                    "completion_tokens": resp["completion_tokens"],
                    "error": resp["error"],
                })
                status = f"{'✓' if conf is not None else '✗'} conf={conf} exact={exact} done={resp['done_reason']} tok={resp['completion_tokens']}"
                print(f"[{count}/{total}] {model} b={budget} q={q['id'][:20]} {status}")
                time.sleep(0.3)

    # Save
    out_path = RESULTS_DIR / "prospective_conf_smoke.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary per model
    print("\n=== SMOKE TEST RESULTS ===")
    for model in MODELS:
        rr = [r for r in results if r["model"] == model]
        valid = [r for r in rr if r["prospective_confidence"] is not None]
        n = len(rr)
        parse_rate = len(valid) / n
        exact_rate = sum(1 for r in rr if r["exact_format"]) / n
        empty_rate = sum(1 for r in rr if not r["content"].strip()) / n
        length_stop = sum(1 for r in rr if r["done_reason"] == "length") / n
        print(f"\n--- {model} ---")
        print(f"  Parse rate:         {parse_rate:.0%} ({len(valid)}/{n})")
        print(f"  Exact-format rate:  {exact_rate:.0%}")
        print(f"  Empty-content rate: {empty_rate:.0%}")
        print(f"  Length-stop rate:   {length_stop:.0%}")
        if valid:
            vals = [r["prospective_confidence"] for r in valid]
            print(f"  Confidence values:  {sorted(set(vals))}")
            print(f"  Mean confidence:    {sum(vals)/len(vals):.1f}")
        if any(r["thinking_chars"] > 0 for r in rr):
            avg_thinking = sum(r["thinking_chars"] for r in rr) / n
            print(f"  Avg thinking chars: {avg_thinking:.0f}")
        # Check for answer leakage
        leaked = sum(1 for r in rr if "boxed" in r.get("content", "").lower())
        if leaked > 0:
            print(f"  ⚠️  Answer leaked in content: {leaked}/{n}")

    print(f"\nDone in {time.time()-start:.0f}s. Saved to {out_path}")

if __name__ == "__main__":
    main()