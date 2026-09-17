#!/usr/bin/env python3
"""Create a reproducible Stage 3 manifest without reusing historic MATH-500 IDs.

This script makes no model/API calls.  Before writing the manifest it scans all
JSON files under this experiment's data/ and results/ trees for ``id`` and
``question_id`` values that look like MATH-500 test IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_RESULTS_DIR = SCRIPT_DIR / "results"
DEFAULT_OUTPUT = DEFAULT_DATA_DIR / "process_stage3_questions.json"
DEFAULT_SEED = 20260918


def collect_question_ids(value: Any) -> set[str]:
    """Recursively find canonical MATH-500 test IDs in arbitrary JSON."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"id", "question_id"} and isinstance(child, str) and child.startswith("test/"):
                found.add(child)
            found.update(collect_question_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_question_ids(child))
    return found


def historic_ids(paths: list[Path], output: Path) -> tuple[set[str], list[str]]:
    """Read historic JSON sources, refusing unreadable/corrupt files."""
    excluded: set[str] = set()
    inspected: list[str] = []
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if path.resolve() == output.resolve():
                continue
            try:
                with path.open(encoding="utf-8") as handle:
                    excluded.update(collect_question_ids(json.load(handle)))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Cannot inspect historic JSON {path}: {exc}") from exc
            try:
                inspected.append(str(path.relative_to(SCRIPT_DIR)))
            except ValueError:
                # Keep the helper usable in tests and for an explicitly supplied
                # external archive directory.
                inspected.append(str(path))
    return excluded, inspected


def fingerprint(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256("\n".join(row["id"] for row in rows).encode("utf-8")).hexdigest()


def stratified_take(pool: list[dict[str, Any]], count: int, rng: random.Random) -> list[dict[str, Any]]:
    if count < 1:
        return []
    counts = {3: count // 2, 4: count - count // 2}
    selected: list[dict[str, Any]] = []
    for level, need in counts.items():
        candidates = [row for row in pool if int(row["level"]) == level]
        if len(candidates) < need:
            raise ValueError(f"Need {need} unused level-{level} questions; found {len(candidates)}")
        selected.extend(rng.sample(candidates, need))
    rng.shuffle(selected)
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--smoke-count", type=int, default=4)
    parser.add_argument("--formal-count", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.smoke_count != 4 or args.formal_count != 60:
        raise SystemExit("Stage 3 is frozen at 4 smoke and 60 formal questions.")
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Missing dependency 'datasets'; install dependencies before preparing data.") from exc

    excluded, inspected = historic_ids([args.data_dir, args.results_dir], args.output)
    dataset = load_dataset("HuggingFaceH4/MATH-500", split="test")
    candidates = [
        {
            "id": row["unique_id"],
            "problem": row["problem"],
            "answer": row["answer"],
            "level": int(row["level"]),
            "subject": row["subject"],
        }
        for row in dataset
        if int(row["level"]) in (3, 4) and row["unique_id"] not in excluded
    ]
    rng = random.Random(args.seed)
    smoke = stratified_take(candidates, args.smoke_count, rng)
    smoke_ids = {row["id"] for row in smoke}
    formal = stratified_take([row for row in candidates if row["id"] not in smoke_ids], args.formal_count, rng)
    all_rows = smoke + formal
    if len({row["id"] for row in all_rows}) != len(all_rows):
        raise RuntimeError("Manifest construction generated duplicate question IDs.")
    if any(row["id"] in excluded for row in all_rows):
        raise RuntimeError("Manifest construction leaked a historic question ID.")

    payload = {
        "schema_version": 1,
        "dataset": "HuggingFaceH4/MATH-500:test",
        "seed": args.seed,
        "selection": {"levels": [3, 4], "smoke_count": 4, "formal_count": 60},
        "excluded_historic_question_count": len(excluded),
        "historic_json_files_inspected": inspected,
        "splits": {"smoke": smoke, "formal": formal},
        "all_question_ids_sha256": fingerprint(all_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {len(all_rows)} new held-out questions: {args.output}")
    print(f"Excluded {len(excluded)} historic IDs; sha256={payload['all_question_ids_sha256']}")


if __name__ == "__main__":
    main()
