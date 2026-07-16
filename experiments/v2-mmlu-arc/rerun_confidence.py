#!/usr/bin/env python3
"""Re-run confidence assessment with conversation context.
Only re-calls the confidence step (not the answer step). 
Saves to raw_responses_v2.json to preserve original data.
"""
import json, os, sys, time, re, urllib.request, urllib.error
warnings = sys.modules.get('warnings')
if warnings:
    import warnings as w
    w.filterwarnings("ignore")

API_KEY = '7d30048207d541afa72fceb4a639852f._kuPlqyToP_iFGGYEek_UIcA'
API_URL = 'https://ollama.com/api/chat'

INPUT_DIR = "experiments/v2-mmlu-arc/results"
OUTPUT_FILE = f"{INPUT_DIR}/raw_responses_v2.json"

MODELS = [
    ("gpt-oss:20b-cloud", "GPT-OSS-20B"),
    ("deepseek-v4-flash:cloud", "DeepSeek-V4-Flash-158B"),
    ("gpt-oss:120b-cloud", "GPT-OSS-120B"),
    ("glm-4.7:cloud", "GLM-4.7-357B"),
    ("glm-5.2:cloud", "GLM-5.2-756B"),
]

def call_ollama_api(model, messages, timeout=120):
    """Call ollama cloud via HTTP API with multi-turn messages."""
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

def make_confidence_prompt_with_context(question, choices, predicted_answer, model_response):
    """Create a conversation with context for confidence assessment."""
    # Build the question text
    if isinstance(choices, dict):
        choices_text = "\n".join([f"  {k}. {v}" for k, v in choices.items()])
    elif isinstance(choices, list):
        letters = ['A', 'B', 'C', 'D', 'E']
        choices_text = "\n".join([f"  {letters[i]}. {v}" for i, v in enumerate(choices)])
    else:
        choices_text = str(choices)
    
    user_msg = f"""{question}

Choices:
{choices_text}

What is the correct answer? Give only the letter."""

    # The model's original answer (truncated if too long)
    response_snippet = model_response[:500] if len(model_response) > 500 else model_response

    confidence_msg = f"""You previously answered "{predicted_answer}" for this question. 

Your reasoning was:
{response_snippet}

Based on your reasoning, how confident are you that "{predicted_answer}" is the correct answer? 

Give ONLY a single number from 0 to 100 (0 = completely unsure, 100 = absolutely certain). Do not include any other text."""

    return [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": model_response[:1000] if len(model_response) > 1000 else model_response},
        {"role": "user", "content": confidence_msg},
    ]

# Load existing data
with open(f"{INPUT_DIR}/raw_responses.json") as f:
    all_results = json.load(f)

# Re-run confidence for all models
for model_id, model_name in MODELS:
    print(f"\n=== {model_name} ({model_id}) ===")
    results = all_results[model_name]
    
    # Check if already done
    done_file = f"{INPUT_DIR}/confidence_v2_{model_name.replace(' ', '_').replace('/', '_')}.json"
    if os.path.exists(done_file):
        print(f"  Already done, loading from {done_file}")
        with open(done_file) as f:
            new_confs = json.load(f)
    else:
        new_confs = []
        for i, r in enumerate(results):
            if r.get("error"):
                new_confs.append({"confidence": None, "confidence_tokens": 0, "confidence_error": "skipped (answer error)"})
                continue
            
            predicted = r.get("predicted_letter", "unknown")
            question = r.get("question", "")
            choices = r.get("choices", {})
            response = r.get("response", "")
            
            # Build contextual messages
            messages = make_confidence_prompt_with_context(question, choices, predicted, response)
            
            print(f"  Q{i+1}/100...", end="", flush=True)
            conf_result = call_ollama_api(model_id, messages, timeout=120)
            
            confidence = extract_confidence(conf_result["response"])
            new_confs.append({
                "confidence": confidence,
                "confidence_tokens": conf_result.get("total_tokens", 0),
                "confidence_raw": conf_result["response"][:200],
                "confidence_error": conf_result.get("error"),
            })
            
            # Save incrementally
            with open(done_file, "w") as f:
                json.dump(new_confs, f, indent=2)
        
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
    done_file = f"{INPUT_DIR}/confidence_v2_{model_name.replace(' ', '_').replace('/', '_')}.json"
    if os.path.exists(done_file):
        with open(done_file) as f:
            new_confs = json.load(f)
        
        results = all_results[model_name]
        for i, r in enumerate(results):
            if i < len(new_confs):
                r["confidence_old"] = r.get("confidence")
                r["confidence"] = new_confs[i]["confidence"]
                r["confidence_tokens_old"] = r.get("confidence_tokens", 0)
                r["confidence_tokens"] = new_confs[i].get("confidence_tokens", 0)
                r["confidence_raw"] = new_confs[i].get("confidence_raw", "")

# Save merged data
with open(OUTPUT_FILE, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\nSaved to {OUTPUT_FILE}")

# Print final comparison
print("\n=== Confidence Comparison (old → new) ===")
for model_id, model_name in MODELS:
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