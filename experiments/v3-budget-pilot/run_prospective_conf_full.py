#!/usr/bin/env python3
"""
Prospective Confidence Full Experiment (360 calls).
Uses improved prompt + API settings validated by smoke test.
"""
import json, os, time, urllib.request, urllib.error, re, random
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")

MODELS = ["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"]
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud", "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud"}
THINK_SETTINGS = {"GPT-OSS-120B": "low", "DeepSeek-V4-Flash-158B": False}
BUDGETS = [256, 512]
REPLICATES = 3
QUESTIONS = 30
SEED = 42

def load_questions():
    rng = random.Random(SEED)
    with open(DATA_DIR / "phase3_questions.json") as f:
        pool = json.load(f)
    return rng.sample([q for q in pool if q["level"] in [3, 4]], QUESTIONS)

def call_ollama(model, messages):
    think = THINK_SETTINGS[model]
    payload = {
        "model": MODEL_MAP[model], "messages": messages,
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
                "content": msg.get("content", ""), "thinking": msg.get("thinking", ""),
                "done_reason": body.get("done_reason"),
                "prompt_tokens": body.get("prompt_eval_count", 0),
                "completion_tokens": body.get("eval_count", 0), "error": None,
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
    fb = re.search(r"CONFIDENCE\s*[:=]\s*(\d{1,3})", content.strip(), flags=re.IGNORECASE)
    if fb:
        v = int(fb.group(1))
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
    total = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    print(f"Total: {total} calls (2 models × 2 budgets × 3 reps × 30 questions)")
    
    chk = RESULTS_DIR / "prospective_conf_full.json"
    existing = []
    if chk.exists():
        with open(chk) as f: existing = json.load(f)
        print(f"Checkpoint: {len(existing)} calls")
    done = set((r["model"], r["budget"], r["replicate"], r["question_id"]) for r in existing)
    results = list(existing)
    count = len(existing); start = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    if (model, budget, rep, q["id"]) in done: continue
                    count += 1
                    prompt = PROMPT_TEMPLATE.format(budget=budget, problem=q["problem"])
                    msg = [{"role": "user", "content": prompt}]
                    resp = call_ollama(model, msg)
                    conf, exact = parse_confidence(resp["content"])
                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"],
                        "prospective_confidence": conf, "exact_format": exact,
                        "content": resp["content"], "thinking": resp["thinking"],
                        "thinking_chars": len(resp.get("thinking", "")),
                        "done_reason": resp["done_reason"],
                        "prompt_tokens": resp["prompt_tokens"],
                        "completion_tokens": resp["completion_tokens"],
                        "error": resp["error"],
                    })
                    print(f"[{count}/{total}] {model} b={budget} r={rep} {'✓' if conf else '✗'} conf={conf} tok={resp['completion_tokens']}")
                    if count % 50 == 0:
                        with open(chk, "w") as f: json.dump(results, f, indent=2)
                    time.sleep(0.2)

    with open(chk, "w") as f: json.dump(results, f, indent=2)
    
    # Summary
    for model in MODELS:
        rr = [r for r in results if r["model"] == model]
        valid = [r for r in rr if r["prospective_confidence"] is not None]
        n = len(rr)
        print(f"\n--- {model} ({n} calls) ---")
        print(f"  Parse rate:   {len(valid)/n:.0%}")
        print(f"  Exact format: {sum(1 for r in rr if r['exact_format'])/n:.0%}")
        print(f"  Length stop:  {sum(1 for r in rr if r['done_reason']=='length')/n:.0%}")
        if valid:
            vals = [r["prospective_confidence"] for r in valid]
            print(f"  Conf values:  {sorted(set(vals))}")
            print(f"  Mean conf:    {sum(vals)/len(vals):.1f}")
        thinkers = [r for r in rr if r["thinking_chars"] > 0]
        if thinkers:
            avg_t = sum(r["thinking_chars"] for r in thinkers) / len(thinkers)
            print(f"  Thinking (avg chars): {avg_t:.0f}")
    
    print(f"\nDone in {time.time()-start:.0f}s")

if __name__ == "__main__":
    main()