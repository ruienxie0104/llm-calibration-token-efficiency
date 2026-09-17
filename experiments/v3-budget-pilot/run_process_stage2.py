#!/usr/bin/env python3
"""Collect auditable Stage 2 actions; API execution is opt-in with ``--execute``.

The runner never labels a fresh independent answer as a continuation.  Its
``continuation`` action explicitly places the visible 512-token prefix in the
assistant context and records that limitation: hidden reasoning is not available
to the API, so this is a *visible-contextual* continuation test.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from answer_utils import extract_boxed, is_correct, normalize_answer  # noqa: E402
from process_event_extractor import activity_sequence, extract_events  # noqa: E402

MODELS = ("GPT-OSS-120B", "DeepSeek-V4-Flash-158B")
MODEL_MAP = {"GPT-OSS-120B": "gpt-oss:120b-cloud", "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud"}
THINK_SETTINGS = {"GPT-OSS-120B": "low", "DeepSeek-V4-Flash-158B": False}
DEFAULT_QUESTIONS = SCRIPT_DIR / "data" / "process_stage2_questions.json"
DEFAULT_RAW = SCRIPT_DIR / "results" / "process_stage2_raw.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("gate0", "gate1", "formal"), required=True)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--prefix-budget", type=int, default=512)
    parser.add_argument("--continuation-budget", type=int, default=512)
    parser.add_argument("--branch-budget", type=int, default=256)
    parser.add_argument("--fresh-high-budget", type=int, default=1024)
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on questions for smoke testing")
    parser.add_argument("--execute", action="store_true", help="Actually call the configured Ollama API")
    return parser.parse_args()


def load_questions(path: Path, stage: str, limit: int) -> tuple[dict, list[dict]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or stage not in payload.get("splits", {}):
        raise ValueError(f"{path} lacks a Stage 2 split named {stage!r}")
    rows = payload["splits"][stage]
    required = {"id", "problem", "answer", "level", "subject"}
    if not isinstance(rows, list) or any(required - set(row) for row in rows):
        raise ValueError("Question manifest has an invalid schema")
    return payload, rows[:limit] if limit else rows


def action_key(stage: str, model: str, question_id: str, action: str) -> tuple[str, str, str, str]:
    return stage, model, question_id, action


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    temp.replace(path)


def read_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "metadata": {}, "records": []}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError(f"Invalid checkpoint schema: {path}")
    return payload


def call_ollama(model: str, messages: list[dict], budget: int, temperature: float) -> dict:
    url = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
    key = os.environ.get("OLLAMA_API_KEY", "")
    payload = {
        "model": MODEL_MAP[model], "messages": messages, "think": THINK_SETTINGS[model],
        "options": {"num_predict": budget, "temperature": temperature}, "stream": False,
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
        message = body.get("message", {})
        return {
            "content": message.get("content", ""), "thinking": message.get("thinking", ""),
            "done_reason": body.get("done_reason"), "prompt_tokens": int(body.get("prompt_eval_count") or 0),
            "completion_tokens": int(body.get("eval_count") or 0),
            "latency_seconds": round(time.monotonic() - started, 4), "error": None,
        }
    except urllib.error.HTTPError as exc:
        return {"content": "", "thinking": "", "done_reason": None, "prompt_tokens": 0,
                "completion_tokens": 0, "latency_seconds": round(time.monotonic() - started, 4),
                "error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:  # API failures are recorded so a rerun can retry them.
        return {"content": "", "thinking": "", "done_reason": None, "prompt_tokens": 0,
                "completion_tokens": 0, "latency_seconds": round(time.monotonic() - started, 4),
                "error": str(exc)}


def initial_prompt(problem: str) -> str:
    return "Solve the math problem. Show concise reasoning and end with exactly one final answer in \\boxed{}.\n\nProblem:\n" + problem


def branch_prompt(problem: str) -> str:
    return "Solve independently. Keep the reasoning concise. End with exactly one final answer in \\boxed{}.\n\nProblem:\n" + problem


def classify_prefix(content: str) -> tuple[str, list[dict], str]:
    parsed = extract_boxed(content) or ""
    events = extract_events(content)
    if parsed:
        return "complete", [{"index": event.index, "activity": event.activity, "text": event.text} for event in events], parsed
    if events:
        return "visible_unfinished", [{"index": event.index, "activity": event.activity, "text": event.text} for event in events], ""
    return "empty_unfinished", [], ""


def make_record(stage: str, model: str, question: dict, action: str, budget: int, response: dict,
                *, prefix: dict | None = None, context_mode: str = "none") -> dict:
    content = response.get("content", "")
    parsed = extract_boxed(content) or ""
    record = {
        "stage": stage, "model": model, "question_id": question["id"], "level": question["level"],
        "subject": question["subject"], "expected_answer": question["answer"], "action": action,
        "budget": budget, "temperature": 0.0 if action != "branch_1" and action != "branch_2" else 0.7,
        "content": content, "thinking": response.get("thinking", ""), "done_reason": response.get("done_reason"),
        "prompt_tokens": response.get("prompt_tokens", 0), "completion_tokens": response.get("completion_tokens", 0),
        "latency_seconds": response.get("latency_seconds", 0), "error": response.get("error"),
        "parsed_answer": parsed, "normalized_answer": normalize_answer(parsed),
        "correct": bool(is_correct(parsed, question["answer"])), "context_mode": context_mode,
    }
    if action == "prefix":
        state, events, prefix_answer = classify_prefix(content)
        record.update({"process_state": state, "event_log": events, "activity_sequence": activity_sequence(content),
                       "parsed_answer": prefix_answer, "normalized_answer": normalize_answer(prefix_answer),
                       "correct": bool(is_correct(prefix_answer, question["answer"]))})
    if prefix is not None:
        record.update({"prefix_process_state": prefix["process_state"], "prefix_action": "prefix"})
    return record


def planned_actions(stage: str, prefix_state: str | None) -> list[str]:
    if prefix_state is None:
        return ["prefix"]
    actions = ["continuation"]
    if stage == "gate0":
        actions.append("fresh_high")
    if stage in {"gate1", "formal"} and prefix_state == "empty_unfinished":
        actions.extend(("branch_1", "branch_2"))
    return actions


def main() -> None:
    args = parse_args()
    manifest, questions = load_questions(args.questions, args.stage, args.limit)
    checkpoint = read_checkpoint(args.raw)
    records = checkpoint["records"]
    existing = {action_key(row["stage"], row["model"], row["question_id"], row["action"]): row for row in records}
    expected_prefixes = len(args.models) * len(questions)
    print(f"Stage {args.stage}: {len(questions)} questions × {len(args.models)} models; {expected_prefixes} required prefix actions")
    if not args.execute:
        print("DRY RUN: no API calls. Re-run with --execute after reviewing the manifest and API budget.")
        return

    checkpoint["metadata"] = {
        "schema_version": 1, "question_manifest": str(args.questions),
        "question_manifest_sha256": manifest.get("all_question_ids_sha256"), "visible_contextual_continuation": True,
        "hidden_thinking_is_not_replayed": True, "stage": args.stage,
        "budgets": {"prefix": args.prefix_budget, "continuation": args.continuation_budget,
                    "branch": args.branch_budget, "fresh_high": args.fresh_high_budget},
    }
    for model in args.models:
        for question in questions:
            prefix_key = action_key(args.stage, model, question["id"], "prefix")
            prefix = existing.get(prefix_key)
            if prefix is None or prefix.get("error"):
                response = call_ollama(model, [{"role": "user", "content": initial_prompt(question["problem"])}], args.prefix_budget, 0.0)
                prefix = make_record(args.stage, model, question, "prefix", args.prefix_budget, response)
                if prefix_key in existing:
                    records.remove(existing[prefix_key])
                records.append(prefix); existing[prefix_key] = prefix; atomic_write(args.raw, checkpoint)
                print(f"{model} {question['id']} prefix {prefix['process_state']} tok={prefix['completion_tokens']} err={prefix['error']}")
                time.sleep(args.sleep_seconds)
            for action in planned_actions(args.stage, prefix["process_state"]):
                key = action_key(args.stage, model, question["id"], action)
                if key in existing and not existing[key].get("error"):
                    continue
                if action == "continuation":
                    messages = [
                        {"role": "user", "content": initial_prompt(question["problem"])},
                        {"role": "assistant", "content": prefix.get("content", "")},
                        {"role": "user", "content": "Continue the existing solution from where it stopped. Do not restart. End with exactly one final answer in \\boxed{}."},
                    ]; budget, temperature, context = args.continuation_budget, 0.0, "visible_prefix_only"
                elif action == "fresh_high":
                    messages = [{"role": "user", "content": initial_prompt(question["problem"])}]; budget, temperature, context = args.fresh_high_budget, 0.0, "independent_fresh_call"
                else:
                    messages = [{"role": "user", "content": branch_prompt(question["problem"])}]; budget, temperature, context = args.branch_budget, 0.7, "independent_branch"
                response = call_ollama(model, messages, budget, temperature)
                row = make_record(args.stage, model, question, action, budget, response, prefix=prefix, context_mode=context)
                if key in existing:
                    records.remove(existing[key])
                records.append(row); existing[key] = row; atomic_write(args.raw, checkpoint)
                print(f"{model} {question['id']} {action} tok={row['completion_tokens']} err={row['error']}")
                time.sleep(args.sleep_seconds)
    print(f"Done. Wrote {len(records)} action records to {args.raw}")


if __name__ == "__main__":
    main()
