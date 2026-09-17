#!/usr/bin/env python3
"""Recompute Stage 2 Gate 0/Gate 1 evidence metrics from raw action logs only."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RAW = SCRIPT_DIR / "results" / "process_stage2_raw.json"
DEFAULT_ANALYSIS = SCRIPT_DIR / "results" / "process_stage2_analysis.json"
DEFAULT_REPORT = SCRIPT_DIR / "results" / "process_stage2_report.md"
DEFAULT_AUDIT = SCRIPT_DIR / "results" / "process_stage2_audit.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    return parser.parse_args()


def rate(rows: list[dict], key: str) -> float | None:
    valid = [row for row in rows if row is not None]
    return None if not valid else sum(bool(row.get(key)) for row in valid) / len(valid)


def mean_total_tokens(rows: list[dict]) -> float | None:
    if not rows:
        return None
    return sum(int(row.get("prompt_tokens", 0)) + int(row.get("completion_tokens", 0)) for row in rows) / len(rows)


def conditional_rate(rows: list[dict], condition: str, outcome: str) -> dict:
    selected = [row for row in rows if row[condition]]
    return {"n": len(selected), "rate": rate(selected, outcome)}


def main() -> None:
    args = parse_args()
    with args.raw.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records", [])
    if not records:
        raise SystemExit("Raw action log is empty; no analysis produced.")
    grouped: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for row in records:
        grouped[(row["stage"], row["model"], row["question_id"])][row["action"]] = row

    gate0, gate1, audit = {}, {}, []
    for key, actions in sorted(grouped.items()):
        stage, model, question_id = key
        prefix = actions.get("prefix")
        if prefix is None:
            continue
        row_audit = {"stage": stage, "model": model, "question_id": question_id,
                     "process_state": prefix.get("process_state"), "actions": {}}
        for action, row in actions.items():
            row_audit["actions"][action] = {field: row.get(field) for field in
                ("parsed_answer", "normalized_answer", "correct", "error", "done_reason", "prompt_tokens", "completion_tokens", "context_mode")}
        audit.append(row_audit)
        if stage == "gate0" and "continuation" in actions and "fresh_high" in actions:
            block = gate0.setdefault(model, [])
            block.append({"prefix": prefix, "continuation": actions["continuation"], "fresh_high": actions["fresh_high"]})
        if stage in {"gate1", "formal"} and prefix.get("process_state") == "empty_unfinished":
            if "branch_1" in actions and "branch_2" in actions and "continuation" in actions:
                b1, b2, cont = actions["branch_1"], actions["branch_2"], actions["continuation"]
                parseable = bool(b1.get("normalized_answer")) and bool(b2.get("normalized_answer"))
                gate1.setdefault(model, []).append({
                    "parseable_pair": parseable,
                    "agree": parseable and b1["normalized_answer"] == b2["normalized_answer"],
                    "branch_consensus_correct": bool(parseable and b1["normalized_answer"] == b2["normalized_answer"] and b1.get("correct")),
                    "continuation_correct": bool(cont.get("correct")),
                    "branch_total_tokens": sum(int(x.get("prompt_tokens", 0)) + int(x.get("completion_tokens", 0)) for x in (b1, b2)),
                    "continuation_total_tokens": int(cont.get("prompt_tokens", 0)) + int(cont.get("completion_tokens", 0)),
                })

    result_gate0 = {}
    for model, rows in gate0.items():
        result_gate0[model] = {
            "n": len(rows), "prefix_parse_rate": rate([row["prefix"] for row in rows], "parsed_answer"),
            "continuation_parse_rate": rate([row["continuation"] for row in rows], "parsed_answer"),
            "fresh_high_parse_rate": rate([row["fresh_high"] for row in rows], "parsed_answer"),
            "prefix_accuracy": rate([row["prefix"] for row in rows], "correct"),
            "continuation_accuracy": rate([row["continuation"] for row in rows], "correct"),
            "fresh_high_accuracy": rate([row["fresh_high"] for row in rows], "correct"),
            "continuation_error_rate": rate([{"bad": bool(row["continuation"].get("error"))} for row in rows], "bad"),
            "mean_actual_total_tokens": {name: mean_total_tokens([row[name] for row in rows]) for name in ("prefix", "continuation", "fresh_high")},
        }
    result_gate1 = {}
    for model, rows in gate1.items():
        agreement_rows = [{**row, "disagree": row["parseable_pair"] and not row["agree"]} for row in rows]
        result_gate1[model] = {
            "n_empty_unfinished": len(rows), "branch_pair_parse_rate": rate(rows, "parseable_pair"),
            "agreement_rate_among_parseable": conditional_rate(agreement_rows, "parseable_pair", "agree"),
            "continuation_correct_given_agree": conditional_rate(agreement_rows, "agree", "continuation_correct"),
            "continuation_correct_given_disagree": conditional_rate(agreement_rows, "disagree", "continuation_correct"),
            "consensus_correct_given_agree": conditional_rate(agreement_rows, "agree", "branch_consensus_correct"),
            "mean_branch_total_tokens": sum(row["branch_total_tokens"] for row in rows) / len(rows) if rows else None,
            "mean_continuation_total_tokens": sum(row["continuation_total_tokens"] for row in rows) / len(rows) if rows else None,
        }
    analysis = {"schema_version": 1, "raw_metadata": payload.get("metadata", {}), "record_count": len(records),
                "unit_count": len(grouped), "gate0": result_gate0, "gate1": result_gate1}
    for path, content in ((args.analysis, analysis), (args.audit, {"schema_version": 1, "units": audit})):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, ensure_ascii=False)

    lines = ["# Stage 2 evidence-allocation report", "", "> Generated only from raw action logs. Gate results are feasibility diagnostics, not final causal claims.", "",
             "## Gate 0: visible-contextual continuation", "", "| Model | n | Prefix acc. | Continuation acc. | Fresh-high acc. | Continuation parse | Continuation errors |", "|---|---:|---:|---:|---:|---:|---:|"]
    for model, item in result_gate0.items():
        fmt = lambda value: "NA" if value is None else f"{value:.1%}"
        lines.append(f"| {model} | {item['n']} | {fmt(item['prefix_accuracy'])} | {fmt(item['continuation_accuracy'])} | {fmt(item['fresh_high_accuracy'])} | {fmt(item['continuation_parse_rate'])} | {fmt(item['continuation_error_rate'])} |")
    lines += ["", "## Gate 1: answer-consistency on empty unfinished cases", "", "| Model | n | Pair parse | Agree n / rate | Consensus correct given agree | Continue correct given agree | Continue correct given disagree |", "|---|---:|---:|---:|---:|---:|---:|"]
    for model, item in result_gate1.items():
        fmt = lambda value: "NA" if value is None else f"{value:.1%}"
        agree = item["agreement_rate_among_parseable"]
        lines.append(f"| {model} | {item['n_empty_unfinished']} | {fmt(item['branch_pair_parse_rate'])} | {agree['n']} / {fmt(agree['rate'])} | {fmt(item['consensus_correct_given_agree']['rate'])} | {fmt(item['continuation_correct_given_agree']['rate'])} | {fmt(item['continuation_correct_given_disagree']['rate'])} |")
    lines += ["", "## Interpretation guardrails", "", "- Continuation replays visible assistant content only; it cannot restore hidden reasoning state.", "- Agreement is not correctness. Report both agreement and gold-answer accuracy.", "- Do not enter the formal policy comparison unless the pre-specified Gate 0/Gate 1 criteria in `process_stage2_evidence_allocation_plan.md` are reviewed."]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote analysis: {args.analysis}\nWrote audit: {args.audit}\nWrote report: {args.report}")


if __name__ == "__main__":
    main()
