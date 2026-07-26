#!/usr/bin/env python3
"""Export a deterministic, model-balanced sample for human activity annotation."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import random

from experiment_v2 import MODELS, label_step, segment_cot


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "results" / "raw_responses_v2.json"
DEFAULT_OUTPUT = BASE_DIR / "results" / "activity_label_sample.csv"
FIELDNAMES = (
    "sample_id",
    "model",
    "question_id",
    "benchmark",
    "step_index",
    "step_text",
    "predicted_activity",
    "human_activity",
    "reviewer",
    "notes",
)


def collect_candidates(raw_results):
    candidates = {}
    for _, model_name in MODELS:
        model_candidates = []
        for response in raw_results.get(model_name, []):
            if response.get("error"):
                continue
            full_cot = "\n\n".join(
                part
                for part in (response.get("thinking", ""), response.get("response", ""))
                if part
            )
            for step_index, step_text in enumerate(segment_cot(full_cot)):
                model_candidates.append(
                    {
                        "model": model_name,
                        "question_id": response.get("question_id", ""),
                        "benchmark": response.get("benchmark", ""),
                        "step_index": step_index,
                        "step_text": step_text,
                        "predicted_activity": label_step(step_text),
                        "human_activity": "",
                        "reviewer": "",
                        "notes": "",
                    }
                )
        candidates[model_name] = model_candidates
    return candidates


def sample_candidates(candidates, sample_size, seed):
    if sample_size < 1:
        raise ValueError("sample_size must be positive")

    rng = random.Random(seed)
    model_names = [model_name for _, model_name in MODELS]
    per_model, remainder = divmod(sample_size, len(model_names))
    selected = []
    for model_index, model_name in enumerate(model_names):
        target = per_model + (1 if model_index < remainder else 0)
        population = candidates.get(model_name, [])
        if len(population) < target:
            raise ValueError(
                f"{model_name} has only {len(population)} candidate steps; {target} requested"
            )

        by_activity = {}
        for row in population:
            by_activity.setdefault(row["predicted_activity"], []).append(row)
        activities = sorted(by_activity)
        rng.shuffle(activities)
        model_selection = [
            rng.choice(by_activity[activity])
            for activity in activities[:target]
        ]
        selected_ids = {id(row) for row in model_selection}
        remaining = [row for row in population if id(row) not in selected_ids]
        model_selection.extend(rng.sample(remaining, target - len(model_selection)))
        selected.extend(model_selection)

    rng.shuffle(selected)
    for sample_index, row in enumerate(selected, start=1):
        row["sample_id"] = f"S{sample_index:03d}"
    return selected


def export_sample(input_path, output_path, sample_size=100, seed=42):
    raw_results = json.loads(Path(input_path).read_text())
    candidates = collect_candidates(raw_results)
    selected = sample_candidates(candidates, sample_size, seed)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temporary_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(selected)
    os.replace(temporary_path, output_path)
    return selected


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    selected = export_sample(args.input, args.output, args.sample_size, args.seed)
    counts = {}
    for row in selected:
        counts[row["model"]] = counts.get(row["model"], 0) + 1
    print(f"Exported {len(selected)} steps to {args.output}")
    for model_name, count in counts.items():
        print(f"- {model_name}: {count}")


if __name__ == "__main__":
    main()
