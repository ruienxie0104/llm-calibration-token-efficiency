#!/usr/bin/env python3
"""Stage 1.6: diagnose process-conditioned confidence for compute allocation.

This script makes no API calls. It uses grouped out-of-fold prediction to test
whether retrospective confidence has incremental value only after conditioning
on observable process state, then charges confidence acquisition cost in an
offline selective-query policy simulation.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from analyze_process_stage1_5 import (  # noqa: E402
    last_activity_features,
    structural_count_features,
)
from analyze_process_value import (  # noqa: E402
    FeatureEncoder,
    average_precision,
    fit_logistic,
    grouped_folds,
    leave_one_model_out,
    metrics,
    predict_logistic,
)


DEFAULT_INPUT = SCRIPT_DIR / "results" / "process_poc_dataset.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "results" / "process_stage1_6_analysis.json"
DEFAULT_REPORT = SCRIPT_DIR / "results" / "process_stage1_6_report.md"
DEFAULT_PREDICTIONS = SCRIPT_DIR / "results" / "process_stage1_6_predictions.json"
DEFAULT_FIGURE = SCRIPT_DIR / "results" / "process_stage1_6_summary.png"

PROFILES = (
    "P0_process_only",
    "P1_confidence_only",
    "P2_additive",
    "P3_state_interaction",
    "P4_process_interaction",
)

PROFILE_DESCRIPTIONS = {
    "P0_process_only": (
        "Context + runtime + coarse process state + non-conclusion process features"
    ),
    "P1_confidence_only": "Context + runtime + retrospective confidence",
    "P2_additive": "P0 process features + retrospective confidence",
    "P3_state_interaction": "P2 + confidence by coarse-state interactions (primary)",
    "P4_process_interaction": (
        "P3 + confidence by selected non-conclusion process interactions (exploratory)"
    ),
}

PROCESS_STATES = ("complete", "visible_unfinished", "empty_unfinished")
CONFIDENCE_BANDS = (
    ("low", 0.0, 75.0, True),
    ("mid", 75.0, 90.0, False),
    ("high", 90.0, 100.0, True),
)
RELIABILITY_BINS = ((0, 25), (25, 50), (50, 75), (75, 90), (90, 100))
SELECTIVE_QUERY_FRACTIONS = (0.10, 0.25, 0.50)
NOMINAL_EXTRA_BUDGET_FRACTIONS = (0.25, 0.50, 0.75)


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
    required = {
        "question_id",
        "model",
        "benefit",
        "low_correct",
        "high_correct",
        "low_has_parsed_answer",
        "activity_sequence",
        "confidence",
        "confidence_total_tokens",
    }
    missing = required - set(records[0])
    if missing:
        raise ValueError(f"Dataset is missing required fields: {sorted(missing)}")
    return payload.get("metadata", {}), records


def process_state(record: dict) -> str:
    if record["low_has_parsed_answer"]:
        return "complete"
    if record["activity_sequence"]:
        return "visible_unfinished"
    return "empty_unfinished"


def base_features(record: dict) -> dict[str, float]:
    return {
        "level": float(record["level"]),
        "question_chars": float(record["question_chars"]),
        f"model::{record['model']}": 1.0,
        f"subject::{record['subject']}": 1.0,
        "low_completion_tokens": float(record["low_completion_tokens"]),
        "low_token_fraction": float(record["low_completion_tokens"])
        / max(1.0, float(record["low_budget"])),
        "low_near_cap": float(record["low_near_cap"]),
    }


def process_features(record: dict) -> dict[str, float]:
    state = process_state(record)
    features = {f"state::{name}": float(state == name) for name in PROCESS_STATES}
    features.update(last_activity_features(record))
    features.update(structural_count_features(record))
    return features


def fit_confidence_imputer(records: list[dict], train_indices: list[int]) -> float:
    values = [
        float(records[index]["confidence"]) / 100.0
        for index in train_indices
        if records[index].get("confidence") is not None
    ]
    if not values:
        raise ValueError("Training fold contains no parsed confidence values")
    return float(np.mean(values))


def confidence_features(record: dict, imputed_confidence: float) -> dict[str, float]:
    value = record.get("confidence")
    confidence = imputed_confidence if value is None else float(value) / 100.0
    return {
        "confidence": confidence,
        "confidence_missing": float(value is None),
    }


def profile_features(record: dict, profile: str, imputed_confidence: float) -> dict[str, float]:
    features = base_features(record)
    process = process_features(record)
    confidence = confidence_features(record, imputed_confidence)

    if profile in {
        "P0_process_only",
        "P2_additive",
        "P3_state_interaction",
        "P4_process_interaction",
    }:
        features.update(process)
    if profile in {
        "P1_confidence_only",
        "P2_additive",
        "P3_state_interaction",
        "P4_process_interaction",
    }:
        features.update(confidence)

    if profile in {"P3_state_interaction", "P4_process_interaction"}:
        for state in PROCESS_STATES:
            features[f"interaction::confidence_x_state::{state}"] = (
                confidence["confidence"] * process[f"state::{state}"]
            )

    if profile == "P4_process_interaction":
        interaction_keys = {
            "structural_empty",
            "structural_step_count",
            "structural_unique_activities",
            "structural_activity_entropy",
            "structural_loop_count",
            "structural_has_verify",
            "structural_has_backtrack",
        }
        interaction_keys.update(
            key for key in process if key.startswith("structural_last_")
        )
        for key in sorted(interaction_keys):
            features[f"interaction::confidence_x_{key}"] = (
                confidence["confidence"] * process.get(key, 0.0)
            )
    return features


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
        target = np.asarray([records[index]["benefit"] for index in train_indices], dtype=float)
        imputed_confidence = fit_confidence_imputer(records, train_indices)
        for profile in PROFILES:
            train_rows = [
                profile_features(records[index], profile, imputed_confidence)
                for index in train_indices
            ]
            test_rows = [
                profile_features(records[index], profile, imputed_confidence)
                for index in test_indices
            ]
            encoder = FeatureEncoder()
            train_matrix = encoder.fit_transform(train_rows)
            test_matrix = encoder.transform(test_rows)
            weights = fit_logistic(train_matrix, target)
            predictions[profile][test_indices] = predict_logistic(test_matrix, weights)
    covered_indices = sorted(covered)
    if any(np.isnan(scores[covered_indices]).any() for scores in predictions.values()):
        raise RuntimeError("At least one covered row lacks an out-of-fold prediction")
    return predictions


def subset_metrics(
    records: list[dict], predictions: dict[str, np.ndarray], indices: list[int]
) -> dict:
    target = np.asarray([records[index]["benefit"] for index in indices], dtype=int)
    return {
        "n": len(indices),
        "unique_questions": len({records[index]["question_id"] for index in indices}),
        "positive_count": int(target.sum()),
        "negative_count": int(len(target) - target.sum()),
        "benefit_prevalence": float(target.mean()),
        "metrics": {
            profile: metrics(target, scores[indices])
            for profile, scores in predictions.items()
        },
    }


def cluster_bootstrap_pr_auc_delta(
    records: list[dict],
    indices: list[int],
    left: np.ndarray,
    right: np.ndarray,
    draws: int,
    seed: int,
) -> dict[str, float | int | None]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index in indices:
        groups[records[index]["question_id"]].append(index)
    group_ids = sorted(groups)
    rng = random.Random(seed)
    deltas = []
    for _ in range(draws):
        sampled_groups = [rng.choice(group_ids) for _ in group_ids]
        sampled_indices = [index for group in sampled_groups for index in groups[group]]
        target = np.asarray([records[index]["benefit"] for index in sampled_indices], dtype=int)
        left_value = average_precision(target, left[sampled_indices])
        right_value = average_precision(target, right[sampled_indices])
        if left_value is not None and right_value is not None:
            deltas.append(left_value - right_value)
    target = np.asarray([records[index]["benefit"] for index in indices], dtype=int)
    left_value = average_precision(target, left[indices])
    right_value = average_precision(target, right[indices])
    estimate = None if left_value is None or right_value is None else left_value - right_value
    if not deltas:
        return {
            "estimate": estimate,
            "ci_low": None,
            "ci_high": None,
            "valid_draws": 0,
        }
    values = np.asarray(deltas)
    return {
        "estimate": float(estimate),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
        "valid_draws": len(deltas),
    }


def safe_rate(rows: list[dict], key: str) -> float | None:
    return None if not rows else float(np.mean([row[key] for row in rows]))


def safe_mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(values))


def confidence_band(value: float | None) -> str:
    if value is None:
        return "missing"
    value = float(value)
    if value <= 75:
        return "low"
    if value < 90:
        return "mid"
    return "high"


def descriptive_state_table(records: list[dict]) -> dict[str, dict]:
    output = {}
    for state in PROCESS_STATES:
        rows = [record for record in records if process_state(record) == state]
        confidences = [float(row["confidence"]) for row in rows if row["confidence"] is not None]
        output[state] = {
            "n": len(rows),
            "low_accuracy": safe_rate(rows, "low_correct"),
            "high_accuracy": safe_rate(rows, "high_correct"),
            "benefit_rate": safe_rate(rows, "benefit"),
            "harm_rate": safe_rate(rows, "harm"),
            "mean_confidence": safe_mean(confidences),
            "missing_confidence": sum(row["confidence"] is None for row in rows),
            "mean_confidence_total_tokens": safe_mean(
                [float(row["confidence_total_tokens"]) for row in rows]
            ),
        }
    return output


def discordance_table(records: list[dict]) -> list[dict]:
    output = []
    for state in PROCESS_STATES:
        for band in ("low", "mid", "high", "missing"):
            rows = [
                record
                for record in records
                if process_state(record) == state
                and confidence_band(record.get("confidence")) == band
            ]
            if not rows:
                continue
            confidences = [float(row["confidence"]) for row in rows if row["confidence"] is not None]
            output.append(
                {
                    "state": state,
                    "confidence_band": band,
                    "n": len(rows),
                    "unique_questions": len({row["question_id"] for row in rows}),
                    "low_accuracy": safe_rate(rows, "low_correct"),
                    "high_accuracy": safe_rate(rows, "high_correct"),
                    "benefit_rate": safe_rate(rows, "benefit"),
                    "harm_rate": safe_rate(rows, "harm"),
                    "mean_confidence": safe_mean(confidences),
                    "mean_confidence_total_tokens": safe_mean(
                        [float(row["confidence_total_tokens"]) for row in rows]
                    ),
                }
            )
    return output


def reliability_summary(records: list[dict]) -> dict:
    valid = [record for record in records if record.get("confidence") is not None]
    if not valid:
        return {"n": 0, "brier": None, "ece": None, "bins": []}
    confidence = np.asarray([float(row["confidence"]) / 100.0 for row in valid])
    target = np.asarray([row["low_correct"] for row in valid], dtype=float)
    bins = []
    weighted_error = 0.0
    for lower, upper in RELIABILITY_BINS:
        selected = [
            index
            for index, row in enumerate(valid)
            if float(row["confidence"]) >= lower
            and (float(row["confidence"]) < upper or upper == 100)
        ]
        if not selected:
            continue
        mean_confidence = float(np.mean(confidence[selected]))
        accuracy = float(np.mean(target[selected]))
        weighted_error += len(selected) / len(valid) * abs(mean_confidence - accuracy)
        bins.append(
            {
                "range": f"[{lower},{upper}{']' if upper == 100 else ')'}",
                "n": len(selected),
                "mean_confidence": mean_confidence,
                "accuracy": accuracy,
                "calibration_gap": mean_confidence - accuracy,
            }
        )
    return {
        "n": len(valid),
        "brier": float(np.mean((confidence - target) ** 2)),
        "ece": float(weighted_error),
        "bins": bins,
    }


def correlation_summary(records: list[dict]) -> dict[str, float | int | None]:
    valid = [record for record in records if record.get("confidence") is not None]
    output: dict[str, float | int | None] = {"n": len(valid)}
    confidence = [float(record["confidence"]) for record in valid]
    for target_name in ("benefit", "low_correct", "high_correct"):
        target = [float(record[target_name]) for record in valid]
        if len(set(confidence)) < 2 or len(set(target)) < 2:
            output[f"spearman_confidence_vs_{target_name}"] = None
        else:
            result = spearmanr(confidence, target)
            output[f"spearman_confidence_vs_{target_name}"] = float(result.statistic)
    return output


def process_conditioned_diagnostics(records: list[dict]) -> dict:
    cohorts = {"all": records}
    cohorts.update(
        {
            state: [record for record in records if process_state(record) == state]
            for state in PROCESS_STATES
        }
    )
    models = sorted({record["model"] for record in records})
    return {
        "state_summary": descriptive_state_table(records),
        "discordance": discordance_table(records),
        "reliability": {
            name: reliability_summary(rows) for name, rows in cohorts.items()
        },
        "reliability_by_model": {
            model: reliability_summary([row for row in records if row["model"] == model])
            for model in models
        },
        "correlations": {
            name: correlation_summary(rows) for name, rows in cohorts.items()
        },
    }


def allocation_result(
    records: list[dict], selected: set[int], confidence_queried: set[int]
) -> dict[str, float | int]:
    correctness = []
    realized_cost = []
    for index, record in enumerate(records):
        upgraded = index in selected
        correctness.append(record["high_correct"] if upgraded else record["low_correct"])
        cost = float(record["low_completion_tokens"])
        if upgraded:
            cost += float(record["incremental_token_proxy"])
        if index in confidence_queried:
            cost += float(record["confidence_total_tokens"])
        realized_cost.append(cost)
    return {
        "accuracy": float(np.mean(correctness)),
        "mean_realized_token_proxy": float(np.mean(realized_cost)),
        "upgraded": len(selected),
        "upgrade_rate": len(selected) / len(records),
        "confidence_queried": len(confidence_queried),
        "confidence_query_rate": len(confidence_queried) / len(records),
        "confidence_overhead_total": int(
            sum(records[index]["confidence_total_tokens"] for index in confidence_queried)
        ),
    }


def ranked_selection(scores: np.ndarray, count: int) -> set[int]:
    if count <= 0:
        return set()
    order = np.argsort(-scores, kind="mergesort")
    return set(int(index) for index in order[:count])


def selective_query_set(base_scores: np.ndarray, nominal_upgrade_count: int, fraction: float) -> set[int]:
    count = max(1, round(fraction * len(base_scores)))
    order = np.argsort(-base_scores, kind="mergesort")
    cutoff_position = min(max(nominal_upgrade_count - 1, 0), len(base_scores) - 1)
    cutoff = float(base_scores[order[cutoff_position]])
    closest = np.argsort(np.abs(base_scores - cutoff), kind="mergesort")
    return set(int(index) for index in closest[:count])


def cost_aware_policy_simulation(
    records: list[dict], predictions: dict[str, np.ndarray]
) -> dict:
    low_total = sum(float(record["low_completion_tokens"]) for record in records)
    cap_increment = int(records[0]["high_budget"] - records[0]["low_budget"])
    if cap_increment <= 0 or any(
        int(record["high_budget"] - record["low_budget"]) != cap_increment
        for record in records
    ):
        raise ValueError("Hard-cap increment must be positive and constant")
    process_scores = predictions["P0_process_only"]
    interaction_scores = predictions["P3_state_interaction"]
    gains = np.asarray([record["gain"] for record in records])
    output = {
        "cap_increment": cap_increment,
        "confidence_query_fractions": list(SELECTIVE_QUERY_FRACTIONS),
        "warning": (
            "Low/high calls were independent. Realized increment is an offline proxy. "
            "Confidence overhead includes prompt and completion tokens, while low/high cost "
            "uses completion tokens."
        ),
        "fractions": {},
    }
    for fraction in NOMINAL_EXTRA_BUDGET_FRACTIONS:
        nominal_count = round(fraction * len(records))
        nominal_total = low_total + nominal_count * cap_increment
        result: dict[str, dict] = {
            "mean_nominal_budget": nominal_total / len(records),
        }

        process_selected = ranked_selection(process_scores, nominal_count)
        result["process_only"] = allocation_result(records, process_selected, set())

        all_queried = set(range(len(records)))
        all_overhead = sum(record["confidence_total_tokens"] for record in records)
        all_affordable = max(
            0,
            min(len(records), int((nominal_total - low_total - all_overhead) // cap_increment)),
        )
        result["confidence_all"] = allocation_result(
            records,
            ranked_selection(interaction_scores, all_affordable),
            all_queried,
        )
        result["confidence_all"]["nominal_budget_feasible"] = bool(
            nominal_total - low_total - all_overhead >= 0
        )

        for query_fraction in SELECTIVE_QUERY_FRACTIONS:
            queried = selective_query_set(process_scores, nominal_count, query_fraction)
            overhead = sum(records[index]["confidence_total_tokens"] for index in queried)
            affordable = max(
                0,
                min(len(records), int((nominal_total - low_total - overhead) // cap_increment)),
            )
            mixed_scores = process_scores.copy()
            query_indices = sorted(queried)
            mixed_scores[query_indices] = interaction_scores[query_indices]
            name = f"selective_{int(query_fraction * 100)}pct"
            result[name] = allocation_result(
                records,
                ranked_selection(mixed_scores, affordable),
                queried,
            )
            result[name]["nominal_budget_feasible"] = bool(
                nominal_total - low_total - overhead >= 0
            )

        oracle_selected = ranked_selection(gains, nominal_count)
        result["oracle"] = allocation_result(records, oracle_selected, set())
        result["random_expected"] = {
            "accuracy": float(
                np.mean(
                    [
                        (1 - fraction) * record["low_correct"]
                        + fraction * record["high_correct"]
                        for record in records
                    ]
                )
            ),
            "mean_realized_token_proxy": float(
                np.mean(
                    [
                        record["low_completion_tokens"]
                        + fraction * record["incremental_token_proxy"]
                        for record in records
                    ]
                )
            ),
            "upgraded_expected": nominal_count,
            "confidence_queried": 0,
        }
        output["fractions"][str(fraction)] = result
    return output


def leave_one_model_out_analysis(records: list[dict]) -> dict:
    output = {}
    for train_indices, test_indices, model in leave_one_model_out(records):
        predictions = cross_validated_predictions(records, [(train_indices, test_indices)])
        output[model] = subset_metrics(records, predictions, test_indices)
    return output


def serializable_predictions(
    records: list[dict], predictions: dict[str, np.ndarray]
) -> list[dict]:
    return [
        {
            "case_id": record["case_id"],
            "question_id": record["question_id"],
            "model": record["model"],
            "replicate": record["replicate"],
            "process_state": process_state(record),
            "confidence": record.get("confidence"),
            "confidence_missing": record.get("confidence_missing", 0),
            "benefit": record["benefit"],
            "low_correct": record["low_correct"],
            "high_correct": record["high_correct"],
            "scores": {
                profile: float(scores[index]) for profile, scores in predictions.items()
            },
        }
        for index, record in enumerate(records)
    ]


def fmt(value) -> str:
    return "NA" if value is None else f"{value:.3f}"


def pct(value) -> str:
    return "NA" if value is None else f"{value:.1%}"


def make_figure(analysis: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    cohorts = ("all", "complete", "visible_unfinished", "empty_unfinished")
    x = np.arange(len(PROFILES))
    width = 0.19
    for offset, cohort in enumerate(cohorts):
        values = [
            analysis["cohorts"][cohort]["metrics"][profile]["pr_auc"] or 0.0
            for profile in PROFILES
        ]
        axes[0].bar(x + (offset - 1.5) * width, values, width, label=cohort)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([profile.split("_")[0] for profile in PROFILES])
    axes[0].set_ylabel("PR-AUC")
    axes[0].set_title("Conditional benefit prediction")
    axes[0].legend(fontsize=7)
    axes[0].grid(axis="y", alpha=0.25)

    colors = {
        "complete": "tab:green",
        "visible_unfinished": "tab:orange",
        "empty_unfinished": "tab:red",
    }
    for state in PROCESS_STATES:
        bins = analysis["diagnostics"]["reliability"][state]["bins"]
        if bins:
            axes[1].plot(
                [row["mean_confidence"] for row in bins],
                [row["accuracy"] for row in bins],
                "o-",
                color=colors[state],
                label=state,
            )
    axes[1].plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfect")
    axes[1].set_xlabel("Mean retrospective confidence")
    axes[1].set_ylabel("Low-budget accuracy")
    axes[1].set_title("Confidence reliability by process state")
    axes[1].legend(fontsize=7)
    axes[1].grid(alpha=0.25)

    policies = analysis["cost_aware_policies"]["fractions"]
    display = (
        "process_only",
        "selective_10pct",
        "selective_25pct",
        "selective_50pct",
        "confidence_all",
        "oracle",
    )
    markers = ("o", "^", "s", "D", "v", "*")
    for policy, marker in zip(display, markers):
        points = [row[policy] for row in policies.values()]
        axes[2].plot(
            [point["mean_realized_token_proxy"] for point in points],
            [point["accuracy"] for point in points],
            marker=marker,
            label=policy,
        )
    axes[2].set_xlabel("Mean realized token proxy")
    axes[2].set_ylabel("Accuracy")
    axes[2].set_title("Cost-aware selective confidence")
    axes[2].legend(fontsize=7)
    axes[2].grid(alpha=0.25)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_report(metadata: dict, analysis: dict, figure: Path) -> str:
    lines = [
        "# Stage 1.6：Process-conditioned confidence report",
        "",
        "> Offline diagnosis only. Low/high Phase 3 outputs are independent calls, not resumed "
        "generations.",
        "",
        "## Data and states",
        "",
        f"- Records: **{analysis['record_count']}**",
        f"- Unique questions: **{analysis['unique_questions']}**",
        f"- Budget comparison: **{metadata.get('low_budget')} → {metadata.get('high_budget')}**",
        f"- Missing confidence: **{analysis['missing_confidence']}**",
        "",
        "| State | n | Low acc. | High acc. | Benefit | Mean conf. | Mean conf. tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for state, row in analysis["diagnostics"]["state_summary"].items():
        lines.append(
            f"| {state} | {row['n']} | {pct(row['low_accuracy'])} | "
            f"{pct(row['high_accuracy'])} | {pct(row['benefit_rate'])} | "
            f"{fmt(row['mean_confidence'])} | {fmt(row['mean_confidence_total_tokens'])} |"
        )

    for cohort in ("all", "complete", "visible_unfinished", "empty_unfinished"):
        result = analysis["cohorts"][cohort]
        lines.extend(
            [
                "",
                f"## {cohort}: grouped OOF benefit prediction",
                "",
                f"n={result['n']}, positives={result['positive_count']}, "
                f"negatives={result['negative_count']}, prevalence={result['benefit_prevalence']:.1%}.",
                "",
                "| Profile | PR-AUC | AUROC | Brier | Log loss |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for profile in PROFILES:
            row = result["metrics"][profile]
            lines.append(
                f"| {profile} | {fmt(row['pr_auc'])} | {fmt(row['roc_auc'])} | "
                f"{fmt(row['brier'])} | {fmt(row['log_loss'])} |"
            )
        state_delta = result["contrasts"]["P3_minus_P0_pr_auc"]
        lines.append(
            "\nP3 state interaction minus P0 process-only PR-AUC: "
            f"**{fmt(state_delta['estimate'])}**, clustered 95% CI "
            f"[{fmt(state_delta['ci_low'])}, {fmt(state_delta['ci_high'])}]."
        )

    primary = analysis["primary_contrasts"]["P3_minus_P0_pr_auc"]
    mechanism = analysis["primary_contrasts"]["P3_minus_P2_pr_auc"]
    lines.extend(
        [
            "",
            "## Primary interaction contrasts",
            "",
            "- P3 state interaction minus P0 process-only PR-AUC: "
            f"**{fmt(primary['estimate'])}**, clustered 95% CI "
            f"[{fmt(primary['ci_low'])}, {fmt(primary['ci_high'])}].",
            "- P3 state interaction minus P2 additive PR-AUC: "
            f"**{fmt(mechanism['estimate'])}**, clustered 95% CI "
            f"[{fmt(mechanism['ci_low'])}, {fmt(mechanism['ci_high'])}].",
            "",
            "## Process-confidence discordance",
            "",
            "| State | Confidence band | n | Low acc. | High acc. | Benefit | Mean conf. |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in analysis["diagnostics"]["discordance"]:
        lines.append(
            f"| {row['state']} | {row['confidence_band']} | {row['n']} | "
            f"{pct(row['low_accuracy'])} | {pct(row['high_accuracy'])} | "
            f"{pct(row['benefit_rate'])} | {fmt(row['mean_confidence'])} |"
        )

    lines.extend(
        [
            "",
            "## Current-correctness calibration",
            "",
            "Retrospective confidence is compared with low-budget correctness. This is not a "
            "calibrated probability of additional-compute benefit.",
            "",
            "| Cohort | n | Brier | ECE |",
            "|---|---:|---:|---:|",
        ]
    )
    for cohort, row in analysis["diagnostics"]["reliability"].items():
        lines.append(
            f"| {cohort} | {row['n']} | {fmt(row['brier'])} | {fmt(row['ece'])} |"
        )

    lines.extend(
        [
            "",
            "## Leave-one-model-out generalization",
            "",
            "| Held-out model | P0 PR-AUC | P3 PR-AUC | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for model, result in analysis["leave_one_model_out"].items():
        p0 = result["metrics"]["P0_process_only"]["pr_auc"]
        p3 = result["metrics"]["P3_state_interaction"]["pr_auc"]
        delta = None if p0 is None or p3 is None else p3 - p0
        lines.append(f"| {model} | {fmt(p0)} | {fmt(p3)} | {fmt(delta)} |")

    lines.extend(
        [
            "",
            "## Cost-aware selective-confidence simulation",
            "",
            "| Nominal extra budget | Policy | Accuracy | Realized token proxy | "
            "Upgraded | Confidence queried |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    policies = analysis["cost_aware_policies"]["fractions"]
    policy_order = (
        "random_expected",
        "process_only",
        "selective_10pct",
        "selective_25pct",
        "selective_50pct",
        "confidence_all",
        "oracle",
    )
    for fraction, result in policies.items():
        for policy in policy_order:
            row = result[policy]
            upgraded = row.get("upgraded", row.get("upgraded_expected", "NA"))
            lines.append(
                f"| {float(fraction):.0%} | {policy} | {row['accuracy']:.1%} | "
                f"{row['mean_realized_token_proxy']:.1f} | {upgraded} | "
                f"{row.get('confidence_queried', 0)} |"
            )

    decision = analysis["decision_checks"]
    lines.extend(
        [
            "",
            f"![Stage 1.6 summary]({figure.name})",
            "",
            "## Pre-registered decision checks",
            "",
            f"- Primary P3−P0 CI entirely above zero: **{decision['primary_ci_positive']}**.",
            f"- P3−P2 point estimate positive: **{decision['mechanism_point_positive']}**.",
            f"- Held-out models with P3 PR-AUC > P0: "
            f"**{decision['held_out_models_positive']}/{decision['held_out_models_total']}**.",
            "- Unfinished states with sufficient class counts and positive interaction CI: "
            f"**{decision['unfinished_states_with_positive_interaction_ci'] or 'none'}**.",
            f"- Budget levels where any selective policy beats process-only: "
            f"**{decision['selective_policy_wins']}/3**.",
            "",
            "## Required interpretation guardrails",
            "",
            "- P3 must beat P0 to claim incremental confidence value; beating confidence-only is "
            "not sufficient.",
            "- P3 beating P2 is evidence that confidence meaning depends on process state.",
            "- A predictive interaction that fails after confidence cost is diagnostic, not yet an "
            "operational allocation method.",
            "- Confidence prompt tokens are charged conservatively; token proxy is not actual price "
            "or latency.",
            "- Rebuild labels with the corrected parser before treating the numerical result as "
            "final.",
            "- Low/high calls are independent; no causal continuation claim is allowed.",
            "",
        ]
    )
    return "\n".join(lines)


def decision_checks(analysis: dict) -> dict:
    primary = analysis["primary_contrasts"]["P3_minus_P0_pr_auc"]
    mechanism = analysis["primary_contrasts"]["P3_minus_P2_pr_auc"]
    held_out = analysis["leave_one_model_out"]
    positive_models = sum(
        row["metrics"]["P3_state_interaction"]["pr_auc"]
        > row["metrics"]["P0_process_only"]["pr_auc"]
        for row in held_out.values()
        if row["metrics"]["P3_state_interaction"]["pr_auc"] is not None
        and row["metrics"]["P0_process_only"]["pr_auc"] is not None
    )
    selective_wins = 0
    for result in analysis["cost_aware_policies"]["fractions"].values():
        baseline = result["process_only"]["accuracy"]
        if any(
            result[f"selective_{int(fraction * 100)}pct"]["accuracy"] > baseline
            for fraction in SELECTIVE_QUERY_FRACTIONS
        ):
            selective_wins += 1
    state_support = []
    for state in ("visible_unfinished", "empty_unfinished"):
        result = analysis["cohorts"][state]
        contrast = result["contrasts"]["P3_minus_P0_pr_auc"]
        if (
            result["positive_count"] >= 20
            and result["negative_count"] >= 20
            and contrast["ci_low"] is not None
            and contrast["ci_low"] > 0
        ):
            state_support.append(state)
    return {
        "primary_ci_positive": bool(
            primary["ci_low"] is not None and primary["ci_low"] > 0
        ),
        "mechanism_point_positive": bool(
            mechanism["estimate"] is not None and mechanism["estimate"] > 0
        ),
        "held_out_models_positive": positive_models,
        "held_out_models_total": len(held_out),
        "selective_policy_wins": selective_wins,
        "operational_go": bool(selective_wins >= 2),
        "unfinished_states_with_positive_interaction_ci": state_support,
    }


def main() -> None:
    args = parse_args()
    metadata, records = load_records(args.input)
    target = np.asarray([record["benefit"] for record in records], dtype=int)
    if len(np.unique(target)) < 2:
        raise ValueError("Benefit target has only one class; analysis is not identifiable")

    folds = grouped_folds(records, args.folds, args.seed)
    predictions = cross_validated_predictions(records, folds)
    cohort_indices = {"all": list(range(len(records)))}
    cohort_indices.update(
        {
            state: [
                index
                for index, record in enumerate(records)
                if process_state(record) == state
            ]
            for state in PROCESS_STATES
        }
    )
    cohorts = {}
    for offset, (name, indices) in enumerate(cohort_indices.items()):
        result = subset_metrics(records, predictions, indices)
        result["contrasts"] = {
            "P3_minus_P0_pr_auc": cluster_bootstrap_pr_auc_delta(
                records,
                indices,
                predictions["P3_state_interaction"],
                predictions["P0_process_only"],
                args.bootstrap,
                args.seed + 10 + offset,
            ),
            "P3_minus_P2_pr_auc": cluster_bootstrap_pr_auc_delta(
                records,
                indices,
                predictions["P3_state_interaction"],
                predictions["P2_additive"],
                args.bootstrap,
                args.seed + 20 + offset,
            ),
        }
        cohorts[name] = result
    all_indices = cohort_indices["all"]
    analysis = {
        "schema_version": 1,
        "profiles": PROFILE_DESCRIPTIONS,
        "record_count": len(records),
        "unique_questions": len({record["question_id"] for record in records}),
        "missing_confidence": sum(record.get("confidence") is None for record in records),
        "primary_target": "benefit = low incorrect and high correct",
        "primary_model": "P3_state_interaction",
        "cohorts": cohorts,
        "primary_contrasts": {
            "P3_minus_P0_pr_auc": cluster_bootstrap_pr_auc_delta(
                records,
                all_indices,
                predictions["P3_state_interaction"],
                predictions["P0_process_only"],
                args.bootstrap,
                args.seed,
            ),
            "P3_minus_P2_pr_auc": cluster_bootstrap_pr_auc_delta(
                records,
                all_indices,
                predictions["P3_state_interaction"],
                predictions["P2_additive"],
                args.bootstrap,
                args.seed + 1,
            ),
        },
        "diagnostics": process_conditioned_diagnostics(records),
        "leave_one_model_out": leave_one_model_out_analysis(records),
        "cost_aware_policies": cost_aware_policy_simulation(records, predictions),
        "guardrails": [
            "All primary predictions are grouped out-of-fold by question_id.",
            "Confidence imputation and feature standardization use training folds only.",
            "Process profiles remove conclude from fine-grained structural features.",
            "Confidence is retrospective current-correctness confidence, not a direct probability of gain.",
            "Low/high Phase 3 calls are independent, not resumed generations.",
            "Parser-equivalence audit must be resolved before final interpretation.",
        ],
    }
    analysis["decision_checks"] = decision_checks(analysis)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "analysis": analysis}, handle, indent=2)
    with args.predictions.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "metadata": {
                    "schema_version": 1,
                    "source_sha256": metadata.get("source_sha256"),
                    "warning": (
                        "Scores are grouped out-of-fold. Low/high outcomes are independent calls."
                    ),
                },
                "records": serializable_predictions(records, predictions),
            },
            handle,
            indent=2,
        )
    make_figure(analysis, args.figure)
    args.report.write_text(make_report(metadata, analysis, args.figure), encoding="utf-8")
    print(f"Wrote Stage 1.6 analysis to {args.output}")
    print(f"Wrote Stage 1.6 predictions to {args.predictions}")
    print(f"Wrote Stage 1.6 report to {args.report}")
    print(f"Wrote Stage 1.6 figure to {args.figure}")


if __name__ == "__main__":
    main()
