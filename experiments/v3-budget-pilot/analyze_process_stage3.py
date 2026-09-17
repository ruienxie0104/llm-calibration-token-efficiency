#!/usr/bin/env python3
"""Analyse the frozen Stage 3 visible-only allocation policy.

The primary random comparator is a cost-calibrated *evaluation* benchmark: its
expected realised continuation cost equals the visible-only policy exactly.  It
is not represented as an online policy that knows future request costs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results"
MANIFEST_PATH = SCRIPT_DIR / "data" / "process_stage3_questions.json"
RAW_PATH = RESULTS_DIR / "process_stage3_formal_raw.json"
EXPECTED_MODELS = ("GPT-OSS-120B", "DeepSeek-V4-Flash-158B")
N_BOOTSTRAP = 10_000
N_LEDGER_SEEDS = 10_000
RANDOM_SEED = 20260918


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fingerprint(questions: list[dict[str, Any]]) -> str:
    return hashlib.sha256("\n".join(q["id"] for q in questions).encode("utf-8")).hexdigest()


def load_manifest() -> tuple[list[str], dict[str, int]]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    formal = manifest["splits"]["formal"]
    require(len(formal) == 60, "Stage 3 manifest must contain 60 formal questions.")
    require(manifest.get("all_question_ids_sha256"), "Manifest lacks ID fingerprint.")
    return [q["id"] for q in formal], {q["id"]: int(q.get("level", 3)) for q in formal}


def load_records(path: Path = RAW_PATH) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records", [])
    ids, levels = load_manifest()
    require(len(records) == 240, f"Expected 240 formal records, found {len(records)}.")
    require(not [r for r in records if r.get("error")], "Formal raw file contains API errors.")
    require(all(r.get("stage") == "formal" for r in records), "Raw file mixes non-formal records.")
    models = sorted({r.get("model") for r in records})
    require(set(models) == set(EXPECTED_MODELS), f"Unexpected models: {models}")
    expected = {(model, qid, action) for model in EXPECTED_MODELS for qid in ids for action in ("prefix", "continuation")}
    got = {(r.get("model"), r.get("question_id"), r.get("action")) for r in records}
    require(got == expected and len(got) == len(records), "Raw records have missing or duplicate actions.")
    schema = payload.get("schema", {})
    require(schema.get("question_ids_sha256") == fingerprint([{"id": q} for q in ids]), "Raw/manifest ID fingerprint mismatch.")
    return records, ids, levels


def index_records(records: Iterable[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["model"], r["question_id"], r["action"]): r for r in records}


def final_correct(index: dict[tuple[str, str, str], dict[str, Any]], model: str, qid: str) -> bool:
    continuation = index[(model, qid, "continuation")]
    if continuation.get("parsed_answer"):
        return bool(continuation.get("correct"))
    prefix = index[(model, qid, "prefix")]
    return bool(prefix.get("correct")) if prefix.get("parsed_answer") else False


def unit(index: dict[tuple[str, str, str], dict[str, Any]], model: str, qid: str, level: int) -> dict[str, Any]:
    prefix = index[(model, qid, "prefix")]
    continuation = index[(model, qid, "continuation")]
    state = prefix.get("process_state")
    require(state in {"complete", "visible_unfinished", "empty_unfinished"}, f"Invalid state {state!r}")
    low = bool(prefix.get("correct"))
    high = final_correct(index, model, qid)
    return {"qid": qid, "level": level, "state": state, "visible": state == "visible_unfinished",
            "low": int(low), "high": int(high), "gain": int(high) - int(low),
            "prefix_tokens": float(prefix.get("total_tokens", 0)),
            "continuation_tokens": float(continuation.get("total_tokens", 0)),
            "continuation_parseable": bool(continuation.get("parsed_answer")),
            "continuation_done_reason": continuation.get("done_reason")}


def visible_policy(rows: list[dict[str, Any]]) -> dict[str, float]:
    n = len(rows)
    selected = [row for row in rows if row["visible"]]
    accuracy = sum(row["high"] if row["visible"] else row["low"] for row in rows) / n
    tokens = sum(row["prefix_tokens"] + (row["continuation_tokens"] if row["visible"] else 0) for row in rows) / n
    continuation_cost = sum(row["continuation_tokens"] for row in selected)
    return {"accuracy": accuracy, "mean_tokens": tokens, "continuation_cost": continuation_cost,
            "n_continue": len(selected), "visible_count": len(selected)}


def cost_calibrated_random(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Expected metrics of signal-free Bernoulli random allocation.

    The probability is chosen from the action bank so expected continuation
    token cost exactly matches the visible-only policy.  This is an evaluation
    comparator, not an online scheduler.
    """
    n = len(rows)
    target = sum(row["continuation_tokens"] for row in rows if row["visible"])
    denominator = sum(row["continuation_tokens"] for row in rows)
    probability = target / denominator if denominator else 0.0
    require(-1e-12 <= probability <= 1 + 1e-12, "Invalid random probability.")
    accuracy = sum(row["low"] + probability * row["gain"] for row in rows) / n
    mean_tokens = sum(row["prefix_tokens"] + probability * row["continuation_tokens"] for row in rows) / n
    return {"accuracy": accuracy, "mean_tokens": mean_tokens, "expected_continuation_cost": probability * denominator,
            "target_continuation_cost": target, "probability": probability,
            "cost_identity_error": probability * denominator - target,
            "expected_n_continue": probability * n}


def rank_by_level(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (-row["level"], hashlib.md5(row["qid"].encode()).hexdigest()))


def selected_metrics(rows: list[dict[str, Any]], selected_qids: set[str]) -> dict[str, float]:
    n = len(rows)
    accuracy = sum(row["high"] if row["qid"] in selected_qids else row["low"] for row in rows) / n
    tokens = sum(row["prefix_tokens"] + (row["continuation_tokens"] if row["qid"] in selected_qids else 0) for row in rows) / n
    return {"accuracy": accuracy, "mean_tokens": tokens, "n_continue": len(selected_qids),
            "continuation_cost": sum(row["continuation_tokens"] for row in rows if row["qid"] in selected_qids)}


def fixed_and_question_policies(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    n = len(rows)
    visible_qids = {row["qid"] for row in rows if row["visible"]}
    k = len(visible_qids)
    low = selected_metrics(rows, set())
    high = selected_metrics(rows, {row["qid"] for row in rows})
    question = selected_metrics(rows, {row["qid"] for row in rank_by_level(rows)[:k]})
    probability = k / n if n else 0.0
    random_count = {
        "accuracy": sum(row["low"] + probability * row["gain"] for row in rows) / n,
        "mean_tokens": sum(row["prefix_tokens"] + probability * row["continuation_tokens"] for row in rows) / n,
        "expected_n_continue": float(k),
    }
    ranked_oracle = sorted(rows, key=lambda row: (-row["gain"], hashlib.md5(row["qid"].encode()).hexdigest()))
    oracle_count = selected_metrics(rows, {row["qid"] for row in ranked_oracle[:k]})
    return {"fixed_low": low, "fixed_continue": high, "random_count_matched": random_count,
            "question_only_count_matched": question, "oracle_count_matched": oracle_count}


def oracle_cost_constrained(rows: list[dict[str, Any]], budget: float) -> dict[str, float]:
    """0/1 knapsack over positive integer-rounded costs; deterministic upper bound."""
    scale = 1  # request token counts are integer; retain a named scale for auditability.
    max_budget = int(round(budget * scale))
    candidates = [(int(round(row["continuation_tokens"] * scale)), row["gain"], row["qid"]) for row in rows]
    # Map each budget to (gain, sorted qids), retaining deterministic tie-breaks.
    states: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for cost, gain, qid in candidates:
        if cost <= 0:
            continue
        for used, prior in list(states.items())[::-1]:
            new_used = used + cost
            if new_used > max_budget:
                continue
            candidate = (prior[0] + gain, tuple(sorted(prior[1] + (qid,))))
            current = states.get(new_used)
            if current is None or candidate[0] > current[0] or (candidate[0] == current[0] and candidate[1] < current[1]):
                states[new_used] = candidate
    best_used, best = max(states.items(), key=lambda item: (item[1][0], -item[0], tuple(reversed(item[1][1]))))
    metrics = selected_metrics(rows, set(best[1]))
    metrics.update({"oracle_gain": best[0], "budget": budget, "used_continuation_cost": best_used / scale})
    return metrics


def random_ledger_replay(rows: list[dict[str, Any]], draws: int = N_LEDGER_SEEDS, seed: int = RANDOM_SEED) -> dict[str, float]:
    """Secondary online-style random allocation with reportable final-call overshoot."""
    budget = sum(row["continuation_tokens"] for row in rows if row["visible"])
    rng = random.Random(seed)
    accuracies, costs, counts = [], [], []
    base_cost = sum(row["prefix_tokens"] for row in rows)
    for _ in range(draws):
        order = list(rows)
        rng.shuffle(order)
        selected: set[str] = set()
        spent = 0.0
        for row in order:
            if spent >= budget:
                break
            selected.add(row["qid"])
            spent += row["continuation_tokens"]
        metrics = selected_metrics(rows, selected)
        accuracies.append(metrics["accuracy"])
        costs.append((base_cost + spent) / len(rows))
        counts.append(len(selected))
    sorted_costs = sorted(costs)
    return {"accuracy": sum(accuracies) / draws, "mean_tokens": sum(costs) / draws,
            "mean_n_continue": sum(counts) / draws, "ledger": budget,
            "cost_p025": sorted_costs[int(.025 * draws)], "cost_p975": sorted_costs[int(.975 * draws)], "draws": draws}


def bootstrap_delta(rows_by_model: dict[str, list[dict[str, Any]]], qids: list[str], n_bootstrap: int = N_BOOTSTRAP, seed: int = RANDOM_SEED) -> dict[str, float]:
    rng = random.Random(seed)
    diffs: list[float] = []
    rows_lookup = {model: {row["qid"]: row for row in rows} for model, rows in rows_by_model.items()}
    for _ in range(n_bootstrap):
        sampled = [qids[rng.randrange(len(qids))] for _ in qids]
        model_diffs = []
        for model in EXPECTED_MODELS:
            rows = [rows_lookup[model][qid] for qid in sampled]
            model_diffs.append(visible_policy(rows)["accuracy"] - cost_calibrated_random(rows)["accuracy"])
        diffs.append(sum(model_diffs) / len(model_diffs))
    diffs.sort()
    return {"delta_mean": sum(diffs) / len(diffs), "ci_lower": diffs[int(.025 * len(diffs))],
            "ci_upper": diffs[int(.975 * len(diffs))], "tail_prob": sum(x <= 0 for x in diffs) / len(diffs),
            "significant": diffs[int(.025 * len(diffs))] > 0, "n_bootstrap": n_bootstrap,
            "cluster_unit": "question_id"}


def state_outcomes(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    output: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if not row["continuation_parseable"]:
            outcome = "unresolved"
        elif row["gain"] > 0:
            outcome = "benefit"
        elif row["gain"] < 0:
            outcome = "harm"
        else:
            outcome = "unchanged"
        output[row["state"]][outcome] += 1
    return {state: dict(counts) for state, counts in output.items()}


def write_figure(model_results: dict[str, Any]) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for axis, model in zip(axes, EXPECTED_MODELS):
        policies = model_results[model]["policies"]
        for name, point in policies.items():
            axis.scatter(point["mean_tokens"], point["accuracy"] * 100, s=52)
            axis.annotate(name.replace("_", " "), (point["mean_tokens"], point["accuracy"] * 100), xytext=(4, 4), textcoords="offset points", fontsize=7)
        axis.set_title(model)
        axis.set_xlabel("Mean realised total tokens / question")
        axis.grid(alpha=.25)
    axes[0].set_ylabel("Final accuracy (%)")
    figure.suptitle("Stage 3 visible-progress allocation: accuracy vs realised cost")
    figure.tight_layout()
    output = RESULTS_DIR / "process_stage3_accuracy_cost.png"
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--bootstrap", type=int, default=N_BOOTSTRAP)
    parser.add_argument("--ledger-draws", type=int, default=N_LEDGER_SEEDS)
    args = parser.parse_args()
    records, qids, levels = load_records(args.raw)
    indexed = index_records(records)
    rows_by_model = {model: [unit(indexed, model, qid, levels[qid]) for qid in qids] for model in EXPECTED_MODELS}
    model_results: dict[str, Any] = {}
    primary_deltas: dict[str, float] = {}
    for model, rows in rows_by_model.items():
        visible = visible_policy(rows)
        random_cost = cost_calibrated_random(rows)
        require(abs(random_cost["cost_identity_error"]) < 1e-8, f"Cost identity failed for {model}")
        policies: dict[str, dict[str, float]] = {"visible_progress": visible, "random_cost_calibrated": random_cost}
        policies.update(fixed_and_question_policies(rows))
        policies["random_ledger_replay"] = random_ledger_replay(rows, args.ledger_draws)
        policies["oracle_cost_constrained"] = oracle_cost_constrained(rows, visible["continuation_cost"])
        primary_deltas[model] = visible["accuracy"] - random_cost["accuracy"]
        model_results[model] = {"n": len(rows), "states": dict(Counter(row["state"] for row in rows)),
                                "visible_support_pass": visible["visible_count"] >= 5, "policies": policies,
                                "primary": {"delta": primary_deltas[model], "cost_identity_error": random_cost["cost_identity_error"]},
                                "continuation_outcomes_by_state": state_outcomes(rows)}
    boot = bootstrap_delta(rows_by_model, qids, args.bootstrap)
    direction = all(primary_deltas[m] > 0 for m in EXPECTED_MODELS)
    support = all(model_results[m]["visible_support_pass"] for m in EXPECTED_MODELS)
    study = {"primary_contrast": "visible_progress_minus_cost_calibrated_random", "pooled": boot,
             "model_deltas": primary_deltas, "direction_consistent": direction, "visible_support_pass": support,
             "study_success": bool(boot["significant"] and direction and support),
             "random_comparator_boundary": "cost-calibrated random is an action-bank evaluation benchmark, not an online policy"}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    analysis_path = RESULTS_DIR / "process_stage3_analysis.json"
    with analysis_path.open("w", encoding="utf-8") as handle:
        json.dump({"models": model_results, "study": study}, handle, indent=2)
    audit = {"n_records": len(records), "question_count": len(qids), "models": list(EXPECTED_MODELS),
             "parseable_prefix": {m: sum(row["state"] == "complete" for row in rows_by_model[m]) for m in EXPECTED_MODELS},
             "parseable_continuation": {m: sum(row["continuation_parseable"] for row in rows_by_model[m]) for m in EXPECTED_MODELS}}
    with (RESULTS_DIR / "process_stage3_parser_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2)
    lines = ["# Stage 3 visible-progress confirmatory experiment", "", "## Primary result",
             f"Pooled Δ = {boot['delta_mean'] * 100:.2f}pp; 95% CI [{boot['ci_lower'] * 100:.2f}, {boot['ci_upper'] * 100:.2f}] pp.",
             f"Direction consistent={direction}; visible-state support pass={support}; study success={study['study_success']}.",
             "", "The random primary comparator is a cost-calibrated action-bank evaluation benchmark, not an online policy.", ""]
    for model in EXPECTED_MODELS:
        result = model_results[model]
        lines += [f"## {model}", f"States: {result['states']}; visible support pass={result['visible_support_pass']}.",
                  f"Primary Δ: {result['primary']['delta'] * 100:.2f}pp; cost identity error={result['primary']['cost_identity_error']:.9f}.",
                  "", "| Policy | Accuracy | Mean total tokens |", "|---|---:|---:|"]
        for name, point in result["policies"].items():
            lines.append(f"| {name} | {point['accuracy'] * 100:.2f}% | {point['mean_tokens']:.1f} |")
        lines += ["", f"Continuation outcomes by prefix state: {result['continuation_outcomes_by_state']}", ""]
    with (RESULTS_DIR / "process_stage3_report.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    figure = write_figure(model_results)
    print(f"Saved {analysis_path}; report, parser audit, and {figure}")


if __name__ == "__main__":
    main()
