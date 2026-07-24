#!/usr/bin/env python3
"""Validate that the canonical V2 reproducibility artifacts are complete."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "experiments" / "v2-mmlu-arc" / "results"
REQUIRED_FILES = (
    "raw_responses_v2.json",
    "traces_final.json",
    "calibration_final.json",
    "conformance_final.json",
    "conformance_deepseek_ref.json",
    "discovery_final.json",
    "entropy_step_analysis.json",
    "full_metrics_final.csv",
)


def is_symmetric(matrix, tolerance=1e-12):
    if any(len(row) != len(matrix) for row in matrix):
        return False
    return all(
        abs(matrix[row][column] - matrix[column][row]) <= tolerance
        for row in range(len(matrix))
        for column in range(len(matrix))
    )


def main() -> int:
    problems = []
    for filename in REQUIRED_FILES:
        path = RESULTS_DIR / filename
        if not path.is_file():
            problems.append(f"Missing: {filename}")

    entropy_path = RESULTS_DIR / "entropy_step_analysis.json"
    if entropy_path.is_file():
        entropy = json.loads(entropy_path.read_text())
        matrix = entropy.get("A3_levenshtein_distance", {}).get("matrix")
        if matrix is None or not is_symmetric(matrix):
            problems.append("Invalid: Levenshtein matrix is not symmetric")
        elif any(abs(matrix[index][index]) > 1e-12 for index in range(len(matrix))):
            problems.append("Invalid: Levenshtein matrix diagonal is not zero")

    if problems:
        print("V2 result set is not ready:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("V2 result set is complete and structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

