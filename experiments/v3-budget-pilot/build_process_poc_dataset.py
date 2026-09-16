#!/usr/bin/env python3
"""Build the offline process-allocation PoC dataset from Phase 3 raw responses.

This script performs no API calls.  It deliberately re-scores answers from raw
response text instead of trusting historical ``correct`` fields.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from answer_utils import extract_boxed, is_correct  # noqa: E402
from process_event_extractor import (  # noqa: E402
    activity_sequence,
    base_process_features,
    extract_events,
)


DEFAULT_RAW = SCRIPT_DIR / "results" / "phase3_raw.json"
DEFAULT_QUESTIONS = SCRIPT_DIR / "data" / "phase3_questions.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "results" / "process_poc_dataset.json"
DEFAULT_AUDIT = SCRIPT_DIR / "results" / "process_poc_dataset_audit.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--low-budget", type=int, default=512)
    parser.add_argument("--high-budget", type=int, default=1024)
    return parser.parse_args()


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required input is missing: {path}\n"
            "The repository does not currently track phase3_raw.json. Copy the original "
            "Phase 3 raw artifact to this path or pass --raw /path/to/file."
        )
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def key(row: dict) -> tuple[str, str, int]:
    return row["model"], row["question_id"], int(row["replicate"])


def index_unique(rows: list[dict], call_type: str, budget: int) -> dict[tuple, dict]:
    selected = [
        row
        for row in rows
        if row.get("call_type") == call_type and int(row.get("budget", -1)) == budget
    ]
    indexed: dict[tuple, dict] = {}
    duplicates = []
    for row in selected:
        row_key = key(row)
        if row_key in indexed:
            duplicates.append(row_key)
        indexed[row_key] = row
    if duplicates:
        examples = ", ".join(map(str, duplicates[:5]))
        raise ValueError(f"Duplicate {call_type} rows at budget {budget}: {examples}")
    return indexed


def rescore(row: dict) -> tuple[bool, str]:
    content = row.get("content") or row.get("response") or ""
    parsed = extract_boxed(content) or ""
    expected = row.get("expected_answer") or ""
    return is_correct(parsed, expected), parsed


def common_prefix_ratio(left: str, right: str) -> float:
    denominator = max(1, min(len(left), len(right)))
    common = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        common += 1
    return common / denominator


def make_record(
    row_key: tuple,
    low: dict,
    high: dict,
    confidence: dict | None,
    question: dict,
    low_budget: int,
    high_budget: int,
) -> dict:
    low_correct, low_answer = rescore(low)
    high_correct, high_answer = rescore(high)
    low_content = low.get("content") or low.get("response") or ""
    high_content = high.get("content") or high.get("response") or ""
    events = extract_events(low_content)
    sequence = activity_sequence(events)
    process_features = base_process_features(events)
    low_tokens = int(low.get("completion_tokens") or 0)
    high_tokens = int(high.get("completion_tokens") or 0)
    confidence_value = None if confidence is None else confidence.get("confidence_value")
    confidence_prompt_tokens = 0 if confidence is None else int(
        confidence.get("prompt_tokens") or 0
    )
    confidence_completion_tokens = 0 if confidence is None else int(
        confidence.get("completion_tokens") or 0
    )
    return {
        "case_id": "|".join(map(str, row_key)),
        "model": row_key[0],
        "question_id": row_key[1],
        "replicate": row_key[2],
        "level": int(question.get("level", low.get("level", 0)) or 0),
        "subject": question.get("subject", low.get("subject", "unknown")),
        "question_chars": len(question.get("problem", "")),
        "low_budget": low_budget,
        "high_budget": high_budget,
        "low_completion_tokens": low_tokens,
        "high_completion_tokens": high_tokens,
        "incremental_token_proxy": max(0, high_tokens - low_tokens),
        "low_near_cap": int(low_tokens >= low_budget * 0.98),
        "low_correct": int(low_correct),
        "high_correct": int(high_correct),
        "gain": int(high_correct) - int(low_correct),
        "benefit": int(not low_correct and high_correct),
        "harm": int(low_correct and not high_correct),
        "low_parsed_answer": low_answer,
        "high_parsed_answer": high_answer,
        "low_has_parsed_answer": int(bool(low_answer)),
        "confidence": confidence_value,
        "confidence_missing": int(confidence_value is None),
        "confidence_prompt_tokens": confidence_prompt_tokens,
        "confidence_completion_tokens": confidence_completion_tokens,
        "confidence_total_tokens": confidence_prompt_tokens + confidence_completion_tokens,
        "prefix_similarity": common_prefix_ratio(low_content, high_content),
        "activity_sequence": sequence,
        "process_features": process_features,
    }


def audit_markdown(records: list[dict], metadata: dict) -> str:
    models = sorted({record["model"] for record in records})
    lines = [
        "# Process-allocation PoC dataset audit",
        "",
        "> Generated from raw Phase 3 responses; no API calls are made.",
        "",
        "## Pairing",
        "",
        f"- Paired rows: **{len(records)}**",
        f"- Unique questions: **{len({r['question_id'] for r in records})}**",
        f"- Models: **{len(models)}**",
        f"- Missing confidence rows: **{sum(r['confidence_missing'] for r in records)}**",
        f"- Low/high budgets: **{metadata['low_budget']} → {metadata['high_budget']}**",
        "",
        "## Outcome distribution",
        "",
        "| Model | n | Low acc. | High acc. | Benefit | Harm | Median prefix similarity |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in models:
        rows = [record for record in records if record["model"] == model]
        lines.append(
            "| {model} | {n} | {low:.1%} | {high:.1%} | {benefit:.1%} | "
            "{harm:.1%} | {prefix:.3f} |".format(
                model=model,
                n=len(rows),
                low=statistics.mean(row["low_correct"] for row in rows),
                high=statistics.mean(row["high_correct"] for row in rows),
                benefit=statistics.mean(row["benefit"] for row in rows),
                harm=statistics.mean(row["harm"] for row in rows),
                prefix=statistics.median(row["prefix_similarity"] for row in rows),
            )
        )
    benefit_count = Counter(record["benefit"] for record in records)
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- `benefit=1` means the independently generated low-budget answer was wrong and "
            "the high-budget answer was correct.",
            "- Phase 3 did not resume the same generation. The gain is therefore an "
            "observational counterfactual proxy, not a causal continuation effect.",
            "- `incremental_token_proxy` must not be presented as measured continuation cost.",
            "- Process features use only the low-budget response.",
            "- Cross-validation must group all rows sharing a question ID.",
            "",
            f"Class counts: no benefit={benefit_count[0]}, benefit={benefit_count[1]}.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.low_budget >= args.high_budget:
        raise ValueError("--low-budget must be lower than --high-budget")
    rows = load_json(args.raw)
    questions = load_json(args.questions)
    question_map = {question["id"]: question for question in questions}

    low_answers = index_unique(rows, "answer", args.low_budget)
    high_answers = index_unique(rows, "answer", args.high_budget)
    low_confidence = index_unique(rows, "confidence", args.low_budget)
    paired_keys = sorted(set(low_answers) & set(high_answers))
    missing_low = sorted(set(high_answers) - set(low_answers))
    missing_high = sorted(set(low_answers) - set(high_answers))
    if missing_low or missing_high:
        raise ValueError(
            f"Unpaired answer rows: missing_low={len(missing_low)}, "
            f"missing_high={len(missing_high)}"
        )
    if not paired_keys:
        raise ValueError("No paired low/high answer rows were found")

    records = []
    for row_key in paired_keys:
        question_id = row_key[1]
        if question_id not in question_map:
            raise KeyError(f"Question metadata missing for {question_id}")
        records.append(
            make_record(
                row_key=row_key,
                low=low_answers[row_key],
                high=high_answers[row_key],
                confidence=low_confidence.get(row_key),
                question=question_map[question_id],
                low_budget=args.low_budget,
                high_budget=args.high_budget,
            )
        )

    metadata = {
        "schema_version": 1,
        "source": str(args.raw),
        "low_budget": args.low_budget,
        "high_budget": args.high_budget,
        "record_count": len(records),
        "unit": "model-question-replicate",
        "target": "benefit = low incorrect and high correct",
        "warning": (
            "Low and high outcomes come from independent Phase 3 calls; this is an "
            "offline predictive-feasibility dataset, not a causal continuation trial."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "records": records}, handle, indent=2)
    args.audit.write_text(audit_markdown(records, metadata), encoding="utf-8")
    print(f"Wrote {len(records)} paired records to {args.output}")
    print(f"Wrote audit report to {args.audit}")


if __name__ == "__main__":
    main()
