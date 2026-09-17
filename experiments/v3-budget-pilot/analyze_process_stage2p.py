#!/usr/bin/env python3
"""Stage 2P analysis: matched-K* policies and question-clustered inference."""

import json
import random
import hashlib
from pathlib import Path
from collections import Counter

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RANDOM_SEED = 20260917
N_BOOTSTRAP = 10000
ALPHA = 0.05
COST_PARITY_TOLERANCE = 0.05  # ±5%

FORMAL_FILE = "process_stage2p_formal_raw.json"
SMOKE_FILE = "process_stage2p_smoke.json"
EXPECTED_MODELS = {"GPT-OSS-120B", "DeepSeek-V4-Flash-158B"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def evaluate_cost_condition(process_accuracy, random_accuracy, process_tokens, random_tokens):
    cost_ratio = process_tokens / random_tokens if random_tokens > 0 else 1.0
    cost_parity = abs(cost_ratio - 1.0) <= COST_PARITY_TOLERANCE
    pareto_improving = process_accuracy > random_accuracy and cost_ratio <= 1.0
    return cost_ratio, cost_parity, pareto_improving, cost_parity or pareto_improving


def load_manifest():
    mpath = Path(__file__).resolve().parent / "data" / "process_stage2_questions.json"
    with open(mpath) as f:
        data = json.load(f)
    formal = data["splits"]["formal"]
    ids = sorted(q["id"] for q in formal)
    levels = {q["id"]: q.get("level", 3) for q in formal}
    return ids, levels, {q["id"]: q for q in formal}


def load_data(stage="formal"):
    fname = FORMAL_FILE if stage == "formal" else SMOKE_FILE
    p = RESULTS_DIR / fname
    with open(p) as f:
        data = json.load(f)
    records = data["records"]

    formal_ids, manifest_levels, manifest_qs = load_manifest()
    model_ids = sorted(set(r["model"] for r in records))

    if stage == "formal":
        rec_qids = sorted(set(r["question_id"] for r in records))
        require(
            set(rec_qids) == set(formal_ids),
            f"Question ID mismatch: {set(rec_qids) ^ set(formal_ids)}",
        )
        require(len(model_ids) == 2, f"Expected 2 models, got {len(model_ids)}")

        for model in model_ids:
            for qid in rec_qids:
                pref_cnt = sum(
                    1
                    for r in records
                    if r["model"] == model and r["question_id"] == qid and r["action"] == "prefix"
                )
                cont_cnt = sum(
                    1
                    for r in records
                    if r["model"] == model
                    and r["question_id"] == qid
                    and r["action"] == "continuation"
                )
                require(pref_cnt == 1, f"{model}/{qid}: {pref_cnt} prefix")
                require(cont_cnt == 1, f"{model}/{qid}: {cont_cnt} continuation")

        keys = [(r["model"], r["question_id"], r["action"]) for r in records]
        dupes = {k: keys.count(k) for k in keys if keys.count(k) > 1}
        require(not dupes, f"Duplicates: {dupes}")
        errors = [r for r in records if r.get("error")]
        require(not errors, f"API errors: {len(errors)}")
        require(len(records) == 240, f"Expected 240, got {len(records)}")
        require(all(r.get("stage") == "formal" for r in records), "Non-formal stage in records")
        require(set(model_ids) == EXPECTED_MODELS, f"Unexpected models: {model_ids}")
        print("Validation: 240 records, 2 models, all formal, no errors, no duplicates")
    else:
        formal_ids = sorted(set(r["question_id"] for r in records))
        print(f"Smoke: {len(records)} records, {len(formal_ids)} questions")

    return records, model_ids, formal_ids


# ---- Helpers ----
def get_prefix(records, qid, model):
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "prefix":
            return r
    return None


def get_continuation(records, qid, model):
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "continuation":
            return r
    return None


def prefix_correct(records, qid, model):
    p = get_prefix(records, qid, model)
    return p.get("correct", False) if p else False


def prefix_tokens(records, qid, model):
    p = get_prefix(records, qid, model)
    return p.get("total_tokens", 0) if p else 0


def continuation_tokens(records, qid, model):
    c = get_continuation(records, qid, model)
    return c.get("total_tokens", 0) if c else 0


def continuation_raw_correct(records, qid, model):
    """Raw continuation correctness (no fallback)."""
    c = get_continuation(records, qid, model)
    if c and c.get("parsed_answer"):
        return c.get("correct", False)
    return None  # unparsed


def continuation_has_answer(records, qid, model):
    c = get_continuation(records, qid, model)
    return bool(c and c.get("parsed_answer"))


def process_state(records, qid, model):
    p = get_prefix(records, qid, model)
    return p.get("process_state", "unknown") if p else "unknown"


def get_final_correct(records, qid, model):
    """Continuation with fallback."""
    c = get_continuation(records, qid, model)
    if c and c.get("parsed_answer"):
        return c.get("correct", False), c.get("parsed_answer", ""), "continue"
    p = get_prefix(records, qid, model)
    if p and p.get("parsed_answer"):
        return p.get("correct", False), p.get("parsed_answer", ""), "fallback_prefix"
    return False, "", "unresolved"


def compute_gain(records, qid, model):
    """+1 fixed, -1 broke, 0 unchanged."""
    pf = prefix_correct(records, qid, model)
    cf, _, _ = get_final_correct(records, qid, model)
    if not pf and cf:
        return 1
    if pf and not cf:
        return -1
    return 0


# ---- Ranking ----
def qid_tiebreak(qid):
    return hashlib.md5(qid.encode()).hexdigest()


def rank_questions(qids, records, model, ranking_key):
    """Return ordered list of qids."""
    manifest_ids, manifest_levels, _ = load_manifest()
    items = []
    for qid in qids:
        if ranking_key == "process":
            st = process_state(records, qid, model)
            score = {"visible_unfinished": 2, "empty_unfinished": 1, "complete": 0}.get(st, -1)
        elif ranking_key == "inverse":
            st = process_state(records, qid, model)
            score = {"complete": 2, "empty_unfinished": 1, "visible_unfinished": 0}.get(st, -1)
        elif ranking_key == "level":
            score = manifest_levels.get(qid, 3)
        else:
            score = 0
        items.append((score, qid_tiebreak(qid), qid))
    items.sort(key=lambda x: (-x[0], x[1]))
    return [x[2] for x in items]


def apply_policy_at_k(qids, records, model, k_star, ranking_key):
    """Rank, continue top K*, stop rest. Returns (corrects, tokens)."""
    ranked = rank_questions(qids, records, model, ranking_key)
    continue_set = set(ranked[:k_star])  # unique K* (OK here since qids are unique input)
    corrects, tokens = [], []
    for qid in qids:
        if qid in continue_set:
            cf, _, _ = get_final_correct(records, qid, model)
            tok = prefix_tokens(records, qid, model) + continuation_tokens(records, qid, model)
        else:
            cf = prefix_correct(records, qid, model)
            tok = prefix_tokens(records, qid, model)
        corrects.append(1 if cf else 0)
        tokens.append(tok)
    return corrects, tokens


def compute_random_expected(records, qids, model, k_star):
    """E[Acc_random] = pref_acc + (K*/N) * avg_gain"""
    n = len(qids)
    pref_acc = sum(1 for q in qids if prefix_correct(records, q, model)) / n
    sum_gain = 0
    for q in qids:
        pf = prefix_correct(records, q, model)
        cf_raw = continuation_raw_correct(records, q, model)
        if cf_raw is not None:
            gain = 1 if cf_raw and not pf else (-1 if not cf_raw and pf else 0)
        else:
            gain = 0
        sum_gain += gain
    avg_gain = sum_gain / n
    expected_acc = pref_acc + (k_star / n) * avg_gain
    pref_tok = sum(prefix_tokens(records, q, model) for q in qids) / n
    cont_tok = sum(continuation_tokens(records, q, model) for q in qids) / n
    expected_tok = pref_tok + (k_star / n) * cont_tok
    return expected_acc, expected_tok, pref_acc, avg_gain


def compute_oracle(records, qids, model, k_star):
    """Oracle: rank by realized gain, select top K*."""
    gains = [(compute_gain(records, q, model), qid_tiebreak(q), q) for q in qids]
    gains.sort(key=lambda x: (-x[0], x[1]))
    continue_set = set(x[2] for x in gains[:k_star])
    corrects, tokens = [], []
    for qid in qids:
        if qid in continue_set:
            cf, _, _ = get_final_correct(records, qid, model)
            tok = prefix_tokens(records, qid, model) + continuation_tokens(records, qid, model)
        else:
            cf = prefix_correct(records, qid, model)
            tok = prefix_tokens(records, qid, model)
        corrects.append(1 if cf else 0)
        tokens.append(tok)
    n_benefit = sum(1 for g, _, _ in gains if g == 1)
    return sum(corrects) / len(corrects), sum(tokens) / len(tokens), n_benefit


# ---- Bootstrap (direct evaluation, no set collapse) ----
def bootstrap_direct(records, qids, model, n_iter=N_BOOTSTRAP, seed=RANDOM_SEED):
    """
    Bootstrap with duplicate-aware evaluation.
    For each replicate: resample questions w/ replacement, evaluate each occurrence directly.
    """
    rng = random.Random(seed)
    n = len(qids)
    diffs = []
    po_accs, rnd_accs = [], []

    for _ in range(n_iter):
        idx = [rng.randint(0, n - 1) for _ in range(n)]

        # Count unfinished and total occurrences directly
        n_unfinished = 0
        for i in idx:
            qid = qids[i]
            if process_state(records, qid, model) != "complete":
                n_unfinished += 1

        k_star_boot = n_unfinished
        if n == 0:
            continue

        # Process-only: each duplicate occurrence evaluated independently
        po_correct = 0
        sum_gain = 0
        for i in idx:
            qid = qids[i]
            if process_state(records, qid, model) != "complete":  # unfinished → continue
                cf, _, _ = get_final_correct(records, qid, model)
            else:
                cf = prefix_correct(records, qid, model)
            po_correct += 1 if cf else 0

            # Random expectation: for each occurrence, compute gain
            pf = prefix_correct(records, qid, model)
            cf_raw = continuation_raw_correct(records, qid, model)
            if cf_raw is not None:
                gain = 1 if cf_raw and not pf else (-1 if not cf_raw and pf else 0)
            else:
                gain = 0
            sum_gain += gain

        po_acc = po_correct / n
        pref_acc_num = sum(1 for i in idx if prefix_correct(records, qids[i], model))
        pref_acc = pref_acc_num / n
        rand_acc = pref_acc + (k_star_boot / n) * (sum_gain / n)

        diffs.append(po_acc - rand_acc)
        po_accs.append(po_acc)
        rnd_accs.append(rand_acc)

    diffs.sort()
    lo = diffs[int(n_iter * ALPHA / 2)]
    hi = diffs[int(n_iter * (1 - ALPHA / 2))]
    tail = sum(1 for d in diffs if d <= 0) / n_iter

    return {
        "process_mean": sum(po_accs) / n_iter,
        "random_mean": sum(rnd_accs) / n_iter,
        "delta_mean": sum(diffs) / n_iter,
        "ci_lower": lo,
        "ci_upper": hi,
        "tail_prob": tail,
        "significant": lo > 0,  # CI excludes zero
    }


def bootstrap_pooled(records, qids, models, n_iter=N_BOOTSTRAP, seed=RANDOM_SEED + 1):
    """Resample question clusters and retain every model observation for each draw."""
    rng = random.Random(seed)
    n = len(qids)
    require(n > 0, "Cannot bootstrap an empty question set")
    require(models, "Cannot bootstrap an empty model set")
    diffs = []

    for _ in range(n_iter):
        sampled = [qids[rng.randrange(n)] for _ in range(n)]
        model_diffs = []
        for model in models:
            k_star = sum(process_state(records, qid, model) != "complete" for qid in sampled)
            process_correct = 0
            prefix_correct_count = 0
            gain_sum = 0
            for qid in sampled:
                pf = prefix_correct(records, qid, model)
                prefix_correct_count += int(pf)
                if process_state(records, qid, model) != "complete":
                    final_correct, _, _ = get_final_correct(records, qid, model)
                else:
                    final_correct = pf
                process_correct += int(final_correct)

                raw_cont = continuation_raw_correct(records, qid, model)
                if raw_cont is not None:
                    gain_sum += int(raw_cont and not pf) - int(pf and not raw_cont)

            process_accuracy = process_correct / n
            random_accuracy = prefix_correct_count / n + (k_star / n) * (gain_sum / n)
            model_diffs.append(process_accuracy - random_accuracy)
        diffs.append(sum(model_diffs) / len(model_diffs))

    diffs.sort()
    lo = diffs[int(n_iter * ALPHA / 2)]
    hi = diffs[int(n_iter * (1 - ALPHA / 2))]
    return {
        "delta_mean": sum(diffs) / n_iter,
        "ci_lower": lo,
        "ci_upper": hi,
        "tail_prob": sum(diff <= 0 for diff in diffs) / n_iter,
        "significant": lo > 0,
        "cluster_unit": "question_id",
        "models_per_cluster": len(models),
    }


def continuation_outcomes_by_state(records, qids, model):
    """Describe the complete action bank, including continuation on complete prefixes."""
    breakdown = {}
    for qid in qids:
        state = process_state(records, qid, model)
        bucket = breakdown.setdefault(
            state, {"benefit": 0, "harm": 0, "unchanged": 0, "unresolved": 0}
        )
        if not continuation_has_answer(records, qid, model):
            bucket["unresolved"] += 1
            continue
        gain = compute_gain(records, qid, model)
        bucket["benefit" if gain == 1 else ("harm" if gain == -1 else "unchanged")] += 1
    return breakdown


def save_accuracy_cost_figure(results_by_model, stage):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    policy_order = [
        "fixed_low",
        "fixed_continue",
        "random_expected",
        "question_only",
        "process_only_inverse",
        "process_only",
        "oracle",
    ]
    figure, axes = plt.subplots(1, len(results_by_model), figsize=(7 * len(results_by_model), 5))
    if len(results_by_model) == 1:
        axes = [axes]
    for axis, (model, model_data) in zip(axes, results_by_model.items()):
        for policy in policy_order:
            point = model_data["policies"].get(policy)
            if not point:
                continue
            axis.scatter(point["mean_tok"], point["acc_pct"], s=55)
            axis.annotate(
                policy,
                (point["mean_tok"], point["acc_pct"]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
            )
        axis.set_title(model)
        axis.set_xlabel("Mean actual total tokens / question")
        axis.set_ylabel("Final accuracy (%)")
        axis.grid(alpha=0.25)
    figure.suptitle(f"Stage 2P accuracy-cost policies ({stage})")
    figure.tight_layout()
    suffix = "" if stage == "formal" else f"_{stage}"
    output = RESULTS_DIR / f"process_stage2p_figure{suffix}.png"
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="formal", choices=["formal", "gate0"])
    parser.add_argument("--model-filter", nargs="+")
    args = parser.parse_args()

    records, model_ids, formal_ids = load_data(args.stage)
    if args.model_filter:
        model_ids = [m for m in args.model_filter if m in model_ids]

    manifest_ids, manifest_levels, _ = load_manifest()
    results_by_model = {}
    raw_model_primary = {}

    for model in model_ids:
        qids = sorted(formal_ids)
        n = len(qids)
        n_visible = sum(1 for q in qids if process_state(records, q, model) == "visible_unfinished")
        n_empty = sum(1 for q in qids if process_state(records, q, model) == "empty_unfinished")
        n_complete = sum(1 for q in qids if process_state(records, q, model) == "complete")
        k_star = n_visible + n_empty

        print(f"\n{'=' * 60}")
        print(f"Model: {model}, N={n}, K*={k_star} (V={n_visible} E={n_empty} C={n_complete})")

        policies = {}

        # Fixed Low (K=0)
        corr, _ = apply_policy_at_k(qids, records, model, 0, "process")
        policies["fixed_low"] = {
            "accuracy": sum(corr) / n,
            "mean_tokens": sum(prefix_tokens(records, q, model) for q in qids) / n,
            "k_used": 0,
        }

        # Fixed Continue (K=n)
        corr, tok = apply_policy_at_k(qids, records, model, n, "process")
        policies["fixed_continue"] = {
            "accuracy": sum(corr) / n,
            "mean_tokens": sum(tok) / n,
            "k_used": n,
        }

        # Process-only
        corr, tok = apply_policy_at_k(qids, records, model, k_star, "process")
        po_acc, po_tok = sum(corr) / n, sum(tok) / n
        policies["process_only"] = {"accuracy": po_acc, "mean_tokens": po_tok, "k_used": k_star}

        # Inverse
        corr, tok = apply_policy_at_k(qids, records, model, k_star, "inverse")
        policies["process_only_inverse"] = {
            "accuracy": sum(corr) / n,
            "mean_tokens": sum(tok) / n,
            "k_used": k_star,
        }

        # Question-only
        corr, tok = apply_policy_at_k(qids, records, model, k_star, "level")
        policies["question_only"] = {
            "accuracy": sum(corr) / n,
            "mean_tokens": sum(tok) / n,
            "k_used": k_star,
        }

        # Random expected
        r_acc, r_tok, pref_acc_mean, avg_gain = compute_random_expected(
            records, qids, model, k_star
        )
        policies["random_expected"] = {"accuracy": r_acc, "mean_tokens": r_tok, "k_used": k_star}

        # Oracle
        o_acc, o_tok, n_benefit = compute_oracle(records, qids, model, k_star)
        policies["oracle"] = {"accuracy": o_acc, "mean_tokens": o_tok, "k_used": k_star}

        # Bootstrap (direct, duplicate-aware)
        boot = bootstrap_direct(records, qids, model)
        print(f"\n  Process-only: {po_acc * 100:.1f}% @ {po_tok:.0f} tok")
        print(f"  Random expected: {r_acc * 100:.1f}% @ {r_tok:.0f} tok")
        print(
            f"  Δ = {(po_acc - r_acc) * 100:.1f}% [{boot['ci_lower'] * 100:.1f}%, {boot['ci_upper'] * 100:.1f}%]"
        )
        print(f"  CI excludes zero: {boot['significant']}  tail: {boot['tail_prob']:.4f}")

        # Cost parity
        cost_ratio, cost_parity_pass, pareto_improving, cost_condition_pass = (
            evaluate_cost_condition(po_acc, r_acc, po_tok, r_tok)
        )
        overall_success = boot["significant"] and cost_condition_pass

        print(
            f"  Cost ratio: {cost_ratio:.3f} (parity: {cost_parity_pass}, pareto: {pareto_improving})"
        )
        print(f"  Overall success: {overall_success}")

        for pname, pd in sorted(policies.items()):
            print(
                f"  {pname:25s}: acc={pd['accuracy'] * 100:.1f}% tok={pd['mean_tokens']:.0f} K={pd['k_used']}"
            )

        # Outcome breakdown
        outcomes = Counter()
        for q in qids:
            st = process_state(records, q, model)
            if st == "complete":
                outcomes["complete_stop"] += 1
            else:
                c_has = continuation_has_answer(records, q, model)
                if c_has:
                    g = compute_gain(records, q, model)
                    outcomes["benefit" if g == 1 else ("harm" if g == -1 else "unchanged")] += 1
                else:
                    outcomes["unresolved_fallback"] += 1

        # Token breakdown
        tok_bd = {"prompt": 0, "completion": 0, "total": 0}
        for r in records:
            if r["model"] == model:
                tok_bd["prompt"] += r.get("prompt_tokens", 0)
                tok_bd["completion"] += r.get("completion_tokens", 0)
                tok_bd["total"] += r.get("total_tokens", 0)

        results_by_model[model] = {
            "n": n,
            "k_star": k_star,
            "states": {"complete": n_complete, "visible": n_visible, "empty": n_empty},
            "policies": {
                k: {
                    "acc_pct": round(v["accuracy"] * 100, 1),
                    "mean_tok": round(v["mean_tokens"], 1),
                    "k": v["k_used"],
                }
                for k, v in policies.items()
            },
            "primary": {
                "delta_pct": round((po_acc - r_acc) * 100, 1),
                "ci_lower_pct": round(boot["ci_lower"] * 100, 1),
                "ci_upper_pct": round(boot["ci_upper"] * 100, 1),
                "tail_prob": round(boot["tail_prob"], 4),
                "significant": boot["significant"],
                "cost_ratio": round(cost_ratio, 3),
                "cost_parity_pass": cost_parity_pass,
                "pareto_improving": pareto_improving,
                "cost_condition_pass": cost_condition_pass,
                "overall_success": overall_success,
                "pref_baseline_pct": round(pref_acc_mean * 100, 1),
            },
            "outcomes": dict(outcomes),
            "continuation_outcomes_by_prefix_state": continuation_outcomes_by_state(
                records, qids, model
            ),
            "token_breakdown": tok_bd,
            "oracle_benefit": n_benefit,
        }
        raw_model_primary[model] = {
            "delta": po_acc - r_acc,
            "process_accuracy": po_acc,
            "random_accuracy": r_acc,
            "process_tokens": po_tok,
            "random_tokens": r_tok,
        }

    # Study-level inference: resample question IDs and keep both models together.
    pooled = bootstrap_pooled(records, sorted(formal_ids), model_ids)
    model_deltas = {model: raw_model_primary[model]["delta"] for model in model_ids}
    direction_consistent = set(model_ids) == EXPECTED_MODELS and all(
        delta > 0 for delta in model_deltas.values()
    )
    pooled_process_tokens = sum(
        raw_model_primary[model]["process_tokens"] for model in model_ids
    ) / len(model_ids)
    pooled_random_tokens = sum(
        raw_model_primary[model]["random_tokens"] for model in model_ids
    ) / len(model_ids)
    pooled_process_accuracy = sum(
        raw_model_primary[model]["process_accuracy"] for model in model_ids
    ) / len(model_ids)
    pooled_random_accuracy = sum(
        raw_model_primary[model]["random_accuracy"] for model in model_ids
    ) / len(model_ids)
    pooled_cost_ratio, pooled_cost_parity, pooled_pareto, pooled_cost_condition = (
        evaluate_cost_condition(
            pooled_process_accuracy,
            pooled_random_accuracy,
            pooled_process_tokens,
            pooled_random_tokens,
        )
    )
    study_success = pooled["significant"] and direction_consistent and pooled_cost_condition
    study_result = {
        "primary_contrast": "process_only_minus_random_expected",
        "cluster_unit": pooled["cluster_unit"],
        "model_deltas_pct": {model: round(delta * 100, 1) for model, delta in model_deltas.items()},
        "direction_consistent_across_models": direction_consistent,
        "delta_pct": round((pooled_process_accuracy - pooled_random_accuracy) * 100, 1),
        "bootstrap_delta_mean_pct": round(pooled["delta_mean"] * 100, 1),
        "ci_lower_pct": round(pooled["ci_lower"] * 100, 1),
        "ci_upper_pct": round(pooled["ci_upper"] * 100, 1),
        "tail_prob": round(pooled["tail_prob"], 4),
        "significant": pooled["significant"],
        "process_mean_tokens": round(pooled_process_tokens, 1),
        "random_mean_tokens": round(pooled_random_tokens, 1),
        "cost_ratio": round(pooled_cost_ratio, 3),
        "cost_parity_pass": pooled_cost_parity,
        "pareto_improving": pooled_pareto,
        "cost_condition_pass": pooled_cost_condition,
        "study_success": study_success,
    }

    # Save
    out = RESULTS_DIR / f"process_stage2p_analysis_{args.stage}.json"
    with open(out, "w") as f:
        json.dump({**results_by_model, "_study": study_result}, f, indent=2)
    print(f"\nSaved to {out}")

    # Report
    lines = [
        f"# Stage 2P: Process-only formal interventional pilot ({args.stage})",
        f"N_BOOTSTRAP={N_BOOTSTRAP} alpha={ALPHA} cost_tol={COST_PARITY_TOLERANCE}",
        "significant = ci_lower > 0 (not tail_prob < 0.05)\n",
        "## Study-level primary result",
        (
            f"Pooled question-clustered Δ={study_result['delta_pct']}% "
            f"CI [{study_result['ci_lower_pct']}, {study_result['ci_upper_pct']}] "
            f"significant={study_result['significant']}"
        ),
        (
            f"Cross-model direction consistent={study_result['direction_consistent_across_models']}; "
            f"cost ratio={study_result['cost_ratio']}; "
            f"study success={study_result['study_success']}\n"
        ),
    ]
    for model in model_ids:
        md = results_by_model[model]
        lines.append(f"### {model}")
        lines.append(
            f"K* = {md['k_star']} ({md['states']}), prefix baseline = {md['primary']['pref_baseline_pct']}%"
        )
        lines.append("| Policy | Acc% | Mean tok | K |")
        lines.append("|---|---:|---:|---:|")
        for pn, pd in sorted(md["policies"].items()):
            lines.append(f"| {pn} | {pd['acc_pct']} | {pd['mean_tok']} | {pd['k']} |")
        pr = md["primary"]
        lines.append(
            f"\n**Primary: Δ={pr['delta_pct']}% CI [{pr['ci_lower_pct']},{pr['ci_upper_pct']}] tail={pr['tail_prob']} significant={pr['significant']}**"
        )
        lines.append(
            f"Cost ratio: {pr['cost_ratio']} parity={pr['cost_parity_pass']} pareto={pr['pareto_improving']}"
        )
        lines.append(f"Overall success: {pr['overall_success']}")
        lines.append(f"Outcomes: {md['outcomes']}")
        lines.append(
            "All continuation outcomes by prefix state: "
            f"{md['continuation_outcomes_by_prefix_state']}"
        )
        lines.append(f"Oracle max benefit: {md['oracle_benefit']}/{md['k_star']}")
        lines.append("")

    rpt = RESULTS_DIR / f"process_stage2p_report_{args.stage}.md"
    with open(rpt, "w") as f:
        f.write("\n".join(lines))
    print(f"Report: {rpt}")
    figure = save_accuracy_cost_figure(results_by_model, args.stage)
    print(f"Figure: {figure}")


if __name__ == "__main__":
    main()
