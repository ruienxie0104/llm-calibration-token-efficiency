#!/usr/bin/env python3
"""Build a source-aware audit of confidence, visible progress, correctness, and tokens.

This analysis makes no API calls.  It intentionally keeps Phase 3 process records
and Soft QOQ confidence records in separate experimental strata: they share a
canonical row schema, but are never treated as one pooled experiment.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results"
sys.path.insert(0, str(SCRIPT_DIR))

from answer_utils import extract_boxed, is_correct  # noqa: E402


PHASE3_INPUT = RESULTS_DIR / "process_poc_dataset.json"
SOFT_INPUT = RESULTS_DIR / "soft_pilot_raw.json"
PROSPECTIVE_INPUT = RESULTS_DIR / "prospective_conf_full.json"
STAGE16_INPUT = RESULTS_DIR / "process_stage1_6_analysis.json"

DEFAULT_TABLE = RESULTS_DIR / "process_confidence_audit_table.json"
DEFAULT_ANALYSIS = RESULTS_DIR / "process_confidence_audit_analysis.json"
DEFAULT_REPORT = RESULTS_DIR / "process_confidence_audit_report.md"
DEFAULT_FIGURE = RESULTS_DIR / "process_confidence_audit_summary.png"

STATE_ORDER = ("complete", "visible_unfinished", "empty_unfinished")
TIMING_ORDER = ("prospective", "retrospective")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase3-input", type=Path, default=PHASE3_INPUT)
    parser.add_argument("--soft-input", type=Path, default=SOFT_INPUT)
    parser.add_argument("--prospective-input", type=Path, default=PROSPECTIVE_INPUT)
    parser.add_argument("--stage16-input", type=Path, default=STAGE16_INPUT)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260918)
    return parser.parse_args()


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def state_from_visible_response(response: str, expected_answer: str) -> tuple[str, str, bool]:
    parsed = extract_boxed(response or "")
    if parsed:
        return "complete", parsed, bool(is_correct(parsed, expected_answer))
    if response and response.strip():
        return "visible_unfinished", "", False
    return "empty_unfinished", "", False


def state_from_process_record(record: dict) -> str:
    if record.get("low_has_parsed_answer"):
        return "complete"
    if record.get("activity_sequence"):
        return "visible_unfinished"
    return "empty_unfinished"


def canonical_row(**values) -> dict:
    required = {
        "source",
        "protocol",
        "state_definition",
        "confidence_timing",
        "model",
        "question_id",
        "replicate",
        "budget",
        "process_state",
        "confidence",
        "confidence_missing",
        "correct",
        "answer_completion_tokens",
        "confidence_total_tokens",
        "benefit",
    }
    missing = required - set(values)
    if missing:
        raise ValueError(f"Canonical row missing fields: {sorted(missing)}")
    return values


def build_phase3_rows(path: Path) -> list[dict]:
    payload = read_json(path)
    records = payload.get("records", [])
    if not records:
        raise ValueError(f"No records in {path}")

    rows = []
    for record in records:
        confidence = record.get("confidence")
        rows.append(
            canonical_row(
                source="phase3_process_poc",
                protocol="Phase 3 independent low/high calls (512 to 1024)",
                state_definition="event-derived low-budget visible process state",
                confidence_timing="retrospective",
                model=record["model"],
                question_id=record["question_id"],
                replicate=record["replicate"],
                budget=record.get("low_budget"),
                process_state=state_from_process_record(record),
                confidence=confidence,
                confidence_missing=confidence is None,
                correct=bool(record.get("low_correct")),
                answer_completion_tokens=record.get("low_completion_tokens"),
                confidence_total_tokens=record.get("confidence_total_tokens"),
                benefit=record.get("benefit"),
                high_correct=record.get("high_correct"),
                subject=record.get("subject"),
                level=record.get("level"),
            )
        )
    return rows


def keyed(rows: list[dict]) -> dict[tuple, dict]:
    result = {}
    for row in rows:
        key = (row["model"], row["question_id"], row["budget"], row["replicate"])
        if key in result:
            raise ValueError(f"Duplicate source key: {key}")
        result[key] = row
    return result


def build_soft_rows(soft_path: Path, prospective_path: Path) -> list[dict]:
    raw = read_json(soft_path)
    prospective = read_json(prospective_path)
    answers = [row for row in raw if row.get("call_type") == "answer"]
    retrospective = [row for row in raw if row.get("call_type") == "confidence"]
    answer_map = keyed(answers)
    retrospective_map = keyed(retrospective)
    prospective_map = keyed(prospective)

    rows = []
    for key, answer in answer_map.items():
        state, parsed, rescored_correct = state_from_visible_response(
            answer.get("response", ""), answer.get("expected_answer", "")
        )
        common = {
            "source": "soft_qoq",
            "protocol": "Soft QOQ answer prompt with approximately-N-token instruction",
            "state_definition": "answer response has parseable final answer / visible text / empty",
            "model": answer["model"],
            "question_id": answer["question_id"],
            "replicate": answer["replicate"],
            "budget": answer["budget"],
            "process_state": state,
            "correct": rescored_correct,
            "answer_completion_tokens": answer.get("completion_tokens"),
            "benefit": None,
            "high_correct": None,
            "subject": answer.get("subject"),
            "level": answer.get("level"),
            "parsed_answer": parsed,
        }
        prospective_row = prospective_map.get(key)
        prospective_value = (
            prospective_row.get("prospective_confidence") if prospective_row else None
        )
        rows.append(
            canonical_row(
                **common,
                confidence_timing="prospective",
                confidence=prospective_value,
                confidence_missing=prospective_value is None,
                confidence_total_tokens=(
                    prospective_row.get("prompt_tokens", 0)
                    + prospective_row.get("completion_tokens", 0)
                    if prospective_row
                    else None
                ),
            )
        )
        retrospective_row = retrospective_map.get(key)
        retrospective_value = (
            retrospective_row.get("confidence_value") if retrospective_row else None
        )
        rows.append(
            canonical_row(
                **common,
                confidence_timing="retrospective",
                confidence=retrospective_value,
                confidence_missing=retrospective_value is None,
                confidence_total_tokens=(
                    retrospective_row.get("prompt_tokens", 0)
                    + retrospective_row.get("completion_tokens", 0)
                    if retrospective_row
                    else None
                ),
            )
        )
    return rows


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def brier(rows: list[dict]) -> float | None:
    usable = [row for row in rows if row["confidence"] is not None]
    if not usable:
        return None
    return mean(
        [((float(row["confidence"]) / 100.0) - float(row["correct"])) ** 2 for row in usable]
    )


def ece(rows: list[dict]) -> float | None:
    usable = [row for row in rows if row["confidence"] is not None]
    if not usable:
        return None
    total = len(usable)
    value = 0.0
    for lower in range(0, 100, 10):
        upper = lower + 10
        bucket = [
            row
            for row in usable
            if lower <= float(row["confidence"]) < upper
            or (upper == 100 and lower <= float(row["confidence"]) <= upper)
        ]
        if bucket:
            confidence_mean = mean([float(row["confidence"]) / 100.0 for row in bucket])
            accuracy_mean = mean([float(row["correct"]) for row in bucket])
            value += abs(confidence_mean - accuracy_mean) * len(bucket) / total
    return value


def auroc(rows: list[dict]) -> float | None:
    usable = [row for row in rows if row["confidence"] is not None]
    positives = [float(row["confidence"]) for row in usable if row["correct"]]
    negatives = [float(row["confidence"]) for row in usable if not row["correct"]]
    if not positives or not negatives:
        return None
    # Mann-Whitney U equivalent, with average ranks for ties.
    ranked = sorted(
        (value, label) for value, label in [(v, 1) for v in positives] + [(v, 0) for v in negatives]
    )
    rank_sum = 0.0
    index = 0
    while index < len(ranked):
        end = index
        while end < len(ranked) and ranked[end][0] == ranked[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        rank_sum += average_rank * sum(label for _, label in ranked[index:end])
        index = end
    u = rank_sum - len(positives) * (len(positives) + 1) / 2
    return u / (len(positives) * len(negatives))


def group_metrics(rows: list[dict]) -> dict:
    usable = [row for row in rows if row["confidence"] is not None]
    confidences = [float(row["confidence"]) for row in usable]
    tokens = [
        float(row["answer_completion_tokens"])
        for row in usable
        if row["answer_completion_tokens"] is not None
    ]
    token_pairs = [
        (float(row["confidence"]), float(row["answer_completion_tokens"]))
        for row in usable
        if row["answer_completion_tokens"] is not None
    ]
    correct_confidences = [float(row["confidence"]) for row in usable if row["correct"]]
    incorrect_confidences = [float(row["confidence"]) for row in usable if not row["correct"]]
    correlation = None
    if (
        len(token_pairs) >= 3
        and len({pair[0] for pair in token_pairs}) > 1
        and len({pair[1] for pair in token_pairs}) > 1
    ):
        correlation = float(spearmanr(*zip(*token_pairs)).statistic)
    return {
        "n": len(rows),
        "unique_questions": len({row["question_id"] for row in rows}),
        "usable_confidence_n": len(usable),
        "missing_confidence_n": len(rows) - len(usable),
        "accuracy": mean([float(row["correct"]) for row in rows]),
        "mean_confidence": mean(confidences),
        "mean_answer_completion_tokens": mean(tokens),
        "mean_confidence_total_tokens": mean(
            [
                float(row["confidence_total_tokens"])
                for row in usable
                if row["confidence_total_tokens"] is not None
            ]
        ),
        "brier": brier(rows),
        "ece": ece(rows),
        "auroc": auroc(rows),
        "confidence_gap_correct_minus_incorrect": (
            mean(correct_confidences) - mean(incorrect_confidences)
            if correct_confidences and incorrect_confidences
            else None
        ),
        "spearman_confidence_vs_answer_tokens": correlation,
    }


def grouped_metrics(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output = []
    for key, values in sorted(groups.items()):
        output.append({**dict(zip(fields, key)), **group_metrics(values)})
    return output


def bootstrap_confidence_difference(
    left: list[dict], right: list[dict], draws: int, seed: int
) -> dict:
    usable_left = [row for row in left if row["confidence"] is not None]
    usable_right = [row for row in right if row["confidence"] is not None]
    left_groups: dict[str, list[dict]] = defaultdict(list)
    right_groups: dict[str, list[dict]] = defaultdict(list)
    for row in usable_left:
        left_groups[row["question_id"]].append(row)
    for row in usable_right:
        right_groups[row["question_id"]].append(row)
    group_ids = sorted(set(left_groups) | set(right_groups))
    if len(group_ids) < 3:
        return {"estimate": None, "ci_low": None, "ci_high": None, "valid_draws": 0}
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        sample = [rng.choice(group_ids) for _ in group_ids]
        left_values = [
            float(row["confidence"]) for qid in sample for row in left_groups.get(qid, [])
        ]
        right_values = [
            float(row["confidence"]) for qid in sample for row in right_groups.get(qid, [])
        ]
        if left_values and right_values:
            values.append(mean(left_values) - mean(right_values))
    if not values:
        return {"estimate": None, "ci_low": None, "ci_high": None, "valid_draws": 0}
    values.sort()
    return {
        "estimate": mean([float(row["confidence"]) for row in usable_left])
        - mean([float(row["confidence"]) for row in usable_right]),
        "ci_low": values[int(0.025 * len(values))],
        "ci_high": values[int(0.975 * len(values))],
        "valid_draws": len(values),
    }


def state_contrasts(rows: list[dict], draws: int, seed: int) -> list[dict]:
    fields = ("source", "confidence_timing", "model", "budget")
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output = []
    for group_index, (key, values) in enumerate(sorted(groups.items())):
        by_state: dict[str, list[dict]] = defaultdict(list)
        for row in values:
            by_state[row["process_state"]].append(row)
        for comparator in ("visible_unfinished", "empty_unfinished"):
            if by_state["complete"] and by_state[comparator]:
                result = bootstrap_confidence_difference(
                    by_state["complete"], by_state[comparator], draws, seed + group_index
                )
                output.append(
                    {
                        **dict(zip(fields, key)),
                        "contrast": f"complete_minus_{comparator}",
                        **result,
                    }
                )
    return output


def stage16_context(path: Path) -> dict:
    if not path.exists():
        return {"available": False}
    payload = read_json(path)
    analysis = payload.get("analysis", {})
    contrast = analysis.get("primary_contrasts", {}).get("P3_minus_P0_pr_auc", {})
    return {
        "available": bool(analysis),
        "record_count": analysis.get("record_count"),
        "primary_contrast": contrast,
        "interpretation": (
            "Existing Stage 1.6 tests incremental predictive value for benefit; "
            "this audit is descriptive and does not replace that test."
        ),
    }


def save_figure(summary_rows: list[dict], path: Path) -> None:
    panels = [row for row in summary_rows if row["usable_confidence_n"] > 0]
    colors = {"complete": "#1f77b4", "visible_unfinished": "#ff7f0e", "empty_unfinished": "#2ca02c"}

    def grouped_bars(axis, rows, title, label_fn):
        groups = sorted({(row["model"], row["budget"]) for row in rows})
        positions = list(range(len(groups)))
        width = 0.24
        for state_index, state in enumerate(STATE_ORDER):
            values = []
            for group in groups:
                match = next(
                    (
                        row
                        for row in rows
                        if (row["model"], row["budget"]) == group and row["process_state"] == state
                    ),
                    None,
                )
                values.append(match["mean_confidence"] if match else float("nan"))
            offset = (state_index - 1) * width
            axis.bar(
                [position + offset for position in positions],
                values,
                width=width,
                label=state,
                color=colors[state],
            )
        axis.set_title(title)
        axis.set_ylabel("Mean confidence (%)")
        axis.set_xticks(
            positions, [label_fn(model, budget) for model, budget in groups], fontsize=8
        )
        axis.set_ylim(0, 105)
        axis.grid(axis="y", alpha=0.25)

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    phase_rows = [row for row in panels if row["source"] == "phase3_process_poc"]
    grouped_bars(
        axes[0, 0],
        phase_rows,
        "Phase 3 retrospective confidence",
        lambda model, _: model.replace("-V4-Flash-158B", "").replace("-5.2-756B", ""),
    )
    prospective_rows = [
        row
        for row in panels
        if row["source"] == "soft_qoq" and row["confidence_timing"] == "prospective"
    ]
    grouped_bars(
        axes[0, 1],
        prospective_rows,
        "Soft QOQ prospective confidence",
        lambda model,
        budget: f"{model.replace('-OSS-', '-').replace('-V4-Flash-158B', '')}\n{budget}",
    )
    retrospective_rows = [
        row
        for row in panels
        if row["source"] == "soft_qoq" and row["confidence_timing"] == "retrospective"
    ]
    grouped_bars(
        axes[1, 0],
        retrospective_rows,
        "Soft QOQ retrospective confidence",
        lambda model,
        budget: f"{model.replace('-OSS-', '-').replace('-V4-Flash-158B', '')}\n{budget}",
    )
    axes[0, 0].legend(fontsize=8, loc="lower left")

    scatter_axis = axes[1, 1]
    for state in STATE_ORDER:
        state_rows = [
            row
            for row in panels
            if row["process_state"] == state
            and row["mean_answer_completion_tokens"] is not None
            and row["mean_confidence"] is not None
        ]
        scatter_axis.scatter(
            [row["mean_answer_completion_tokens"] for row in state_rows],
            [row["mean_confidence"] for row in state_rows],
            s=55,
            label=state,
            color=colors[state],
        )
    scatter_axis.set_title("State-stratified answer cost vs confidence")
    scatter_axis.set_xlabel("Mean answer completion tokens")
    scatter_axis.set_ylabel("Mean confidence (%)")
    scatter_axis.grid(alpha=0.25)
    scatter_axis.legend(fontsize=8)
    fig.suptitle("Process-conditioned confidence audit (descriptive, source-stratified)")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def write_report(
    path: Path,
    metadata: dict,
    overall_summaries: list[dict],
    summaries: list[dict],
    contrasts: list[dict],
    stage16: dict,
) -> None:
    lines = [
        "# Process-conditioned confidence audit",
        "",
        "## Scope and guardrails",
        "",
        "- No API calls were made.",
        "- Rows share a common schema but are analysed within source, confidence timing, model, and budget strata.",
        "- This is a descriptive mechanism audit; it does not make a causal continuation claim.",
        "- Prospective and retrospective confidence are not pooled because they answer different questions.",
        "",
        "## Data inventory",
        "",
        "| Source | Rows | Usable confidence | Missing confidence |",
        "|---|---:|---:|---:|",
    ]
    for source, values in sorted(metadata["source_inventory"].items()):
        lines.append(
            f"| {source} | {values['rows']} | {values['usable_confidence']} | {values['missing_confidence']} |"
        )

    lines.extend(
        [
            "",
            "## Overall confidence and answer-token association",
            "",
            "These rows retain all process states within each experimental stratum; state-specific results follow below.",
            "",
            "| Source | Timing | Model | Budget | n | Acc. | Mean conf. | Brier | ECE | Conf-token rho |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in overall_summaries:
        lines.append(
            "| {source} | {confidence_timing} | {model} | {budget} | {n} | {accuracy} | {mean_confidence} | {brier} | {ece} | {spearman_confidence_vs_answer_tokens} |".format(
                **{
                    **row,
                    "accuracy": fmt(row["accuracy"]),
                    "mean_confidence": fmt(row["mean_confidence"], 1),
                    "brier": fmt(row["brier"]),
                    "ece": fmt(row["ece"]),
                    "spearman_confidence_vs_answer_tokens": fmt(
                        row["spearman_confidence_vs_answer_tokens"]
                    ),
                }
            )
        )

    lines.extend(
        [
            "",
            "## State-stratified descriptive summaries",
            "",
            "| Source | Timing | Model | Budget | State | n | Acc. | Mean conf. | Brier | ECE | Mean answer tok. | Conf-token rho |",
            "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        lines.append(
            "| {source} | {confidence_timing} | {model} | {budget} | {process_state} | {n} | {accuracy} | {mean_confidence} | {brier} | {ece} | {mean_answer_completion_tokens} | {spearman_confidence_vs_answer_tokens} |".format(
                **{
                    **row,
                    "accuracy": fmt(row["accuracy"]),
                    "mean_confidence": fmt(row["mean_confidence"], 1),
                    "brier": fmt(row["brier"]),
                    "ece": fmt(row["ece"]),
                    "mean_answer_completion_tokens": fmt(row["mean_answer_completion_tokens"], 1),
                    "spearman_confidence_vs_answer_tokens": fmt(
                        row["spearman_confidence_vs_answer_tokens"]
                    ),
                }
            )
        )

    lines.extend(
        [
            "",
            "## Confidence contrast: complete minus unfinished",
            "",
            "Positive values mean complete cases report higher confidence. CIs resample question IDs.",
            "",
            "| Source | Timing | Model | Budget | Contrast | Estimate | 95% CI |",
            "|---|---|---|---:|---|---:|---:|",
        ]
    )
    for row in contrasts:
        lines.append(
            f"| {row['source']} | {row['confidence_timing']} | {row['model']} | {row['budget']} | {row['contrast']} | {fmt(row['estimate'], 1)} | [{fmt(row['ci_low'], 1)}, {fmt(row['ci_high'], 1)}] |"
        )

    lines.extend(["", "## Relation to the Stage 1.6 allocation result", ""])
    if stage16.get("available"):
        contrast = stage16.get("primary_contrast", {})
        lines.append(
            "Existing grouped OOF incremental-benefit contrast, P3 state interaction minus P0 process-only: "
            f"estimate={fmt(contrast.get('estimate'))}, "
            f"CI=[{fmt(contrast.get('ci_low'))}, {fmt(contrast.get('ci_high'))}]."
        )
        lines.append(
            "This audit explains alignment and mismatch patterns; it does not reinterpret a non-positive incremental allocation contrast as operational value."
        )
    else:
        lines.append("Stage 1.6 analysis file was not available.")

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "A confidence–state association is not evidence that confidence should control token allocation. "
            "The deployable method remains visible-progress allocation; this audit documents when self-reported confidence agrees with observable progress and when it does not.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    phase3_rows = build_phase3_rows(args.phase3_input)
    soft_rows = build_soft_rows(args.soft_input, args.prospective_input)
    rows = phase3_rows + soft_rows
    if not rows:
        raise ValueError("No aligned audit rows were built")

    source_inventory = {}
    for source in sorted({row["source"] for row in rows}):
        values = [row for row in rows if row["source"] == source]
        source_inventory[source] = {
            "rows": len(values),
            "usable_confidence": sum(row["confidence"] is not None for row in values),
            "missing_confidence": sum(row["confidence"] is None for row in values),
            "models": sorted({row["model"] for row in values}),
            "budgets": sorted({row["budget"] for row in values}),
        }
    metadata = {
        "schema_version": 1,
        "unit": "source-model-question-replicate-confidence_timing",
        "row_count": len(rows),
        "source_inventory": source_inventory,
        "guardrails": [
            "No pooling across source protocols, confidence timing, model, or budget.",
            "Process state definitions differ by source and are preserved in each row.",
            "This is descriptive; Stage 2P remains the causal allocation experiment.",
        ],
    }
    summary_fields = ("source", "confidence_timing", "model", "budget", "process_state")
    summaries = grouped_metrics(rows, summary_fields)
    overall_fields = ("source", "confidence_timing", "model", "budget")
    overall_summaries = grouped_metrics(rows, overall_fields)
    contrasts = state_contrasts(rows, args.bootstrap, args.seed)
    stage16 = stage16_context(args.stage16_input)

    args.table.write_text(
        json.dumps({"metadata": metadata, "rows": rows}, indent=2), encoding="utf-8"
    )
    args.analysis.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "overall_summaries": overall_summaries,
                "state_summaries": summaries,
                "state_contrasts": contrasts,
                "stage1_6_context": stage16,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_report(args.report, metadata, overall_summaries, summaries, contrasts, stage16)
    save_figure(summaries, args.figure)
    print(f"Built {len(rows)} audit rows")
    print(f"Table: {args.table}")
    print(f"Analysis: {args.analysis}")
    print(f"Report: {args.report}")
    print(f"Figure: {args.figure}")


if __name__ == "__main__":
    main()
