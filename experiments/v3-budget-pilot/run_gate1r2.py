#!/usr/bin/env python3
"""Gate 1R2: Minimal think=false smoke test. 5 GPT empty cases × 2 branches = 10 calls."""

import json, os, time, urllib.request, sys, copy, hashlib
from pathlib import Path
sys.path.insert(0, 'experiments/v3-budget-pilot')
sys.path.insert(0, 'experiments/v3-budget-pilot/data')

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
    return {q['id']: q for q in all_qs if q['id'] in EMPTY_CASES}

def extract_boxed(text):
    """Extract boxed answer from text."""
    if not text:
        return None
    import re
    m = re.search(r'\\boxed\{([^}]*)\}', text)
    if m:
        return m.group(1).strip()
    # fallback: try to find the last number
    nums = re.findall(r'-?\d+(?:\.\d+)?', text)
    return nums[-1] if nums else None

def is_correct(parsed, expected):
    if not parsed:
        return False
    try:
        p = float(parsed.replace(',','').strip())
        e = float(expected.replace(',','').strip())
        return abs(p - e) < 1e-6
    except:
        return parsed.strip() == expected.strip()

BRANCH_PROMPT = """Solve independently. Keep the reasoning concise.
End with exactly one final answer in \\boxed{}.

{problem}"""

def call(model, prompt, budget=256, save_thinking=True):
    """Call API with think=false explicitly."""
    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": "gpt-oss:120b-cloud",
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": budget,
            "temperature": 0.7,
        },
    }
    # Explicitly set think to false to disable hidden reasoning
    payload["think"] = False

    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"})
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        elapsed = time.time() - t0
        msg = body.get("message", {})
        content = msg.get("content", "")
        # Check if thinking field exists
        thinking = msg.get("thinking", "") if save_thinking else ""
        usage = body.get("usage", {})
        return {
            "content": content,
            "thinking": thinking,
            "completion_tokens": body.get("eval_count", usage.get("completion_tokens", 0)),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "total_tokens": body.get("eval_count", 0) + usage.get("prompt_tokens", 0),
            "done_reason": body.get("done_reason"),
            "elapsed": elapsed,
            "error": None,
        }
    except Exception as e:
        return {
            "content": "", "thinking": "",
            "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
            "done_reason": None, "elapsed": 0,
            "error": str(e),
        }

def run_branch(question, branch_id, budget=256):
    prompt = BRANCH_PROMPT.replace('{problem}', question['problem'])
    response = call("GPT-OSS-120B", prompt, budget, save_thinking=True)
    boxed = extract_boxed(response['content'])
    correct = is_correct(boxed, question['answer']) if boxed else False
    record = {
        "model": "GPT-OSS-120B",
        "question_id": question['id'],
        "question_problem": question['problem'][:100],
        "expected_answer": question['answer'],
        "branch_id": branch_id,
        "budget": budget,
        "branch_prompt": prompt,
        **response,
        "parsed_answer": boxed or "",
        "correct": correct,
        # Full response for audit
        "content_full": response['content'],
        "thinking_full": response.get('thinking', ''),
    }
    return record, boxed

def main():
    questions = load_questions()
    print(f"Loaded {len(questions)} questions")
    all_records = []

    for q_id in EMPTY_CASES:
        q = questions.get(q_id)
        if not q:
            print(f"SKIP {q_id}: not in manifest")
            continue
        print(f"\n--- {q_id.split('/')[-1]} ---")

        # Branch 1
        r1, b1 = run_branch(q, "1", 256)
        # Branch 2 - fresh context, no shared info
        r2, b2 = run_branch(q, "2", 256)
        all_records.extend([r1, r2])

        # Audit output
        print(f"  b1: parsed={'✓' if b1 else '✗'} boxed={b1 or 'NONE'} tok={r1['completion_tokens']} think_len={len(r1.get('thinking',''))} dr={r1['done_reason']}")
        if r1['content']:
            print(f"    content preview: {r1['content'][:200]}")
        print(f"  b2: parsed={'✓' if b2 else '✗'} boxed={b2 or 'NONE'} tok={r2['completion_tokens']} think_len={len(r2.get('thinking',''))} dr={r2['done_reason']}")
        if r2['content']:
            print(f"    content preview: {r2['content'][:200]}")
        if b1 and b2:
            agree = b1 == b2
            print(f"  agreement: {'✓' if agree else '✗'} ({b1} vs {b2})")
        time.sleep(0.25)

    # Summary
    print("\n=== GATE 1R2 SUMMARY ===")
    total = len(all_records)
    parsed = [r for r in all_records if r['parsed_answer']]
    pct = len(parsed)/total*100 if total else 0
    print(f"Total calls: {total}")
    print(f"Parsed: {len(parsed)}/{total} = {pct:.0f}%")
    for r in all_records:
        found_thinking = bool(r.get('thinking',''))
        print(f"  {r['question_id'].split('/')[-1]:30s} b={r['branch_id']} parsed={'✓' if r['parsed_answer'] else '✗'} tok={r['completion_tokens']} think_found={found_thinking} dr={r['done_reason']}")

    # Save
    out = RESULTS_DIR / "process_stage2_gate1r2.json"
    # Strip full content for storage, keep preview
    save_records = []
    for r in all_records:
        sr = copy.deepcopy(r)
        sr.pop('branch_prompt', None)
        sr.pop('content_full', None)
        sr.pop('thinking_full', None)
        save_records.append(sr)
    with open(out, "w") as f:
        json.dump(save_records, f, indent=2)

    # Save full raw responses for audit
    raw_out = RESULTS_DIR / "process_stage2_gate1r2_raw.json"
    with open(raw_out, "w") as f:
        json.dump(all_records, f, indent=2)
    print(f"\nSaved audit to {raw_out}")
    print(f"Saved summary to {out}")

if __name__ == "__main__":
    main()