#!/usr/bin/env python3
"""Stage 2P: collect prefix + continuation. Formal mode uses process_stage2p_formal_raw.json."""

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

THINK_CONFIG = {
    "GPT-OSS-120B": "low",
    "DeepSeek-V4-Flash-158B": False,
}

PROMPT_VERSION = "stage2p.v2"
PREFIX_PROMPT_TEMPLATE = "Show concise reasoning. End with exactly one final answer in \\boxed{{}}.\n\n{problem}"
CONTINUATION_PROMPT = "Continue from your existing work. Do not restart.\nEnd with exactly one final answer in \\boxed{{}}."

# Output paths
SMOKE_OUT = "process_stage2p_smoke.json"
FORMAL_OUT = "process_stage2p_formal_raw.json"


def compute_process_state(content, parsed_answer):
    if parsed_answer:
        return "complete"
    if content and content.strip():
        return "visible_unfinished"
    return "empty_unfinished"


def api_call(model_name, messages, budget, temperature=0.0):
    model_id = MODEL_MAP.get(model_name)
    if not model_id:
        return None, f"Unknown model: {model_name}"

    think_val = THINK_CONFIG.get(model_name, False)
    payload = {
        "model": model_id,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": budget, "temperature": temperature},
        "think": think_val,
    }
    # Save request metadata for audit
    request_meta = {
        "think_setting": think_val,
        "temperature": temperature,
        "num_predict": budget,
        "prompt_version": PROMPT_VERSION,
    }

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

        prompt_tokens = int(body.get("prompt_eval_count") or body.get("usage", {}).get("prompt_tokens") or 0)
        completion_tokens = int(body.get("eval_count") or body.get("usage", {}).get("completion_tokens") or 0)

        return {
            "content": msg.get("content", ""),
            "thinking": msg.get("thinking", ""),
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "done_reason": body.get("done_reason"),
            "elapsed": round(elapsed, 3),
            "error": None,
            "request_meta": request_meta,
        }, None
    except urllib.error.HTTPError as e:
        return {"content": "", "thinking": "", "error": f"HTTP {e.code}: {e.read().decode()[:500]}",
                "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
                "done_reason": None, "elapsed": 0, "request_meta": request_meta}, None
    except Exception as e:
        return {"content": "", "thinking": "", "error": str(e),
                "completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
                "done_reason": None, "elapsed": 0, "request_meta": request_meta}, None


def load_questions(stage="formal"):
    manifest_path = Path(__file__).resolve().parent / "data" / "process_stage2_questions.json"
    with open(manifest_path) as f:
        data = json.load(f)
    return data["splits"].get(stage, [])


def make_prefix_messages(problem):
    return [{"role": "user", "content": PREFIX_PROMPT_TEMPLATE.replace("{problem}", problem)}]


def make_continuation_messages(problem, prefix_content):
    prefix_prompt = PREFIX_PROMPT_TEMPLATE.replace("{problem}", problem)
    return [
        {"role": "user", "content": prefix_prompt},
        {"role": "assistant", "content": prefix_content},
        {"role": "user", "content": CONTINUATION_PROMPT},
    ]


def load_and_index(checkpoint_path):
    """Load checkpoint and return (all_records, index_by_key)."""
    if not checkpoint_path.exists():
        return [], {}
    with open(checkpoint_path) as f:
        data = json.load(f)
    records = data.get("records", [])
    index = {}
    for r in records:
        key = (r.get("stage", ""), r.get("model", ""), r.get("question_id", ""), r.get("action", ""))
        if not r.get("error") and r.get("action") in ("prefix", "continuation"):
            # Only mark as done if no error
            index[key] = r
        else:
            # Keep errored records but don't mark as done
            pass
    return records, index


def atomic_save(checkpoint_path, records):
    schema = {
        "schema_version": PROMPT_VERSION,
        "last_saved": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n_records": len(records),
    }
    tmp = checkpoint_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump({"schema": schema, "records": records}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, checkpoint_path)


def do_prefix(question, model, stage, checkpoint_path, index):
    """Run or skip prefix. Returns (record, done_flag)."""
    qid = question["id"]
    key = (stage, model, qid, "prefix")
    if key in index:
        return index[key], True  # already done

    messages = make_prefix_messages(question["problem"])
    result, _ = api_call(model, messages, 512, 0.0)
    parsed = extract_boxed(result.get("content", ""))
    rec = {
        "stage": stage, "model": model, "question_id": qid, "action": "prefix",
        "budget": 512, "temperature": 0.0, **result,
        "parsed_answer": parsed or "", "correct": is_correct(parsed, question["answer"]) if parsed else False,
        "process_state": compute_process_state(result.get("content", ""), parsed),
        "expected_answer": question.get("answer", ""),
    }
    return rec, False


def do_continuation(question, model, stage, prefix_content, checkpoint_path, index):
    """Run or skip continuation. Returns (record, done_flag)."""
    qid = question["id"]
    key = (stage, model, qid, "continuation")
    if key in index:
        return index[key], True

    messages = make_continuation_messages(question["problem"], prefix_content)
    result, _ = api_call(model, messages, 512, 0.0)
    parsed = extract_boxed(result.get("content", ""))
    rec = {
        "stage": stage, "model": model, "question_id": qid, "action": "continuation",
        "budget": 512, "temperature": 0.0, "context_mode": "contextual_continuation",
        **result,
        "parsed_answer": parsed or "", "correct": is_correct(parsed, question["answer"]) if parsed else False,
        "expected_answer": question.get("answer", ""),
        "prefix_content_chars": len(prefix_content),
    }
    return rec, False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="formal", choices=["formal", "gate0", "gate1"])
    parser.add_argument("--models", nargs="+", default=["GPT-OSS-120B", "DeepSeek-V4-Flash-158B"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--question-ids", nargs="+")
    args = parser.parse_args()

    questions = load_questions(args.stage)
    if args.question_ids:
        questions = [q for q in questions if q["id"] in args.question_ids]
        print(f"Filtered to {len(questions)} specific questions")

    if not args.execute:
        expected = len(questions) * len(args.models) * 2
        print(f"DRY RUN: {expected} actions for stage={args.stage}")
        print("Re-run with --execute to proceed.")
        return

    # Stage-specific output path
    out_name = SMOKE_OUT if args.stage == "gate0" else FORMAL_OUT
    ckpt = RESULTS_DIR / out_name

    # Load existing records + index
    all_records, index = load_and_index(ckpt)
    print(f"Checkpoint: {len(all_records)} records, {len(index)} done keys")

    n_errors = 0
    n_skipped = 0

    for question in questions:
        for model in args.models:
            # --- PREFIX ---
            pref_rec, pref_done = do_prefix(question, model, args.stage, ckpt, index)
            if pref_done:
                # Read existing prefix record (for continuation context)
                pref_rec = index[(args.stage, model, question["id"], "prefix")]
            # Append if new
            pref_key = (args.stage, model, question["id"], "prefix")
            if pref_key not in index:
                all_records.append(pref_rec)
                index[pref_key] = pref_rec
                atomic_save(ckpt, all_records)
                n_errors += 1 if pref_rec.get("error") else 0
                time.sleep(0.15)
            else:
                n_skipped += 1

            pstate = pref_rec.get("process_state", "?")
            ptok = pref_rec.get("total_tokens", 0)
            p_err = pref_rec.get("error", "")
            print(f"{model[:20]:20s} prefix  {question['id'][:40]:40s} {pstate:20s} tok={ptok}"
                  + (f" err={p_err}" if p_err else ""))

            # --- CONTINUATION ---
            cont_rec, cont_done = do_continuation(question, model, args.stage,
                                                  pref_rec.get("content", ""), ckpt, index)
            cont_key = (args.stage, model, question["id"], "continuation")
            if cont_key not in index:
                all_records.append(cont_rec)
                index[cont_key] = cont_rec
                atomic_save(ckpt, all_records)
                n_errors += 1 if cont_rec.get("error") else 0
                time.sleep(0.15)
            else:
                n_skipped += 1

            ctok = cont_rec.get("total_tokens", 0)
            cerr = cont_rec.get("error", "")
            print(f"{model[:20]:20s} cont    {question['id'][:40]:40s} tok={ctok}"
                  + (f" err={cerr}" if cerr else ""))

    print(f"\nDone: {len(all_records)} records, {n_skipped} skipped, {n_errors} errors -> {ckpt}")


if __name__ == "__main__":
    import urllib.request, urllib.error
    main()