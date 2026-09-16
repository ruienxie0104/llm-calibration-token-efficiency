#!/usr/bin/env python3
"""Evaluate whether process-prefix features predict additional-compute benefit.

The analysis is offline and makes no API calls.  All test predictions are
out-of-fold.  Process models are fitted only on each training fold.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from process_event_extractor import (  # noqa: E402
    dfg_conformance_features,
    fit_dfg,
)


DEFAULT_INPUT = SCRIPT_DIR / "results" / "process_poc_dataset.json"
DEFAULT_JSON = SCRIPT_DIR / "results" / "process_poc_analysis.json"
DEFAULT_REPORT = SCRIPT_DIR / "results" / "process_poc_report.md"
DEFAULT_FIGURE = SCRIPT_DIR / "results" / "process_poc_accuracy_cost.png"
FEATURE_SETS = ("M0_context", "M1_runtime", "M2_confidence", "M3_process", "M4_combined")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=1000)
    return parser.parse_args()


def load_records(path: Path) -> tuple[dict, list[dict]]:
    if not path.exists():
        raise FileNotFoundError(
            f"PoC dataset not found: {path}\nRun build_process_poc_dataset.py first."
        )
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records", [])
    if not records:
        raise ValueError("PoC dataset contains no records")
    return payload.get("metadata", {}), records


def grouped_folds(records: list[dict], n_folds: int, seed: int) -> list[tuple[list[int], list[int]]]:
    """Greedily balance question groups while keeping each question in one fold."""
    groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        groups[record["question_id"]].append(index)
    if len(groups) < n_folds:
        raise ValueError(f"Need at least {n_folds} unique questions; found {len(groups)}")
    rng = random.Random(seed)
    group_items = list(groups.items())
    rng.shuffle(group_items)
    group_items.sort(
        key=lambda item: sum(records[index]["benefit"] for index in item[1]), reverse=True
    )
    bins = [{"groups": [], "positive": 0, "rows": 0} for _ in range(n_folds)]
    for group_id, indices in group_items:
        destination = min(bins, key=lambda item: (item["positive"], item["rows"]))
        destination["groups"].append(group_id)
        destination["positive"] += sum(records[index]["benefit"] for index in indices)
        destination["rows"] += len(indices)
    all_indices = set(range(len(records)))
    folds = []
    for fold in bins:
        test = sorted(index for group in fold["groups"] for index in groups[group])
        train = sorted(all_indices - set(test))
        folds.append((train, test))
    return folds


def leave_one_model_out(records: list[dict]) -> list[tuple[list[int], list[int], str]]:
    folds = []
    for model in sorted({record["model"] for record in records}):
        test = [index for index, record in enumerate(records) if record["model"] == model]
        train = [index for index, record in enumerate(records) if record["model"] != model]
        folds.append((train, test, model))
    return folds


def fold_process_features(
    records: list[dict], train_indices: list[int], target_indices: list[int]
) -> dict[int, dict[str, float]]:
    all_sequences = [records[index]["activity_sequence"] for index in train_indices]
    benefit_sequences = [
        records[index]["activity_sequence"]
        for index in train_indices
        if records[index]["benefit"] == 1
    ]
    no_benefit_sequences = [
        records[index]["activity_sequence"]
        for index in train_indices
        if records[index]["benefit"] == 0
    ]
    # Empty class models are still valid Laplace-smoothed DFGs.
    all_dfg = fit_dfg(all_sequences)
    benefit_dfg = fit_dfg(benefit_sequences)
    no_benefit_dfg = fit_dfg(no_benefit_sequences)
    output = {}
    for index in target_indices:
        output[index] = dfg_conformance_features(
            records[index]["activity_sequence"], all_dfg, benefit_dfg, no_benefit_dfg
        )
    return output


def feature_dict(record: dict, feature_set: str, dfg: dict[str, float]) -> dict[str, float]:
    features = {
        "level": float(record["level"]),
        "question_chars": float(record["question_chars"]),
        f"model::{record['model']}": 1.0,
        f"subject::{record['subject']}": 1.0,
    }
    if feature_set != "M0_context":
        features.update(
            {
                "low_completion_tokens": float(record["low_completion_tokens"]),
                "low_token_fraction": float(record["low_completion_tokens"])
                / max(1.0, float(record["low_budget"])),
                "low_near_cap": float(record["low_near_cap"]),
                "low_has_parsed_answer": float(record["low_has_parsed_answer"]),
            }
        )
    if feature_set in {"M2_confidence", "M4_combined"}:
        confidence = record.get("confidence")
        features["confidence"] = 0.0 if confidence is None else float(confidence) / 100.0
        features["confidence_missing"] = float(record.get("confidence_missing", 0))
    if feature_set in {"M3_process", "M4_combined"}:
        features.update({key: float(value) for key, value in record["process_features"].items()})
        features.update(dfg)
    return features


class FeatureEncoder:
    def __init__(self) -> None:
        self.keys: list[str] = []
        self.mean: np.ndarray | None = None
        self.scale: np.ndarray | None = None

    def fit_transform(self, rows: list[dict[str, float]]) -> np.ndarray:
        self.keys = sorted({key for row in rows for key in row})
        matrix = self._matrix(rows)
        self.mean = matrix.mean(axis=0)
        self.scale = matrix.std(axis=0)
        self.scale[self.scale < 1e-12] = 1.0
        return (matrix - self.mean) / self.scale

    def transform(self, rows: list[dict[str, float]]) -> np.ndarray:
        if self.mean is None or self.scale is None:
            raise RuntimeError("FeatureEncoder must be fitted before transform")
        return (self._matrix(rows) - self.mean) / self.scale

    def _matrix(self, rows: list[dict[str, float]]) -> np.ndarray:
        return np.asarray([[row.get(key, 0.0) for key in self.keys] for row in rows], dtype=float)


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -35, 35)
    return 1.0 / (1.0 + np.exp(-values))


def fit_logistic(features: np.ndarray, target: np.ndarray, l2: float = 1.0) -> np.ndarray:
    design = np.column_stack([np.ones(len(features)), features])
    if len(np.unique(target)) < 2:
        prevalence = float(np.clip(target.mean(), 1e-6, 1 - 1e-6))
        weights = np.zeros(design.shape[1])
        weights[0] = math.log(prevalence / (1 - prevalence))
        return weights

    def objective(weights: np.ndarray) -> tuple[float, np.ndarray]:
        probability = sigmoid(design @ weights)
        loss = -np.mean(
            target * np.log(np.clip(probability, 1e-12, 1.0))
            + (1 - target) * np.log(np.clip(1 - probability, 1e-12, 1.0))
        )
        loss += 0.5 * l2 * float(weights[1:] @ weights[1:]) / len(target)
        gradient = design.T @ (probability - target) / len(target)
        gradient[1:] += l2 * weights[1:] / len(target)
        return loss, gradient

    result = minimize(
        objective,
        np.zeros(design.shape[1]),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 1000},
    )
    if not result.success:
        raise RuntimeError(f"Logistic regression failed: {result.message}")
    return result.x


def predict_logistic(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(features)), features])
    return sigmoid(design @ weights)


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    cursor = 0
    while cursor < len(values):
        end = cursor + 1
        while end < len(values) and values[order[end]] == values[order[cursor]]:
            end += 1
        average = (cursor + 1 + end) / 2.0
        ranks[order[cursor:end]] = average
        cursor = end
    return ranks


def roc_auc(target: np.ndarray, score: np.ndarray) -> float | None:
    positive = int(target.sum())
    negative = len(target) - positive
    if not positive or not negative:
        return None
    ranks = average_ranks(score)
    return float((ranks[target == 1].sum() - positive * (positive + 1) / 2) / (positive * negative))


def average_precision(target: np.ndarray, score: np.ndarray) -> float | None:
    positive = int(target.sum())
    if not positive:
        return None
    order = np.argsort(-score, kind="mergesort")
    sorted_target = target[order]
    precision = np.cumsum(sorted_target) / np.arange(1, len(target) + 1)
    return float((precision * sorted_target).sum() / positive)


def metrics(target: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
    clipped = np.clip(score, 1e-12, 1 - 1e-12)
    return {
        "n": int(len(target)),
        "prevalence": float(target.mean()),
        "pr_auc": average_precision(target, score),
        "roc_auc": roc_auc(target, score),
        "brier": float(np.mean((score - target) ** 2)),
        "log_loss": float(-np.mean(target * np.log(clipped) + (1 - target) * np.log(1 - clipped))),
    }


def cross_validated_predictions(
    records: list[dict], folds: list[tuple[list[int], list[int]]]
) -> dict[str, np.ndarray]:
    predictions = {feature_set: np.full(len(records), np.nan) for feature_set in FEATURE_SETS}
    covered_indices: set[int] = set()
    for train_indices, test_indices in folds:
        overlap = covered_indices & set(test_indices)
        if overlap:
            raise ValueError(f"Test rows appeared in multiple folds: {sorted(overlap)[:5]}")
        covered_indices.update(test_indices)
        dfg_train = fold_process_features(records, train_indices, train_indices)
        dfg_test = fold_process_features(records, train_indices, test_indices)
        target = np.asarray([records[index]["benefit"] for index in train_indices], dtype=float)
        for feature_set in FEATURE_SETS:
            train_rows = [
                feature_dict(records[index], feature_set, dfg_train[index])
                for index in train_indices
            ]
            test_rows = [
                feature_dict(records[index], feature_set, dfg_test[index])
                for index in test_indices
            ]
            encoder = FeatureEncoder()
            train_matrix = encoder.fit_transform(train_rows)
            test_matrix = encoder.transform(test_rows)
            weights = fit_logistic(train_matrix, target)
            predictions[feature_set][test_indices] = predict_logistic(test_matrix, weights)
    covered = sorted(covered_indices)
    if any(np.isnan(values[covered]).any() for values in predictions.values()):
        raise RuntimeError("At least one row did not receive an out-of-fold prediction")
    return predictions


def model_generalization(records: list[dict]) -> dict[str, dict[str, dict]]:
    output = {}
    for train_indices, test_indices, held_out_model in leave_one_model_out(records):
        predictions = cross_validated_predictions(records, [(train_indices, test_indices)])
        target = np.asarray([records[index]["benefit"] for index in test_indices], dtype=int)
        output[held_out_model] = {
            feature_set: metrics(target, values[test_indices])
            for feature_set, values in predictions.items()
        }
    return output


def allocation_row(
    records: list[dict], selected: set[int], include_confidence_cost: bool
) -> dict[str, float]:
    final_correct = []
    total_cost = []
    for index, record in enumerate(records):
        upgraded = index in selected
        final_correct.append(record["high_correct"] if upgraded else record["low_correct"])
        cost = float(record["low_completion_tokens"])
        if upgraded:
            cost += float(record["incremental_token_proxy"])
        if include_confidence_cost:
            cost += float(record["confidence_total_tokens"])
        total_cost.append(cost)
    return {
        "accuracy": float(np.mean(final_correct)),
        "mean_token_proxy": float(np.mean(total_cost)),
        "upgraded": len(selected),
        "upgrade_rate": len(selected) / len(records),
    }


def simulate_policies(
    records: list[dict], predictions: dict[str, np.ndarray], rates=(0.25, 0.5, 0.75)
) -> dict:
    output: dict[str, dict] = {
        "fixed_low": allocation_row(records, set(), False),
        "fixed_high": allocation_row(records, set(range(len(records))), False),
        "rates": {},
        "cost_warning": (
            "incremental_token_proxy is high_completion_tokens-low_completion_tokens. "
            "It is not a measured continuation cost because Phase 3 calls were independent."
        ),
    }
    gain = np.asarray([record["gain"] for record in records])
    for rate in rates:
        count = max(1, round(rate * len(records)))
        rate_output = {}
        oracle_order = np.argsort(-gain, kind="mergesort")
        rate_output["oracle"] = allocation_row(records, set(oracle_order[:count]), False)
        expected_random_accuracy = float(
            np.mean(
                [
                    (1 - rate) * record["low_correct"] + rate * record["high_correct"]
                    for record in records
                ]
            )
        )
        expected_random_cost = float(
            np.mean(
                [
                    record["low_completion_tokens"] + rate * record["incremental_token_proxy"]
                    for record in records
                ]
            )
        )
        rate_output["random_expected"] = {
            "accuracy": expected_random_accuracy,
            "mean_token_proxy": expected_random_cost,
            "upgrade_rate": rate,
        }
        for feature_set, scores in predictions.items():
            order = np.argsort(-scores, kind="mergesort")
            rate_output[feature_set] = allocation_row(
                records,
                set(order[:count]),
                include_confidence_cost=feature_set in {"M2_confidence", "M4_combined"},
            )
        output["rates"][str(rate)] = rate_output
    return output


def bootstrap_delta(
    records: list[dict], left: np.ndarray, right: np.ndarray, draws: int, seed: int
) -> dict[str, float | None]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        groups[record["question_id"]].append(index)
    group_ids = sorted(groups)
    rng = random.Random(seed)
    deltas = []
    for _ in range(draws):
        sampled = [rng.choice(group_ids) for _ in group_ids]
        indices = [index for group_id in sampled for index in groups[group_id]]
        target = np.asarray([records[index]["benefit"] for index in indices], dtype=int)
        left_value = average_precision(target, left[indices])
        right_value = average_precision(target, right[indices])
        if left_value is not None and right_value is not None:
            deltas.append(left_value - right_value)
    if not deltas:
        return {"estimate": None, "ci_low": None, "ci_high": None}
    values = np.asarray(deltas)
    return {
        "estimate": float(average_precision(
            np.asarray([record["benefit"] for record in records]), left
        ) - average_precision(
            np.asarray([record["benefit"] for record in records]), right
        )),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
    }


def make_figure(policies: dict, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    styles = {
        "M1_runtime": "o-",
        "M2_confidence": "s-",
        "M3_process": "^-",
        "M4_combined": "D-",
        "oracle": "*-",
        "random_expected": "x--",
    }
    for policy, style in styles.items():
        points = [values[policy] for values in policies["rates"].values()]
        plt.plot(
            [point["mean_token_proxy"] for point in points],
            [point["accuracy"] for point in points],
            style,
            label=policy,
        )
    plt.scatter(
        [policies["fixed_low"]["mean_token_proxy"], policies["fixed_high"]["mean_token_proxy"]],
        [policies["fixed_low"]["accuracy"], policies["fixed_high"]["accuracy"]],
        color="black",
        label="fixed endpoints",
    )
    plt.xlabel("Mean completion-token proxy per case")
    plt.ylabel("Final accuracy")
    plt.title("Offline matched-cost allocation simulation")
    plt.grid(alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=180)
    plt.close()


def fmt(value) -> str:
    return "NA" if value is None else f"{value:.3f}"


def make_report(metadata: dict, analysis: dict, figure: Path) -> str:
    lines = [
        "# Process-prefix value PoC report",
        "",
        "> Offline predictive-feasibility analysis. Phase 3 low/high outputs were independent calls.",
        "",
        "## Dataset",
        "",
        f"- Records: **{analysis['record_count']}**",
        f"- Positive benefit prevalence: **{analysis['benefit_prevalence']:.1%}**",
        f"- Budget comparison: **{metadata.get('low_budget')} → {metadata.get('high_budget')}**",
        "",
        "## Grouped out-of-fold prediction",
        "",
        "| Feature set | PR-AUC | AUROC | Brier | Log loss |",
        "|---|---:|---:|---:|---:|",
    ]
    for feature_set in FEATURE_SETS:
        result = analysis["grouped_cv"][feature_set]
        lines.append(
            f"| {feature_set} | {fmt(result['pr_auc'])} | {fmt(result['roc_auc'])} | "
            f"{fmt(result['brier'])} | {fmt(result['log_loss'])} |"
        )
    delta = analysis["combined_vs_confidence_pr_auc"]
    lines.extend(
        [
            "",
            "## Primary incremental-value contrast",
            "",
            "M4 combined minus M2 confidence PR-AUC: "
            f"**{fmt(delta['estimate'])}**, clustered bootstrap 95% CI "
            f"[{fmt(delta['ci_low'])}, {fmt(delta['ci_high'])}].",
            "",
            "## Matched-cost allocation",
            "",
            "| Upgrade rate | Policy | Accuracy | Mean token proxy |",
            "|---:|---|---:|---:|",
        ]
    )
    for rate, policy_results in analysis["policies"]["rates"].items():
        for policy in ("random_expected", "M2_confidence", "M3_process", "M4_combined", "oracle"):
            result = policy_results[policy]
            lines.append(
                f"| {float(rate):.0%} | {policy} | {result['accuracy']:.1%} | "
                f"{result['mean_token_proxy']:.1f} |"
            )
    lines.extend(
        [
            "",
            f"![Accuracy-cost simulation]({figure.name})",
            "",
            "## Required interpretation",
            "",
            "- M4 must be compared with the strongest non-process baseline, not with random alone.",
            "- Confidence-call prompt and completion tokens are charged to M2 and M4.",
            "- A positive offline result justifies an interventional continuation pilot; it does not "
            "establish a causal online allocation benefit.",
            "- If answer presence alone explains the target, process mining has not shown incremental value.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    metadata, records = load_records(args.input)
    target = np.asarray([record["benefit"] for record in records], dtype=int)
    if len(np.unique(target)) < 2:
        raise ValueError("Benefit target has only one class; predictive PoC is not identifiable")

    folds = grouped_folds(records, args.folds, args.seed)
    predictions = cross_validated_predictions(records, folds)
    grouped_results = {
        feature_set: metrics(target, values) for feature_set, values in predictions.items()
    }
    analysis = {
        "schema_version": 1,
        "record_count": len(records),
        "benefit_prevalence": float(target.mean()),
        "grouped_cv": grouped_results,
        "leave_one_model_out": model_generalization(records),
        "combined_vs_confidence_pr_auc": bootstrap_delta(
            records,
            predictions["M4_combined"],
            predictions["M2_confidence"],
            args.bootstrap,
            args.seed,
        ),
        "policies": simulate_policies(records, predictions),
        "guardrail": (
            "All predictions are out-of-fold by question_id. DFG models are fitted on training "
            "folds only. Phase 3 low/high calls are not a resumed trajectory."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "analysis": analysis}, handle, indent=2)
    make_figure(analysis["policies"], args.figure)
    args.report.write_text(make_report(metadata, analysis, args.figure), encoding="utf-8")
    print(f"Wrote analysis JSON to {args.output}")
    print(f"Wrote report to {args.report}")
    print(f"Wrote figure to {args.figure}")


if __name__ == "__main__":
    main()
