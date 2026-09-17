#!/usr/bin/env python3
"""Collect the Stage 3 prefix/continuation action bank.

Dry-run is the default.  ``--execute`` is required before any network request.
Both actions are collected for each unit solely to evaluate counterfactual
allocation policies from one common action bank.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from answer_utils import extract_boxed, is_correct  # noqa: E402

RESULTS_DIR = SCRIPT_DIR / "results"
MANIFEST_PATH = SCRIPT_DIR / "data" / "process_stage3_questions.json"
OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
MODEL_MAP = {
    "GPT-OSS-120B": "gpt-oss:120b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
}
THINK_CONFIG = {"GPT-OSS-120B": "low", "DeepSeek-V4-Flash-158B": False}
FORMAL_MODELS = tuple(MODEL_MAP)
PROMPT_VERSION = "stage3.visible-only.v1"
PREFIX_PROMPT = "Show concise reasoning. End with exactly one final answer in \\boxed{{}}.\n\n{problem}"
CONTINUATION_PROMPT = "Continue from your existing work. Do not restart.\nEnd with exactly one final answer in \\boxed{{}}."
OUT_NAMES = {"smoke": "process_stage3_smoke.json", "formal": "process_stage3_formal_raw.json"}


def compute_process_state(content: str, parsed_answer: str | None) -> str:
    if parsed_answer:
        return "complete"
    return "visible_unfinished" if content and content.strip() else "empty_unfinished"


def manifest_fingerprint(questions: list[dict[str, Any]]) -> str:
    return hashlib.sha256("\n".join(q["id"] for q in questions).encode("utf-8")).hexdigest()


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1 or set(data.get("splits", {})) != {"smoke", "formal"}:
        raise ValueError("Invalid Stage 3 manifest schema.")
    return data


def load_questions(stage: str) -> list[dict[str, Any]]:
    return load_manifest()["splits"][stage]


def make_prefix_messages(problem: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": PREFIX_PROMPT.format(problem=problem)}]


def make_continuation_messages(problem: str, prefix_content: str) -> list[dict[str, str]]:
    return [
        {"role": "user", "content": PREFIX_PROMPT.format(problem=problem)},
        {"role": "assistant", "content": prefix_content},
        {"role": "user", "content": CONTINUATION_PROMPT},
    ]


def api_call(model: str, messages: list[dict[str, str]], budget: int = 512) -> dict[str, Any]:
    """Make one API request and always return an auditable record payload."""
    think = THINK_CONFIG[model]
    request_meta = {"think_setting": think, "temperature": 0.0, "num_predict": budget, "prompt_version": PROMPT_VERSION}
    payload = {"model": MODEL_MAP[model], "messages": messages, "stream": False,
               "options": {"num_predict": budget, "temperature": 0.0}, "think": think}
    request = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_KEY}"},
    )
    try:
        started = time.time()
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
        message = body.get("message", {})
        prompt_tokens = int(body.get("prompt_eval_count") or body.get("usage", {}).get("prompt_tokens") or 0)
        completion_tokens = int(body.get("eval_count") or body.get("usage", {}).get("completion_tokens") or 0)
        return {"content": message.get("content", ""), "thinking": message.get("thinking", ""),
                "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens, "done_reason": body.get("done_reason"),
                "elapsed": round(time.time() - started, 3), "error": None, "request_meta": request_meta}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        error = f"HTTP {exc.code}: {detail}"
    except Exception as exc:  # Keep failures checkpointed for a safe retry.
        error = str(exc)
    return {"content": "", "thinking": "", "prompt_tokens": 0, "completion_tokens": 0,
            "total_tokens": 0, "done_reason": None, "elapsed": 0.0, "error": error,
            "request_meta": request_meta}


def record_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (record.get("stage", ""), record.get("model", ""), record.get("question_id", ""), record.get("action", ""))


def load_checkpoint(path: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str], dict[str, Any]], dict[str, Any]]:
    if not path.exists():
        return [], {}, {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    canonical: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str, str]] = []
    for record in payload.get("records", []):
        key = record_key(record)
        if key not in canonical:
            order.append(key)
        if key not in canonical or canonical[key].get("error") or not record.get("error"):
            canonical[key] = record
    records = [canonical[key] for key in order]
    done = {record_key(row): row for row in records if not row.get("error")}
    return records, done, payload.get("schema", {})


def save_checkpoint(path: Path, records: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": {"schema_version": 1, "last_saved": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                           "n_records": len(records), **meta}, "records": records}
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(temporary, path)


def upsert(records: list[dict[str, Any]], record: dict[str, Any]) -> None:
    key = record_key(record)
    for index, existing in enumerate(records):
        if record_key(existing) == key:
            records[index] = record
            return
    records.append(record)


def validate_configuration(stage: str, models: list[str], questions: list[dict[str, Any]], question_filter: list[str] | None) -> None:
    if len(models) != len(set(models)) or set(models) - set(MODEL_MAP):
        raise ValueError("Models must be unique known Stage 3 models.")
    if stage == "formal":
        expected = load_questions("formal")
        if question_filter or questions != expected or len(questions) != 60:
            raise ValueError("Formal mode requires the exact ordered 60-question manifest and no filter.")
        if set(models) != set(FORMAL_MODELS) or len(models) != len(FORMAL_MODELS):
            raise ValueError(f"Formal mode requires exactly {list(FORMAL_MODELS)}.")


def validate_checkpoint(schema: dict[str, Any], meta: dict[str, Any], path: Path) -> None:
    if not schema:
        return
    for key in ("stage", "models", "question_ids_sha256", "prompt_version"):
        if schema.get(key) != meta[key]:
            raise ValueError(f"Incompatible checkpoint {path}: {key} differs.")


def make_record(question: dict[str, Any], model: str, stage: str, action: str, result: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    parsed = extract_boxed(result.get("content", ""))
    record: dict[str, Any] = {"stage": stage, "model": model, "question_id": question["id"], "action": action,
                              "budget": 512, "temperature": 0.0, **result, "parsed_answer": parsed or "",
                              "correct": is_correct(parsed, question["answer"]) if parsed else False,
                              "expected_answer": question["answer"], "messages_sent": messages}
    if action == "prefix":
        record["process_state"] = compute_process_state(result.get("content", ""), parsed)
    else:
        record["context_mode"] = "contextual_continuation"
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "formal"), default="formal")
    parser.add_argument("--models", nargs="+", default=list(FORMAL_MODELS))
    parser.add_argument("--question-ids", nargs="+")
    parser.add_argument("--execute", action="store_true", help="Required before API calls.")
    args = parser.parse_args()
    questions = load_questions(args.stage)
    if args.question_ids:
        questions = [question for question in questions if question["id"] in args.question_ids]
    try:
        validate_configuration(args.stage, args.models, questions, args.question_ids)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.execute:
        print(f"DRY RUN: {len(questions) * len(args.models) * 2} calls for stage={args.stage}; no API calls made.")
        return

    meta = {"stage": args.stage, "models": sorted(args.models), "question_count": len(questions),
            "question_ids_sha256": manifest_fingerprint(questions), "prompt_version": PROMPT_VERSION,
            "action_bank": True, "visible_only_policy_frozen": True}
    checkpoint = RESULTS_DIR / OUT_NAMES[args.stage]
    records, done, schema = load_checkpoint(checkpoint)
    try:
        validate_checkpoint(schema, meta, checkpoint)
    except ValueError as exc:
        parser.error(str(exc))
    for question in questions:
        for model in args.models:
            prefix_key = (args.stage, model, question["id"], "prefix")
            if prefix_key not in done:
                messages = make_prefix_messages(question["problem"])
                prefix = make_record(question, model, args.stage, "prefix", api_call(model, messages), messages)
                upsert(records, prefix)
                if not prefix["error"]:
                    done[prefix_key] = prefix
                save_checkpoint(checkpoint, records, meta)
                time.sleep(0.15)
            prefix = done.get(prefix_key)
            if not prefix:
                print(f"{model} {question['id']}: prefix failed; retry on next run")
                continue
            continuation_key = (args.stage, model, question["id"], "continuation")
            if continuation_key not in done:
                messages = make_continuation_messages(question["problem"], prefix.get("content", ""))
                continuation = make_record(question, model, args.stage, "continuation", api_call(model, messages), messages)
                continuation["prefix_content_chars"] = len(prefix.get("content", ""))
                upsert(records, continuation)
                if not continuation["error"]:
                    done[continuation_key] = continuation
                save_checkpoint(checkpoint, records, meta)
                time.sleep(0.15)
    failures = sum(bool(row.get("error")) for row in records)
    print(f"Saved {len(records)} records to {checkpoint}; failures={failures}. Re-run --execute only to retry failures.")


if __name__ == "__main__":
    main()
