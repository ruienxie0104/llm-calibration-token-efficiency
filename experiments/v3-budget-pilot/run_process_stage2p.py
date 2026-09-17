#!/usr/bin/env python3
"""Stage 2P: collect prefix + continuation for formal interventional pilot."""

import sys, json, os, time, copy, re, hashlib
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

# Prompt contracts (consistent across all stages)
PREFIX_PROMPT = """Show concise reasoning. End with exactly one final answer in \\boxed{{}}.

{{problem}}"""

CONTINUATION_PROMPT = """Continue from your existing work. Do not restart.
End with exactly one final answer in \\boxed{{}}."""

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

    # For GPT-OSS-120B, use think=low for consistency with Gate 0
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

        # Prompt tokens: Ollama uses prompt_eval_count
        prompt_tokens = int(
            body.get("prompt_eval_count")
            or body.get("usage", {}).get("prompt_tokens")
            or 0
        )
        completion_tokens = int(
            body.get("eval_count")
            or body.get("usage", {}).get("completion_tokens")
            or 0
        )
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

def validate_manifest(stage, questions):
    """Validate that questions match expected stage."""
    expected_ids = sorted(q["id"] for q in questions)
    seen = set()
    for qid in expected_ids:
        assert qid not in seen, f"Duplicate question ID: {qid}"
        seen.add(qid)
    print(f"Validated: {len(questions)} unique questions for stage={stage}")

def load_checkpoint(checkpoint_path, stage, models):
    """Load existing checkpoint, return set of completed keys."""
    if not checkpoint_path.exists():
        return set()
    with open(checkpoint_path) as f:
        data = json.load(f)
    keys = set()
    for r in data.get("records", []):
        if r.get("stage") == stage and r.get("model") in models:
            keys.add((r["stage"], r["model"], r["question_id"], r["action"]))
    return keys

def atomic_save(checkpoint_path, all_records, schema):
    """Save checkpoint atomically."""
    tmp = checkpoint_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump({"schema": schema, "records": all_records}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, checkpoint_path)

def make_prefix_messages(problem):
    """Create messages for 512-token prefix generation."""
    content = PREFIX_PROMPT.replace("{{problem}}", problem)
    return [{"role": "user", "content": content}]

def make_continuation_messages(problem, prefix_content):
    """Create continuation messages: original problem + existing work as assistant context."""
    prefix_prompt = PREFIX_PROMPT.replace("{{problem}}", problem)
    return [
        {"role": "user", "content": prefix_prompt},
        {"role": "assistant", "content": prefix_content},
        {"role": "user", "content": CONTINUATION_PROMPT},
    ]

def run_question(question, model, stage="formal", checkpoint=None, done_keys=None):
    """Collect prefix and continuation for one question-model pair. Atomic per action."""
    qid = question["id"]
    records = []

    # --- prefix ---
    prefix_key = (stage, model, qid, "prefix")
    if done_keys and prefix_key in done_keys:
        return [], True  # skip, already done

    prefix_messages = make_prefix_messages(question["problem"])
    result, err = api_call(model, prefix_messages, 512, 0.0)
    if err:
        rec = {
            "stage": stage, "model": model, "question_id": qid, "action": "prefix",
            "budget": 512, "temperature": 0.0,
            "content": "", "thinking": "", "error": err,
            "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
            "done_reason": None, "elapsed": 0,
        }
    else:
        rec = {
            "stage": stage, "model": model, "question_id": qid, "action": "prefix",
            "budget": 512, "temperature": 0.0,
            **result,
        }

    parsed = extract_boxed(rec.get("content", ""))
    rec["parsed_answer"] = parsed or ""
    rec["correct"] = is_correct(parsed, question["answer"]) if parsed else False
    rec["process_state"] = compute_process_state(rec.get("content", ""), parsed)
    rec["expected_answer"] = question.get("answer", "")
    records.append(rec)

    # Atomic checkpoint after prefix
    if checkpoint is not None:
        checkpoint_path = Path(checkpoint)
        existing = []
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                existing_data = json.load(f)
                existing = existing_data.get("records", [])
        schema = {
            "schema_version": "stage2p.v2",
            "last_saved": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stage": stage, "models": [model], "n_records": len(existing) + len(records),
        }
        atomic_save(checkpoint_path, existing + records, schema)
        time.sleep(0.15)  # rate limit

    # --- continuation ---
    continuation_key = (stage, model, qid, "continuation")
    if done_keys and continuation_key in done_keys:
        return [], True  # skip, already done

    prefix_content = rec.get("content", "")
    cont_messages = make_continuation_messages(question["problem"], prefix_content)
    result_c, err_c = api_call(model, cont_messages, 512, 0.0)
    if err_c:
        rec_c = {
            "stage": stage, "model": model, "question_id": qid, "action": "continuation",
            "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
            "content": "", "thinking": "", "error": err_c,
            "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
            "done_reason": None, "elapsed": 0,
            "prefix_content_chars": len(prefix_content),
        }
    else:
        rec_c = {
            "stage": stage, "model": model, "question_id": qid, "action": "continuation",
            "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
            **result_c,
            "prefix_content_chars": len(prefix_content),
        }

    parsed_c = extract_boxed(rec_c.get("content", ""))
    rec_c["parsed_answer"] = parsed_c or ""
    rec_c["correct"] = is_correct(parsed_c, question["answer"]) if parsed_c else False
    rec_c["expected_answer"] = question.get("answer", "")
    records.append(rec_c)

    return records, False

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="formal",
                        choices=["formal", "gate0", "gate1"],
                        help="Question split to use")
    parser.add_argument("--models", nargs="+",
                        default=["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"])
    parser.add_argument("--execute", action="store_true",
                        help="Execute API calls")
    parser.add_argument("--question-ids", nargs="+",
                        help="Specific question IDs (for smoke test)")
    args = parser.parse_args()

    questions = load_questions(args.stage)
    if args.question_ids:
        questions = [q for q in questions if q["id"] in args.question_ids]
        print(f"Filtered to {len(questions)} specific questions")
    validate_manifest(args.stage, questions)

    dry_run = not args.execute
    print(f"Stage {args.stage}: {len(questions)} questions × {len(args.models)} models")
    if dry_run:
        expected = len(questions) * len(args.models) * 2
        print(f"DRY RUN: no API calls. Approx {expected} actions (prefix + continuation).")
        print(f"Re-run with --execute after reviewing.")
        return

    # Output file is stage-specific
    out_name = f"process_stage2p_smoke.json" if args.stage == "gate0" else f"process_stage2p_raw.json"
    checkpoint_path = RESULTS_DIR / out_name

    # Load checkpoint
    done_keys = load_checkpoint(checkpoint_path, args.stage, args.models)
    print(f"Checkpoint loaded: {len(done_keys)} existing keys")

    all_records = []
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            data = json.load(f)
            all_records = data.get("records", [])

    n_total = len(questions) * len(args.models)
    done = 0
    skipped = 0
    n_errors = 0

    for question in questions:
        for model in args.models:
            records, was_skipped = run_question(
                question, model,
                stage=args.stage,
                checkpoint=str(checkpoint_path),
                done_keys=done_keys,
            )
            done += 1
            if was_skipped:
                skipped += 1
                continue
            all_records.extend(records)
            for r in records:
                tok = r.get("total_tokens", 0)
                ptok = r.get("prompt_tokens", 0)
                err = r.get("error", "")
                state = r.get("process_state", "")
                a = r["action"]
                n_errors += 1 if err else 0
                print(f"{model[:20]:20s} {a:15s} {r['question_id'][:40]:40s} "
                      f"{state:20s} tok={tok} ptok={ptok}" + (f" err={err}" if err else ""))

    # Final save
    schema = {
        "schema_version": "stage2p.v2",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "stage": args.stage,
        "models": args.models,
        "n_questions": len(questions),
        "n_records": len(all_records),
        "n_skipped": skipped,
        "n_errors": n_errors,
    }
    atomic_save(checkpoint_path, all_records, schema)
    print(f"\nSaved {len(all_records)} action records to {checkpoint_path}")
    if skipped:
        print(f"Skipped {skipped} previously completed units")
    if n_errors:
        print(f"WARNING: {n_errors} action(s) had errors")

if __name__ == "__main__":
    import urllib.request, urllib.error
    main()