#!/usr/bin/env python3
"""Re-run confidence assessment with conversation context.
Only re-calls the confidence step (not the answer step). 
Saves to raw_responses_v2.json to preserve original data.
"""
import json, os, sys, time, re, urllib.request, urllib.error
from confidence_utils import make_confidence_prompt_with_context
warnings = sys.modules.get('warnings')
if warnings:
    import warnings as w
    w.filterwarnings("ignore")

API_KEY = os.getenv("OLLAMA_API_KEY")
API_URL = os.getenv("OLLAMA_API_URL", "https://ollama.com/api/chat")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "results")
OUTPUT_FILE = f"{INPUT_DIR}/raw_responses_v2.json"

MODELS = [
    ("gpt-oss:20b-cloud", "GPT-OSS-20B"),
    ("deepseek-v4-flash:cloud", "DeepSeek-V4-Flash-158B"),
    ("gpt-oss:120b-cloud", "GPT-OSS-120B"),
    ("glm-5.2:cloud", "GLM-5.2-756B"),
]

def call_ollama_api(model, messages, timeout=120):
    """Call ollama cloud via HTTP API with multi-turn messages."""
    if not API_KEY:
        return {
            "response": "",
            "elapsed": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error": "OLLAMA_API_KEY is not set",
        }

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()
    
    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    })
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            elapsed = time.time() - start
            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            return {
                "response": content,
                "elapsed": elapsed,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read().decode() if e.readable() else ""
        return {"response": "", "elapsed": elapsed, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        elapsed = time.time() - start
        return {"response": "", "elapsed": elapsed, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "error": str(e)}

def extract_confidence(response):
    """Extract confidence score from response — improved version."""
    # Try common patterns first
    # "Confidence: 85" or "85%" or "I am 85% confident"
    patterns = [
        r'[Cc]onfidence[:\s]*(\d{1,3})\s*%',
        r'[Cc]onfidence[:\s]*(\d{1,3})\b',
        r'(\d{1,3})\s*%\s*[Cc]onfident',
        r'[Cc]onfident.*?(\d{1,3})\s*%',
        r'(\d{1,3})\s*%',
    ]
    for pat in patterns:
        match = re.search(pat, response)
        if match:
            val = int(match.group(1))
            if 0 <= val <= 100:
                return val
    
    # Fallback: find all numbers and take the last one
    numbers = re.findall(r'\b(\d{1,3})\b', response)
    if numbers:
        val = int(numbers[-1])
        if 0 <= val <= 100:
            return val
    return None

def save_json_atomic(path, value):
    """Avoid leaving a truncated checkpoint when a run is interrupted."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "w") as f:
        json.dump(value, f, indent=2)
    os.replace(temp_path, path)


# Load existing data
with open(f"{INPUT_DIR}/raw_responses.json") as f:
    all_results = json.load(f)

# Re-run confidence for all models
for model_id, model_name in MODELS:
    print(f"\n=== {model_name} ({model_id}) ===")
    if model_name not in all_results:
        print("  Model not present in input; skipping.")
        continue
    results = all_results[model_name]
    
    done_file = f"{INPUT_DIR}/confidence_v2_{model_name.replace(' ', '_').replace('/', '_')}.json"
    if os.path.exists(done_file):
        print(f"  Loading checkpoint from {done_file}")
        with open(done_file) as f:
            new_confs = json.load(f)
        if len(new_confs) > len(results):
            raise ValueError(f"{done_file} has more entries than the input data")
    else:
        new_confs = []

    for i, r in enumerate(results):
        existing = new_confs[i] if i < len(new_confs) else None
        if existing and existing.get("question_id") not in (None, r.get("question_id")):
            raise ValueError(f"Checkpoint/input mismatch at index {i} in {done_file}")
        if existing and existing.get("confidence") is not None and not existing.get("confidence_error"):
            continue

        if r.get("error"):
            record = {
                "question_id": r.get("question_id"),
                "confidence": None,
                "confidence_tokens": 0,
                "confidence_error": "skipped (answer error)",
            }
        else:
            predicted = r.get("predicted_letter", "unknown")
            messages = make_confidence_prompt_with_context(
                r.get("question", ""),
                r.get("choices", {}),
                predicted,
                r.get("response", ""),
                r.get("thinking", ""),
            )

            print(f"  Q{i+1}/{len(results)}...", end="", flush=True)
            conf_result = call_ollama_api(model_id, messages, timeout=120)
            confidence = extract_confidence(conf_result["response"])
            record = {
                "question_id": r.get("question_id"),
                "confidence": confidence,
                "confidence_tokens": conf_result.get("total_tokens", 0),
                "confidence_raw": conf_result["response"][:200],
                "confidence_error": conf_result.get("error"),
            }

        if i < len(new_confs):
            new_confs[i] = record
        else:
            new_confs.append(record)
        save_json_atomic(done_file, new_confs)

    print()
    
    # Print summary
    valid_confs = [c["confidence"] for c in new_confs if c["confidence"] is not None]
    if valid_confs:
        from collections import Counter
        c = Counter(valid_confs)
        print(f"  Valid: {len(valid_confs)}/{len(new_confs)}")
        print(f"  Avg: {sum(valid_confs)/len(valid_confs):.1f}%")
        print(f"  Distribution: {c.most_common(10)}")
    else:
        print(f"  No valid confidences extracted!")

# Now merge new confidences into the data and save
print("\n=== Merging new confidences ===")
for model_id, model_name in MODELS:
    if model_name not in all_results:
        continue
    done_file = f"{INPUT_DIR}/confidence_v2_{model_name.replace(' ', '_').replace('/', '_')}.json"
    if os.path.exists(done_file):
        with open(done_file) as f:
            new_confs = json.load(f)
        
        results = all_results[model_name]
        for i, r in enumerate(results):
            if i < len(new_confs):
                checkpoint_id = new_confs[i].get("question_id")
                if checkpoint_id not in (None, r.get("question_id")):
                    raise ValueError(f"Checkpoint/input mismatch at index {i} in {done_file}")
                r["confidence_old"] = r.get("confidence")
                r["confidence"] = new_confs[i]["confidence"]
                r["confidence_tokens_old"] = r.get("confidence_tokens", 0)
                r["confidence_tokens"] = new_confs[i].get("confidence_tokens", 0)
                r["confidence_raw"] = new_confs[i].get("confidence_raw", "")

# Save only the current, supported model set.
final_results = {
    model_name: all_results[model_name]
    for _, model_name in MODELS
    if model_name in all_results
}
save_json_atomic(OUTPUT_FILE, final_results)
print(f"\nSaved to {OUTPUT_FILE}")

# Print final comparison
print("\n=== Confidence Comparison (old → new) ===")
for model_id, model_name in MODELS:
    if model_name not in all_results:
        continue
    results = all_results[model_name]
    old_confs = [r.get("confidence_old") for r in results if r.get("confidence_old") is not None]
    new_confs = [r.get("confidence") for r in results if r.get("confidence") is not None]
    
    correct_new = [r["confidence"] for r in results if r.get("correct") and r.get("confidence") is not None]
    wrong_new = [r["confidence"] for r in results if not r.get("correct") and r.get("confidence") is not None]
    
    print(f"\n{model_name}:")
    if old_confs:
        print(f"  Old: avg={sum(old_confs)/len(old_confs):.1f}% (n={len(old_confs)})")
    if new_confs:
        print(f"  New: avg={sum(new_confs)/len(new_confs):.1f}% (n={len(new_confs)})")
    if correct_new:
        print(f"  New correct: avg={sum(correct_new)/len(correct_new):.1f}% (n={len(correct_new)})")
    if wrong_new:
        print(f"  New wrong: avg={sum(wrong_new)/len(wrong_new):.1f}% (n={len(wrong_new)})")
    if correct_new and wrong_new:
        gap = sum(correct_new)/len(correct_new) - sum(wrong_new)/len(wrong_new)
        print(f"  Gap: {gap:+.1f}")
