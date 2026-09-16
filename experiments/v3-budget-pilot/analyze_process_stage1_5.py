#!/usr/bin/env python3
"""Stage 1.5 robustness analysis for process-aware compute allocation.

This script makes no API calls.  It tests whether process structure remains useful
after removing answer/conclusion shortcuts and conditioning on unfinished cases.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from analyze_process_value import (  # noqa: E402
    FeatureEncoder,
    bootstrap_delta,
    fit_logistic,
    grouped_folds,
    leave_one_model_out,
    metrics,
    predict_logistic,
)
from process_event_extractor import ACTIVITIES, dfg_conformance_features, fit_dfg  # noqa: E402


DEFAULT_INPUT = SCRIPT_DIR / "results" / "process_poc_dataset.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "results" / "process_stage1_5_analysis.json"
DEFAULT_REPORT = SCRIPT_DIR / "results" / "process_stage1_5_report.md"
DEFAULT_PREDICTIONS = SCRIPT_DIR / "results" / "process_stage1_5_predictions.json"
DEFAULT_FIGURE = SCRIPT_DIR / "results" / "process_stage1_5_summary.png"

PROFILES = (
    "C0_completion",
    "C1_last_activity",
    "C2_activity_counts",
    "C3_dfg_only",
    "C4_structural",
    "C5_full_process",
    "C6_structural_confidence",
)

PROFILE_DESCRIPTIONS = {
    "C0_completion": "Context + tokens + near-cap + parsed-answer presence",
    "C1_last_activity": "C0 + empty marker + last non-conclusion activity",
    "C2_activity_counts": "C0 + non-conclusion activity counts/shares/entropy",
    "C3_dfg_only": "C0 + fold-local DFG features after removing conclude",
    "C4_structural": "C0 + last activity + counts + structural DFG",
    "C5_full_process": "C0 + original full process features, including conclude",
    "C6_structural_confidence": "C4 + retrospective confidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
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


def structural_sequence(record: dict) -> list[str]:
    """Remove conclusion events so structural models cannot reuse answer presence."""
    return [activity for activity in record["activity_sequence"] if activity != "conclude"]


def sequence_entropy(sequence: list[str]) -> float:
    counts = Counter(sequence)
    total = len(sequence)
    if not total:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def structural_count_features(record: dict) -> dict[str, float]:
    sequence = structural_sequence(record)
    counts = Counter(sequence)
    denominator = max(1, len(sequence))
    features = {
        "structural_empty": float(not sequence),
        "structural_step_count": float(len(sequence)),
        "structural_unique_activities": float(len(counts)),
        "structural_activity_entropy": sequence_entropy(sequence),
        "structural_loop_count": float(
            sum(left == right for left, right in zip(sequence, sequence[1:]))
        ),
        "structural_has_verify": float("verify" in counts),
        "structural_has_backtrack": float("backtrack" in counts),
    }
    for activity in ACTIVITIES:
        if activity == "conclude":
            continue
        features[f"structural_count_{activity}"] = float(counts[activity])
        features[f"structural_share_{activity}"] = counts[activity] / denominator
    return features


def last_activity_features(record: dict) -> dict[str, float]:
    sequence = structural_sequence(record)
    features = {"structural_empty": float(not sequence)}
    for activity in ACTIVITIES:
        if activity == "conclude":
            continue
        features[f"structural_last_{activity}"] = float(
            bool(sequence and sequence[-1] == activity)
        )
    return features


def fit_fold_dfgs(records: list[dict], train_indices: list[int], structural: bool) -> tuple:
    def sequence(index: int) -> list[str]:
        return (
            structural_sequence(records[index])
            if structural
            else records[index]["activity_sequence"]
        )

    all_sequences = [sequence(index) for index in train_indices]
    benefit_sequences = [
        sequence(index) for index in train_indices if records[index]["benefit"] == 1
    ]
    no_benefit_sequences = [
        sequence(index) for index in train_indices if records[index]["benefit"] == 0
    ]
    return fit_dfg(all_sequences), fit_dfg(benefit_sequences), fit_dfg(no_benefit_sequences)


def dfg_features(record: dict, models: tuple, structural: bool, prefix: str) -> dict[str, float]:
    sequence = structural_sequence(record) if structural else record["activity_sequence"]
    raw = dfg_conformance_features(sequence, *models)
    return {f"{prefix}_{key}": value for key, value in raw.items()}


def base_completion_features(record: dict) -> dict[str, float]:
    return {
        "level": float(record["level"]),
        "question_chars": float(record["question_chars"]),
        f"model::{record['model']}": 1.0,
        f"subject::{record['subject']}": 1.0,
        "low_completion_tokens": float(record["low_completion_tokens"]),
        "low_token_fraction": float(record["low_completion_tokens"])
        / max(1.0, float(record["low_budget"])),
        "low_near_cap": float(record["low_near_cap"]),
        "low_has_parsed_answer": float(record["low_has_parsed_answer"]),
    }


def profile_features(
    record: dict,
    profile: str,
    structural_dfg: dict[str, float],
    full_dfg: dict[str, float],
) -> dict[str, float]:
    features = base_completion_features(record)
    if profile in {"C1_last_activity", "C4_structural", "C6_structural_confidence"}:
        features.update(last_activity_features(record))
    if profile in {"C2_activity_counts", "C4_structural", "C6_structural_confidence"}:
        features.update(structural_count_features(record))
    if profile in {"C3_dfg_only", "C4_structural", "C6_structural_confidence"}:
        features.update(structural_dfg)
    if profile == "C5_full_process":
        features.update(
            {f"full_{key}": float(value) for key, value in record["process_features"].items()}
        )
        features.update(full_dfg)
    if profile == "C6_structural_confidence":
        confidence = record.get("confidence")
        features["confidence"] = 0.0 if confidence is None else float(confidence) / 100.0
        features["confidence_missing"] = float(record.get("confidence_missing", 0))
    return features


def fold_feature_maps(
    records: list[dict], train_indices: list[int], target_indices: list[int]
) -> tuple[dict[int, dict], dict[int, dict]]:
    structural_models = fit_fold_dfgs(records, train_indices, structural=True)
    full_models = fit_fold_dfgs(records, train_indices, structural=False)
    structural_map = {}
    full_map = {}
    for index in target_indices:
        structural_map[index] = dfg_features(
            records[index], structural_models, structural=True, prefix="structural"
        )
        full_map[index] = dfg_features(
            records[index], full_models, structural=False, prefix="full"
        )
    return structural_map, full_map


def cross_validated_predictions(
    records: list[dict], folds: list[tuple[list[int], list[int]]]
) -> dict[str, np.ndarray]:
    predictions = {profile: np.full(len(records), np.nan) for profile in PROFILES}
    covered: set[int] = set()
    for train_indices, test_indices in folds:
        overlap = covered & set(test_indices)
        if overlap:
            raise ValueError(f"Rows appeared in multiple test folds: {sorted(overlap)[:5]}")
        covered.update(test_indices)
        structural_train, full_train = fold_feature_maps(records, train_indices, train_indices)
        structural_test, full_test = fold_feature_maps(records, train_indices, test_indices)
        target = np.asarray([records[index]["benefit"] for index in train_indices], dtype=float)
        for profile in PROFILES:
            train_rows = [
                profile_features(
                    records[index], profile, structural_train[index], full_train[index]
                )
                for index in train_indices
            ]
            test_rows = [
                profile_features(records[index], profile, structural_test[index], full_test[index])
                for index in test_indices
            ]
            encoder = FeatureEncoder()
            train_matrix = encoder.fit_transform(train_rows)
            test_matrix = encoder.transform(test_rows)
            weights = fit_logistic(train_matrix, target)
            predictions[profile][test_indices] = predict_logistic(test_matrix, weights)
    covered_indices = sorted(covered)
    if any(np.isnan(values[covered_indices]).any() for values in predictions.values()):
        raise RuntimeError("At least one covered row lacks an out-of-fold prediction")
    return predictions


def analyze_cohort(
    records: list[dict], folds: int, seed: int, bootstrap: int
) -> tuple[dict, dict[str, np.ndarray]]:
    target = np.asarray([record["benefit"] for record in records], dtype=int)
    if len(np.unique(target)) < 2:
        raise ValueError("Cohort benefit target has only one class")
    split = grouped_folds(records, folds, seed)
    predictions = cross_validated_predictions(records, split)
    result = {
        "n": len(records),
        "unique_questions": len({record["question_id"] for record in records}),
        "benefit_prevalence": float(target.mean()),
        "empty_trace_rate": float(np.mean([not record["activity_sequence"] for record in records])),
        "metrics": {profile: metrics(target, score) for profile, score in predictions.items()},
        "structural_vs_completion_pr_auc": bootstrap_delta(
            records,
            predictions["C4_structural"],
            predictions["C0_completion"],
            bootstrap,
            seed,
        ),
        "full_vs_structural_pr_auc": bootstrap_delta(
            records,
            predictions["C5_full_process"],
            predictions["C4_structural"],
            bootstrap,
            seed + 1,
        ),
    }
    return result, predictions


def leave_one_model_out_analysis(records: list[dict]) -> dict:
    output = {}
    target_profiles = ("C0_completion", "C4_structural", "C5_full_process", "C6_structural_confidence")
    for train_indices, test_indices, model in leave_one_model_out(records):
        predictions = cross_validated_predictions(records, [(train_indices, test_indices)])
        target = np.asarray([records[index]["benefit"] for index in test_indices], dtype=int)
        output[model] = {
            profile: metrics(target, predictions[profile][test_indices])
            for profile in target_profiles
        }
    return output


def allocation_result(
    records: list[dict], selected: set[int], confidence_overhead: bool
) -> dict[str, float]:
    correctness = []
    actual_cost = []
    for index, record in enumerate(records):
        upgraded = index in selected
        correctness.append(record["high_correct"] if upgraded else record["low_correct"])
        cost = float(record["low_completion_tokens"])
        if upgraded:
            cost += float(record["incremental_token_proxy"])
        if confidence_overhead:
            cost += float(record["confidence_total_tokens"])
        actual_cost.append(cost)
    return {
        "accuracy": float(np.mean(correctness)),
        "mean_realized_token_proxy": float(np.mean(actual_cost)),
        "upgraded": len(selected),
        "upgrade_rate": len(selected) / len(records),
    }


def hard_budget_policy_simulation(
    records: list[dict], predictions: dict[str, np.ndarray], fractions=(0.25, 0.5, 0.75)
) -> dict:
    """Allocate one known Hard-cap increment under an equal worst-case token budget."""
    low_total = sum(record["low_completion_tokens"] for record in records)
    cap_increment = int(records[0]["high_budget"] - records[0]["low_budget"])
    if cap_increment <= 0 or any(
        record["high_budget"] - record["low_budget"] != cap_increment for record in records
    ):
        raise ValueError("Hard-cap increment must be positive and constant")
    output = {
        "budget_definition": (
            "Each upgrade reserves the known high_budget-low_budget Hard-cap increment. "
            "Policies are compared under the same worst-case nominal token budget; realized "
            "completion-token proxy is reported separately."
        ),
        "cap_increment": cap_increment,
        "fractions": {},
    }
    gains = np.asarray([record["gain"] for record in records])
    for fraction in fractions:
        nominal_total_budget = low_total + round(fraction * len(records)) * cap_increment
        result = {
            "mean_nominal_budget": nominal_total_budget / len(records),
        }
        for profile, scores in predictions.items():
            uses_confidence = profile == "C6_structural_confidence"
            overhead = (
                sum(record["confidence_total_tokens"] for record in records)
                if uses_confidence
                else 0
            )
            available = nominal_total_budget - low_total - overhead
            affordable = max(0, min(len(records), available // cap_increment))
            order = np.argsort(-scores, kind="mergesort")
            selected = set(order[:affordable])
            policy = allocation_result(records, selected, uses_confidence)
            policy.update(
                {
                    "confidence_overhead_total": overhead,
                    "nominal_budget_feasible": bool(available >= 0),
                    "reserved_upgrade_tokens": int(affordable * cap_increment),
                }
            )
            result[profile] = policy
        standard_count = round(fraction * len(records))
        oracle_order = np.argsort(-gains, kind="mergesort")
        result["oracle"] = allocation_result(
            records, set(oracle_order[:standard_count]), confidence_overhead=False
        )
        rate = standard_count / len(records)
        result["random_expected"] = {
            "accuracy": float(
                np.mean(
                    [
                        (1 - rate) * record["low_correct"]
                        + rate * record["high_correct"]
                        for record in records
                    ]
                )
            ),
            "mean_realized_token_proxy": float(
                np.mean(
                    [
                        record["low_completion_tokens"]
                        + rate * record["incremental_token_proxy"]
                        for record in records
                    ]
                )
            ),
            "upgraded_expected": standard_count,
        }
        output["fractions"][str(fraction)] = result
    return output


def serializable_predictions(records: list[dict], predictions: dict[str, np.ndarray]) -> list[dict]:
    return [
        {
            "case_id": record["case_id"],
            "question_id": record["question_id"],
            "model": record["model"],
            "replicate": record["replicate"],
            "benefit": record["benefit"],
            "low_has_parsed_answer": record["low_has_parsed_answer"],
            "trace_empty": int(not record["activity_sequence"]),
            "scores": {profile: float(score[index]) for profile, score in predictions.items()},
        }
        for index, record in enumerate(records)
    ]


def fmt(value) -> str:
    return "NA" if value is None else f"{value:.3f}"


def make_figure(analysis: dict, path: Path) -> None:
    cohorts = ("all", "unfinished", "nonempty_unfinished", "empty_unfinished")
    display_profiles = (
        "C0_completion",
        "C1_last_activity",
        "C2_activity_counts",
        "C3_dfg_only",
        "C4_structural",
        "C5_full_process",
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    x = np.arange(len(display_profiles))
    width = 0.18
    for offset, cohort in enumerate(cohorts):
        values = [analysis["cohorts"][cohort]["metrics"][profile]["pr_auc"] for profile in display_profiles]
        axes[0].bar(x + (offset - 1.5) * width, values, width, label=cohort)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([profile.split("_")[0] for profile in display_profiles])
    axes[0].set_ylabel("PR-AUC")
    axes[0].set_title("Shortcut and cohort ablations")
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="y", alpha=0.25)

    policies = analysis["hard_budget_policy"]["fractions"]
    for profile, marker in (
        ("C0_completion", "o"),
        ("C4_structural", "^"),
        ("C5_full_process", "s"),
        ("C6_structural_confidence", "D"),
        ("oracle", "*"),
        ("random_expected", "x"),
    ):
        points = [value[profile] for value in policies.values()]
        axes[1].plot(
            [point["mean_realized_token_proxy"] for point in points],
            [point["accuracy"] for point in points],
            marker=marker,
            label=profile,
        )
    axes[1].set_xlabel("Mean realized completion-token proxy")
    axes[1].set_ylabel("Accuracy")
    axes[1].set_title("Equal worst-case Hard-token budgets")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_report(metadata: dict, analysis: dict, figure: Path) -> str:
    lines = [
        "# Stage 1.5：Process signal robustness report",
        "",
        "> This analysis removes conclusion shortcuts, conditions on unfinished cases, and "
        "uses equal worst-case Hard-token budgets.",
        "",
        "## Cohorts",
        "",
        "| Cohort | n | Questions | Benefit rate | Empty trace rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, cohort in analysis["cohorts"].items():
        lines.append(
            f"| {name} | {cohort['n']} | {cohort['unique_questions']} | "
            f"{cohort['benefit_prevalence']:.1%} | {cohort['empty_trace_rate']:.1%} |"
        )
    for name in ("all", "unfinished", "nonempty_unfinished", "empty_unfinished"):
        cohort = analysis["cohorts"][name]
        lines.extend(
            [
                "",
                f"## {name}: grouped out-of-fold metrics",
                "",
                "| Profile | PR-AUC | AUROC | Brier | Log loss |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for profile in PROFILES:
            result = cohort["metrics"][profile]
            lines.append(
                f"| {profile} | {fmt(result['pr_auc'])} | {fmt(result['roc_auc'])} | "
                f"{fmt(result['brier'])} | {fmt(result['log_loss'])} |"
            )
        contrast = cohort["structural_vs_completion_pr_auc"]
        lines.append(
            "\nC4 structural minus C0 completion PR-AUC: "
            f"**{fmt(contrast['estimate'])}**, clustered 95% CI "
            f"[{fmt(contrast['ci_low'])}, {fmt(contrast['ci_high'])}]."
        )
    lines.extend(
        [
            "",
            "## Equal Hard-token budget policy simulation",
            "",
            "| Nominal extra budget | Policy | Accuracy | Realized token proxy | Upgraded | Feasible |",
            "|---:|---|---:|---:|---:|---|",
        ]
    )
    for fraction, result in analysis["hard_budget_policy"]["fractions"].items():
        for profile in (
            "random_expected",
            "C0_completion",
            "C4_structural",
            "C5_full_process",
            "C6_structural_confidence",
            "oracle",
        ):
            row = result[profile]
            upgraded = row.get("upgraded", row.get("upgraded_expected", "NA"))
            feasible = row.get("nominal_budget_feasible", True)
            lines.append(
                f"| {float(fraction):.0%} | {profile} | {row['accuracy']:.1%} | "
                f"{row['mean_realized_token_proxy']:.1f} | {upgraded} | {feasible} |"
            )
    lines.extend(
        [
            "",
            f"![Stage 1.5 summary]({figure.name})",
            "",
            "## Pre-registered interpretation",
            "",
            "- Primary cohort: `unfinished` (`low_has_parsed_answer=0`).",
            "- Primary contrast: C4 structural vs C0 completion.",
            "- C4 excludes every `conclude` event and answer-equivalent process feature.",
            "- If C4 does not improve the unfinished cohort, Stage 1 supports progress/completion "
            "detection but not a structural process-mining claim.",
            "- Empty and non-empty trace results must be reported separately.",
            "- Confidence is retained as an ablation and pays its complete prompt+completion cost.",
            "- The low/high responses remain independent calls; no causal continuation claim is allowed.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    metadata, all_records = load_records(args.input)
    cohorts = {
        "all": all_records,
        "unfinished": [record for record in all_records if not record["low_has_parsed_answer"]],
        "nonempty_unfinished": [
            record
            for record in all_records
            if not record["low_has_parsed_answer"] and record["activity_sequence"]
        ],
        "empty_unfinished": [
            record
            for record in all_records
            if not record["low_has_parsed_answer"] and not record["activity_sequence"]
        ],
    }
    cohort_results = {}
    cohort_predictions = {}
    for name, records in cohorts.items():
        result, predictions = analyze_cohort(records, args.folds, args.seed, args.bootstrap)
        cohort_results[name] = result
        cohort_predictions[name] = serializable_predictions(records, predictions)

    all_folds = grouped_folds(all_records, args.folds, args.seed)
    all_predictions = cross_validated_predictions(all_records, all_folds)
    analysis = {
        "schema_version": 1,
        "profiles": PROFILE_DESCRIPTIONS,
        "primary_cohort": "unfinished",
        "primary_contrast": "C4_structural - C0_completion PR-AUC",
        "cohorts": cohort_results,
        "unfinished_leave_one_model_out": leave_one_model_out_analysis(cohorts["unfinished"]),
        "hard_budget_policy": hard_budget_policy_simulation(all_records, all_predictions),
        "guardrails": [
            "All test predictions are grouped out-of-fold by question_id.",
            "DFGs are fitted on training folds only.",
            "Structural profiles remove conclude events and answer-equivalent process features.",
            "Low/high Phase 3 outcomes are independent calls, not resumed generations.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "analysis": analysis}, handle, indent=2)
    with args.predictions.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "metadata": {
                    "schema_version": 1,
                    "warning": "Scores are out-of-fold within each named cohort and are not interchangeable.",
                },
                "cohorts": cohort_predictions,
            },
            handle,
            indent=2,
        )
    make_figure(analysis, args.figure)
    args.report.write_text(make_report(metadata, analysis, args.figure), encoding="utf-8")
    print(f"Wrote Stage 1.5 analysis to {args.output}")
    print(f"Wrote out-of-fold predictions to {args.predictions}")
    print(f"Wrote report to {args.report}")
    print(f"Wrote figure to {args.figure}")


if __name__ == "__main__":
    main()
