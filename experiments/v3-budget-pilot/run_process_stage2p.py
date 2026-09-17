#!/usr/bin/env python3
"""Stage 2P: collect prefix + continuation for formal interventional pilot."""

import sys, json, os, time, copy, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import extract_boxed, is_correct

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")

MODEL_MAP = {
    "GPT-OSS-120B": "gpt-oss:120b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
}

def compute_process_state(content, parsed_answer):
    """Deterministic process state from visible content."""
    if parsed_answer:
        return "complete"
    if content and content.strip():
        return "visible_unfinished"
    return "empty_unfinished"

def api_call(model_name, messages, budget, temperature=0.0):
    """Single API call with error handling."""
    model_id = MODEL_MAP.get(model_name)
    if not model_id:
        return None, f"Unknown model: {model_name}"

    payload = {
        "model": model_id,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": budget,
            "temperature": temperature,
        },
    }

    # For GPT-OSS-120B, keep think setting (compatible with API)
    if model_name == "GPT-OSS-120B":
        payload["think"] = "low"

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"},
    )
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        elapsed = time.time() - t0
        msg = body.get("message", {})
        content = msg.get("content", "")
        thinking = msg.get("thinking", "")
        completion_tokens = body.get("eval_count", 0)
        prompt_tokens = body.get("prompt_tokens", 0)
        done_reason = body.get("done_reason")
        return {
            "content": content,
            "thinking": thinking,
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "done_reason": done_reason,
            "elapsed": round(elapsed, 3),
            "error": None,
        }, None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:500]
        return None, f"HTTP {e.code}: {err_body}"
    except Exception as e:
        return None, str(e)

def load_questions(stage="formal"):
    """Load questions from the manifest."""
    manifest_path = Path(__file__).resolve().parent / "data" / "process_stage2_questions.json"
    with open(manifest_path) as f:
        data = json.load(f)
    return data["splits"].get(stage, [])

def make_prefix_messages(question):
    """Create messages for 512-token prefix generation."""
    return [{"role": "user", "content": question["problem"]}]

def make_continuation_messages(question, prefix_content):
    """Create continuation messages: original problem + existing work as assistant context."""
    return [
        {"role": "user", "content": question["problem"]},
        {"role": "assistant", "content": prefix_content},
        {"role": "user", "content": "Continue from your existing work. Do not restart. End with \\boxed{answer}."},
    ]

def run_question(question, model, dry_run=False):
    """Collect prefix and continuation for one question-model pair."""
    qid = question["id"]
    records = []

    # --- prefix ---
    prefix_messages = make_prefix_messages(question)
    if dry_run:
        rec = {
            "model": model, "question_id": qid, "action": "prefix",
            "budget": 512, "temperature": 0.0,
            "dry_run": True, "content": "", "thinking": "",
            "completion_tokens": 512, "prompt_tokens": 0,
            "total_tokens": 512, "done_reason": None,
            "elapsed": 0, "error": None,
        }
    else:
        result, err = api_call(model, prefix_messages, 512, 0.0)
        if err:
            rec = {
                "model": model, "question_id": qid, "action": "prefix",
                "budget": 512, "temperature": 0.0,
                "content": "", "thinking": "", "error": err,
                "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
                "done_reason": None, "elapsed": 0,
            }
        else:
            rec = {
                "model": model, "question_id": qid, "action": "prefix",
                "budget": 512, "temperature": 0.0,
                **result,
            }
        time.sleep(0.15)

    # Parse answer and compute state
    parsed = extract_boxed(rec.get("content", ""))
    rec["parsed_answer"] = parsed or ""
    rec["correct"] = is_correct(parsed, question["answer"]) if parsed else False
    rec["process_state"] = compute_process_state(rec.get("content", ""), parsed)
    records.append(rec)

    # --- continuation ---
    if dry_run:
        rec_c = {
            "model": model, "question_id": qid, "action": "continuation",
            "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
            "dry_run": True, "content": "", "thinking": "",
            "completion_tokens": 512, "prompt_tokens": 0,
            "total_tokens": 512, "done_reason": None,
            "elapsed": 0, "error": None,
            "prefix_content_chars": len(rec.get("content", "")),
        }
    else:
        prefix_content = rec.get("content", "")
        cont_messages = make_continuation_messages(question, prefix_content)
        result_c, err_c = api_call(model, cont_messages, 512, 0.0)
        if err_c:
            rec_c = {
                "model": model, "question_id": qid, "action": "continuation",
                "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
                "content": "", "thinking": "", "error": err_c,
                "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
                "done_reason": None, "elapsed": 0,
                "prefix_content_chars": len(prefix_content),
            }
        else:
            rec_c = {
                "model": model, "question_id": qid, "action": "continuation",
                "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
                **result_c,
                "prefix_content_chars": len(prefix_content),
            }
        time.sleep(0.15)

    parsed_c = extract_boxed(rec_c.get("content", ""))
    rec_c["parsed_answer"] = parsed_c or ""
    rec_c["correct"] = is_correct(parsed_c, question["answer"]) if parsed_c else False
    records.append(rec_c)

    return records

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="formal", help="Question split to use")
    parser.add_argument("--models", nargs="+", default=["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"])
    parser.add_argument("--execute", action="store_true", help="Execute API calls")
    parser.add_argument("--question-ids", nargs="+", help="Specific question IDs (for smoke test)")
    args = parser.parse_args()

    questions = load_questions(args.stage)
    if args.question_ids:
        questions = [q for q in questions if q["id"] in args.question_ids]
        print(f"Filtered to {len(questions)} specific questions")

    dry_run = not args.execute
    print(f"Stage {args.stage}: {len(questions)} questions × {len(args.models)} models")
    if dry_run:
        expected = len(questions) * len(args.models) * 2
        print(f"DRY RUN: no API calls. Expected {expected} actions.")
        print(f"Re-run with --execute after reviewing.")
        return

    all_records = []
    n_total = len(questions) * len(args.models)
    done = 0

    for question in questions:
        for model in args.models:
            records = run_question(question, model, dry_run=False)
            all_records.extend(records)
            done += 1
            for r in records:
                tok = r.get("total_tokens", 0)
                err = r.get("error", "")
                state = r.get("process_state", "")
                a = r["action"]
                print(f"{model[:20]:20s} {a:15s} {r['question_id'][:40]:40s} {state:20s} tok={tok}" + (f" err={err}" if err else ""))

    # Save
    out = RESULTS_DIR / f"process_stage2p_raw.json"
    schema = {
        "schema_version": "stage2p.v1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "stage": args.stage,
        "models": args.models,
        "n_questions": len(questions),
        "n_records": len(all_records),
    }

    # Deduplicate saves
    existing = []
    if out.exists():
        with open(out) as f:
            existing_data = json.load(f)
            existing = existing_data.get("records", [])

    existing_ids = {(r["question_id"], r["model"], r["action"]) for r in existing}
    new_records = [r for r in all_records if (r["question_id"], r["model"], r["action"]) not in existing_ids]
    if new_records:
        all_records = existing + all_records
        print(f"\nAppended {len(new_records)} new records (total {len(all_records)})")

    with open(out, "w") as f:
        json.dump({"schema": schema, "records": all_records}, f, indent=2)
    print(f"\nSaved {len(all_records)} action records to {out}")

if __name__ == "__main__":
    import urllib.request, urllib.error
    main()