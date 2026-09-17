#!/usr/bin/env python3
"""Create a reproducible, held-out MATH-500 question manifest for Stage 2.

This script makes no model/API calls.  It excludes every MATH-500 identifier
already found in ``data/*.json`` before sampling the Gate 0, Gate 1, and formal
pilot splits.  Review the generated manifest before running the API runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = SCRIPT_DIR / "data"
DEFAULT_OUTPUT = DEFAULT_DATA / "process_stage2_questions.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--gate0-count", type=int, default=10)
    parser.add_argument("--gate1-count", type=int, default=20)
    parser.add_argument("--formal-count", type=int, default=60)
    return parser.parse_args()


def collect_ids(value: object) -> set[str]:
    """Find MATH-500 ids without assuming every historic JSON schema is alike."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"id", "question_id"} and isinstance(child, str) and child.startswith("test/"):
                found.add(child)
            found.update(collect_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_ids(child))
    return found


def historic_ids(data_dir: Path, output: Path) -> set[str]:
    excluded: set[str] = set()
    for path in sorted(data_dir.glob("*.json")):
        if path.resolve() == output.resolve():
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                excluded.update(collect_ids(json.load(handle)))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot inspect historic question file {path}: {exc}") from exc
    return excluded


def stratified_take(pool: list[dict], count: int, rng: random.Random) -> list[dict]:
    if count < 1:
        return []
    by_level = {level: [row for row in pool if int(row["level"]) == level] for level in (3, 4)}
    need_l3 = count // 2
    need_l4 = count - need_l3
    if len(by_level[3]) < need_l3 or len(by_level[4]) < need_l4:
        raise ValueError("Not enough unseen level-3/4 MATH-500 questions for requested split")
    selected = rng.sample(by_level[3], need_l3) + rng.sample(by_level[4], need_l4)
    rng.shuffle(selected)
    return selected


def fingerprint(rows: list[dict]) -> str:
    payload = "\n".join(row["id"] for row in rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    args = parse_args()
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Missing dependency 'datasets'. Install project dependencies before preparing Stage 2.") from exc

    excluded = historic_ids(args.data_dir, args.output)
    dataset = load_dataset("HuggingFaceH4/MATH-500", split="test")
    candidates = [
        {"id": row["unique_id"], "problem": row["problem"], "answer": row["answer"],
         "level": int(row["level"]), "subject": row["subject"]}
        for row in dataset
        if int(row["level"]) in (3, 4) and row["unique_id"] not in excluded
    ]
    rng = random.Random(args.seed)
    remaining = list(candidates)
    splits: dict[str, list[dict]] = {}
    for name, count in (("gate0", args.gate0_count), ("gate1", args.gate1_count), ("formal", args.formal_count)):
        split = stratified_take(remaining, count, rng)
        selected_ids = {row["id"] for row in split}
        remaining = [row for row in remaining if row["id"] not in selected_ids]
        splits[name] = split

    all_rows = [row for name in ("gate0", "gate1", "formal") for row in splits[name]]
    payload = {
        "schema_version": 1,
        "dataset": "HuggingFaceH4/MATH-500:test",
        "seed": args.seed,
        "excluded_historic_question_count": len(excluded),
        "splits": splits,
        "all_question_ids_sha256": fingerprint(all_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {len(all_rows)} held-out questions to {args.output}")
    print(f"Excluded historic ids: {len(excluded)}; manifest SHA-256: {payload['all_question_ids_sha256']}")


if __name__ == "__main__":
    main()
