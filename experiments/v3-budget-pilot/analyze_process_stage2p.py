#!/usr/bin/env python3
"""Stage 2P analysis: apply policies (matched-K* ranking), bootstrap expectation, report."""

import sys, json, random, copy, hashlib
from pathlib import Path
from collections import Counter

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RANDOM_SEED = 20260917
N_BOOTSTRAP = 10000
ALPHA = 0.05
EXPECTED_FORMAL_IDS = []  # populated from manifest

def load_manifest():
    """Load the formal 60 question IDs from manifest."""
    mpath = Path(__file__).resolve().parent / "data" / "process_stage2_questions.json"
    with open(mpath) as f:
        data = json.load(f)
    formal = data["splits"]["formal"]
    ids = sorted(q["id"] for q in formal)
    levels = {q["id"]: q.get("level", 3) for q in formal}
    answers = {q["id"]: q.get("answer", "") for q in formal}
    return ids, levels, {q["id"]: q for q in formal}

def load_data(stage="formal"):
    """Load raw data and validate."""
    fname = "process_stage2p_smoke.json" if stage == "gate0" else "process_stage2p_raw.json"
    p = RESULTS_DIR / fname
    with open(p) as f:
        data = json.load(f)
    records = data["records"]

    formal_ids, _, _ = load_manifest()
    model_ids = sorted(set(r["model"] for r in records))

    if stage == "formal":
        # Validation assertions
        rec_qids = sorted(set(r["question_id"] for r in records))
        assert set(rec_qids) == set(formal_ids), \
            f"Question ID mismatch: {set(rec_qids) ^ set(formal_ids)}"
        assert len(model_ids) == 2, f"Expected 2 models, got {len(model_ids)}: {model_ids}"

        # Check each model-question has exactly one prefix and one continuation
        for model in model_ids:
            for qid in rec_qids:
                prefix_count = sum(1 for r in records
                                   if r["model"] == model and r["question_id"] == qid
                                   and r["action"] == "prefix")
                cont_count = sum(1 for r in records
                                 if r["model"] == model and r["question_id"] == qid
                                 and r["action"] == "continuation")
                assert prefix_count == 1, f"{model}/{qid}: {prefix_count} prefix records ({cont_count} cont)"
                assert cont_count == 1, f"{model}/{qid}: {cont_count} continuation records"

        # Check for duplicate keys
        keys = [(r["model"], r["question_id"], r["action"]) for r in records]
        dupes = {k: keys.count(k) for k in keys if keys.count(k) > 1}
        assert not dupes, f"Duplicate keys found: {dupes}"

        # Check for API errors
        errors = [r for r in records if r.get("error")]
        assert not errors, f"API errors found: {len(errors)}"

        # Check all IDs are from formal split
        for r in records:
            assert r["question_id"] in formal_ids, \
                f"Question {r['question_id']} not in formal split"

        total = len(records)
        assert total == 240, f"Expected 240 records, got {total}"

        print(f"Validation passed: {total} records, {len(model_ids)} models, "
              f"{len(model_ids) * len(rec_qids)} model-question pairs")
    else:
        # Smoke: use whatever question IDs exist in records
        formal_ids = sorted(set(r["question_id"] for r in records))
        print(f"Smoke mode: {len(records)} records, {len(formal_ids)} questions")

    return records, model_ids, formal_ids

def get_prefix(records, qid, model):
    """Get prefix record for a question-model pair."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "prefix":
            return r
    return None

def get_continuation(records, qid, model):
    """Get continuation record for a question-model pair."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "continuation":
            return r
    return None

def get_final_correct(records, qid, model):
    """Get continuation result with fallback.
    If continuation has parseable answer → use it.
    Otherwise keep prefix answer. If no prefix answer either → unresolved (incorrect)."""
    pref = get_prefix(records, qid, model)
    cont = get_continuation(records, qid, model)

    if cont and cont.get("parsed_answer"):
        return cont.get("correct", False), cont.get("parsed_answer", ""), "continue"
    elif pref and pref.get("parsed_answer"):
        return pref.get("correct", False), pref.get("parsed_answer", ""), "fallback_prefix"
    else:
        return False, "", "unresolved"

def get_process_state(records, qid, model):
    """Get prefix process state."""
    pref = get_prefix(records, qid, model)
    return pref.get("process_state", "unknown") if pref else "unknown"

def get_prefix_correct(records, qid, model):
    """Get prefix correctness and answer."""
    pref = get_prefix(records, qid, model)
    if pref:
        return pref.get("correct", False), pref.get("parsed_answer", "")
    return False, ""

def get_prefix_tokens(records, qid, model):
    """Get prefix total tokens."""
    pref = get_prefix(records, qid, model)
    if pref:
        return pref.get("total_tokens", 0)
    return 0

def get_continuation_tokens(records, qid, model):
    """Get continuation total tokens."""
    cont = get_continuation(records, qid, model)
    if cont:
        return cont.get("total_tokens", 0)
    return 0

def get_continuation_correct(records, qid, model):
    """Get continuation raw correctness (without fallback)."""
    cont = get_continuation(records, qid, model)
    if cont:
        return cont.get("correct", False), cont.get("parsed_answer", "")
    return False, ""

def compute_continuation_gain(records, qid, model):
    """Compute gain from continuation: +1 if fixed wrong, -1 if broke correct, 0 otherwise."""
    pref = get_prefix(records, qid, model)
    cont = get_continuation(records, qid, model)
    if not pref or not cont:
        return 0

    pref_correct = pref.get("correct", False)
    cont_correct, cont_parsed, _src = get_final_correct(records, qid, model)

    if not pref_correct and cont_correct:
        return 1  # fixed
    elif pref_correct and not cont_correct:
        return -1  # broke
    else:
        return 0  # unchanged

POLICY_DEFINITIONS = {
    "fixed_low": "Always stop at prefix (0 continuations)",
    "fixed_continue": "Always continue (all questions)",
    "process_only": f"complete→stop, unfinished→continue (K* = n_unfinished)",
    "process_only_inverse": f"complete→continue, unfinished→stop (reverse direction, matched K*)",
    "question_only": "Level 4→continue, Level 3→stop (frozen rule, matched K*)",
    "random_expected": "Uniform random expectation at K* (analytical formula)",
    "oracle": "Rank by realized gain, select top K* (matched K*)",
}

def rank_questions(qids, records, model, ranking_key):
    """
    Rank questions by a priority key, return ordered list.
    ranking_key: 'process' (visible>empty>complete),
                 'inverse' (complete>empty>visible),
                 'level' (Level4>Level3)
    """
    states = []
    qlevels = {}
    manifest_ids, manifest_levels, manifest_qs = load_manifest()

    def tie_break(qid):
        """Deterministic tie-break by question ID hash."""
        return hashlib.md5(qid.encode()).hexdigest()

    for qid in qids:
        state = get_process_state(records, qid, model) if ranking_key in ("process", "inverse") else None
        level = manifest_levels.get(qid, 3)

        if ranking_key == "process":
            # visible (2) > empty (1) > complete (0)
            state_score = {"visible_unfinished": 2, "empty_unfinished": 1, "complete": 0}.get(state, -1)
            score = (state_score, tie_break(qid))
        elif ranking_key == "inverse":
            # complete (2) > empty (1) > visible (0)
            state_score = {"complete": 2, "empty_unfinished": 1, "visible_unfinished": 0}.get(state, -1)
            score = (state_score, tie_break(qid))
        elif ranking_key == "level":
            score = (level if level else 3, tie_break(qid))
        else:
            score = (0, tie_break(qid))

        states.append((score, qid, state, level))

    states.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in states]

def apply_policy_at_k(qids, records, model, k_star, ranking_key):
    """
    Generic policy: rank questions by ranking_key, continue top K*, stop rest.
    Returns list of correctness booleans and total_tokens for each question.
    """
    ranked = rank_questions(qids, records, model, ranking_key)
    continue_set = set(ranked[:k_star])
    corrects = []
    tokens = []

    for qid in qids:
        if qid in continue_set:
            correct, _, _ = get_final_correct(records, qid, model)
            tok = get_prefix_tokens(records, qid, model) + get_continuation_tokens(records, qid, model)
        else:
            correct, _ = get_prefix_correct(records, qid, model)
            tok = get_prefix_tokens(records, qid, model)
        corrects.append(1 if correct else 0)
        tokens.append(tok)

    return corrects, tokens, len(continue_set)

def compute_random_expected(records, qids, model, k_star):
    """
    Compute expected accuracy of uniform random matched-allocation:
    E[Acc_random] = Acc_prefix + (K*/N) * (1/N) * sum(Gain_i)
    where Gain_i = continuation_correct - prefix_correct
    """
    n = len(qids)
    sum_gain = 0
    for qid in qids:
        pf_correct, _ = get_prefix_correct(records, qid, model)
        cont_correct, cont_parsed = get_continuation_correct(records, qid, model)
        if cont_parsed:
            gain = 1 if cont_correct and not pf_correct else (-1 if not cont_correct and pf_correct else 0)
        else:
            gain = 0  # continuation unparsed → fallback to prefix, no gain
        sum_gain += gain

    # Expected: prefix accuracy + (K*/N) * avg_gain
    pref_acc = sum(1 for q in qids if get_prefix_correct(records, q, model)[0]) / n
    avg_gain = sum_gain / n
    expected_acc = pref_acc + (k_star / n) * avg_gain

    # Expected tokens: prefix + (K*/N) * continuation marginal
    prefix_tok_sum = sum(get_prefix_tokens(records, q, model) for q in qids) / n
    cont_tok_sum = sum(get_continuation_tokens(records, q, model) for q in qids) / n
    expected_tok = prefix_tok_sum + (k_star / n) * cont_tok_sum

    return expected_acc, expected_tok, pref_acc, avg_gain

def compute_oracle_gain(records, qids, model, k_star):
    """Oracle: rank by realized continuation gain, select top K*."""
    gains = []
    for qid in qids:
        g = compute_continuation_gain(records, qid, model)
        gains.append((g, qid))

    # Sort by gain descending, tie-break by question ID hash
    gains.sort(key=lambda x: (-x[0], hashlib.md5(x[1].encode()).hexdigest()))
    continue_set = set(qid for _, qid in gains[:k_star])

    corrects = []
    tokens = []
    for qid in qids:
        if qid in continue_set:
            correct, _, _ = get_final_correct(records, qid, model)
            tok = get_prefix_tokens(records, qid, model) + get_continuation_tokens(records, qid, model)
            corrects.append(1 if correct else 0)
        else:
            correct, _ = get_prefix_correct(records, qid, model)
            tok = get_prefix_tokens(records, qid, model)
            corrects.append(1 if correct else 0)
        tokens.append(tok)

    # Also compute what we could achieve if we had budget = oracle_optimal
    # i.e., continue only on gain=1 cases
    n_benefit = sum(1 for g, _ in gains if g == 1)
    max_possible = n_benefit / len(qids) + pref_acc_quick(records, qids, model)

    acc = sum(corrects) / len(corrects)
    return acc, sum(tokens) / len(tokens), n_benefit

def pref_acc_quick(records, qids, model):
    return sum(1 for q in qids if get_prefix_correct(records, q, model)[0]) / len(qids)

def bootstrap_process_vs_random(records, qids, model, k_star, n_iter=N_BOOTSTRAP, seed=RANDOM_SEED):
    """Bootstrap Process-only vs Random expected at K*. Resamples questions."""
    rng = random.Random(seed)
    n = len(qids)
    po_diffs = []
    pref_accs = []
    random_accs = []
    process_accs = []

    for _ in range(n_iter):
        # Resample questions with replacement
        idx = [rng.randint(0, n - 1) for _ in range(n)]
        sampled_qids = [qids[i] for i in idx]

        # Compute K* for this replicate (same logic as overall)
        n_unfinished = sum(1 for q in sampled_qids
                           if get_process_state(records, q, model) != "complete")
        k_star_boot = n_unfinished

        # Process-only accuracy
        po_corrects, po_toks, po_n = apply_policy_at_k(sampled_qids, records, model, k_star_boot, "process")
        po_acc = sum(po_corrects) / n

        # Random expected accuracy (analytical)
        pref_acc = sum(1 for q in sampled_qids if get_prefix_correct(records, q, model)[0]) / n
        sum_gain = 0
        for q in sampled_qids:
            pf_c, _ = get_prefix_correct(records, q, model)
            cont_c, cont_p = get_continuation_correct(records, q, model)
            if cont_p:
                gain = 1 if cont_c and not pf_c else (-1 if not cont_c and pf_c else 0)
            else:
                gain = 0
            sum_gain += gain
        avg_gain = sum_gain / n
        random_acc = pref_acc + (k_star_boot / n) * avg_gain

        po_diffs.append(po_acc - random_acc)
        pref_accs.append(pref_acc)
        random_accs.append(random_acc)
        process_accs.append(po_acc)

    # CI from bootstrap distribution
    po_diffs.sort()
    lo = po_diffs[int(n_iter * ALPHA / 2)]
    hi = po_diffs[int(n_iter * (1 - ALPHA / 2))]
    p = sum(1 for d in po_diffs if d <= 0) / n_iter

    return {
        "process_mean": sum(process_accs) / n_iter,
        "random_mean": sum(random_accs) / n_iter,
        "delta_mean": sum(po_diffs) / n_iter,
        "ci_lower": lo, "ci_upper": hi, "p_value": p,
        "significant": p < 0.05,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="formal", choices=["formal", "gate0"])
    parser.add_argument("--model-filter", nargs="+", help="Filter to specific models")
    args = parser.parse_args()

    records, model_ids, formal_ids = load_data(args.stage)
    if args.model_filter:
        model_ids = [m for m in args.model_filter if m in model_ids]
    # Get question metadata
    _, manifest_levels, manifest_qs = load_manifest()

    results_by_model = {}
    all_report_sections = []

    for model in model_ids:
        qids = sorted(formal_ids)
        n = len(qids)

        # Compute K*: number of unfinished prefix cases
        n_visible = sum(1 for q in qids if get_process_state(records, q, model) == "visible_unfinished")
        n_empty = sum(1 for q in qids if get_process_state(records, q, model) == "empty_unfinished")
        n_complete = sum(1 for q in qids if get_process_state(records, q, model) == "complete")
        k_star = n_visible + n_empty

        print(f"\n{'='*60}")
        print(f"Model: {model}")
        print(f"Questions: {n}, complete={n_complete}, visible={n_visible}, empty={n_empty}, K*={k_star}")

        # Apply all policies (matched K* for ranking-based policies)
        policies = {}

        # Fixed Low (K=0)
        pol_corrects, _, _ = apply_policy_at_k(qids, records, model, 0, "process")
        acc = sum(pol_corrects) / n
        tok = sum(get_prefix_tokens(records, q, model) for q in qids) / n
        policies["fixed_low"] = {"accuracy": acc, "mean_tokens": tok, "k_used": 0}

        # Fixed Continue (K=n)
        pol_corrects, _, _ = apply_policy_at_k(qids, records, model, n, "process")
        acc = sum(pol_corrects) / n
        tok = sum(get_prefix_tokens(records, q, model) + get_continuation_tokens(records, q, model) for q in qids) / n
        policies["fixed_continue"] = {"accuracy": acc, "mean_tokens": tok, "k_used": n}

        # Process-only (ranking=process, K=K*)
        po_corrects, po_toks, _ = apply_policy_at_k(qids, records, model, k_star, "process")
        po_acc = sum(po_corrects) / n
        po_tok = sum(po_toks) / n
        policies["process_only"] = {"accuracy": po_acc, "mean_tokens": po_tok, "k_used": k_star}

        # Process-only inverse (ranking=inverse, K=K*)
        inv_corrects, inv_toks, _ = apply_policy_at_k(qids, records, model, k_star, "inverse")
        inv_acc = sum(inv_corrects) / n
        inv_tok = sum(inv_toks) / n
        policies["process_only_inverse"] = {"accuracy": inv_acc, "mean_tokens": inv_tok, "k_used": k_star}

        # Question-only (ranking=level, K=K*)
        qo_corrects, qo_toks, _ = apply_policy_at_k(qids, records, model, k_star, "level")
        qo_acc = sum(qo_corrects) / n
        qo_tok = sum(qo_toks) / n
        policies["question_only"] = {"accuracy": qo_acc, "mean_tokens": qo_tok, "k_used": k_star}

        # Random expected (analytical formula)
        r_exp, r_tok, pref_acc_mean, avg_gain = compute_random_expected(records, qids, model, k_star)
        policies["random_expected"] = {"accuracy": r_exp, "mean_tokens": r_tok, "k_used": k_star}

        # Oracle (ranking by realized gain, K=K*)
        o_acc, o_tok, n_benefit = compute_oracle_gain(records, qids, model, k_star)
        policies["oracle"] = {"accuracy": o_acc, "mean_tokens": o_tok, "k_used": k_star}

        # Bootstrap primary comparison
        boot = bootstrap_process_vs_random(records, qids, model, k_star)

        print(f"  Primary: Process-only vs Random expected")
        print(f"    Process-only acc = {po_acc*100:.1f}%, tok = {po_tok:.0f}")
        print(f"    Random expected acc = {r_exp*100:.1f}%, tok = {r_tok:.0f}")
        print(f"    Pref baseline = {pref_acc_mean*100:.1f}%")
        print(f"    Avg gain per continuation = {avg_gain*100:.1f}%")
        print(f"    Δ = {(po_acc - r_exp)*100:.1f}%")
        print(f"    95% CI [{boot['ci_lower']*100:.1f}%, {boot['ci_upper']*100:.1f}%]")
        print(f"    p = {boot['p_value']:.4f}, significant = {boot['significant']}")

        for pname, pdata in sorted(policies.items()):
            print(f"  {pname:25s}: acc={pdata['accuracy']*100:.1f}% tok={pdata['mean_tokens']:.0f} K={pdata['k_used']}")

        # Token breakdown
        breakdown = {"prompt": 0, "completion": 0, "total": 0}
        for r in records:
            if r["model"] == model:
                breakdown["prompt"] += r.get("prompt_tokens", 0)
                breakdown["completion"] += r.get("completion_tokens", 0)
                breakdown["total"] += r.get("total_tokens", 0)

        # Benefit/Harm/Unchanged/Unresolved
        outcomes = Counter()
        for q in qids:
            correct_final, _, suffix = get_final_correct(records, q, model)
            pref_correct, _ = get_prefix_correct(records, q, model)
            prefix_state = get_process_state(records, q, model)
            if prefix_state == "complete":
                outcomes[f"complete_stop"] += 1
            else:
                cont = get_continuation(records, q, model)
                if cont and cont.get("parsed_answer"):
                    gain = compute_continuation_gain(records, q, model)
                    if gain == 1:
                        outcomes["benefit"] += 1
                    elif gain == -1:
                        outcomes["harm"] += 1
                    else:
                        outcomes["unchanged"] += 1
                else:
                    # continuation unparsed, fallback
                    if pref_correct:
                        outcomes["unchanged_fallback"] += 1
                    else:
                        outcomes["unresolved"] += 1

        results_by_model[model] = {
            "n_questions": n,
            "k_star": k_star,
            "prefix_state_distribution": {"complete": n_complete, "visible_unfinished": n_visible, "empty_unfinished": n_empty},
            "policies": {k: {"accuracy_pct": round(v["accuracy"]*100, 1), "mean_total_tokens": round(v["mean_tokens"], 1), "k_used": v["k_used"]} for k, v in policies.items()},
            "primary_comparison": {
                "delta_accuracy_pct": round((po_acc - r_exp)*100, 1),
                "ci_lower_pct": round(boot["ci_lower"]*100, 1),
                "ci_upper_pct": round(boot["ci_upper"]*100, 1),
                "p_value": round(boot["p_value"], 4),
                "significant": boot["significant"],
                "process_only_accuracy_pct": round(po_acc*100, 1),
                "random_expected_accuracy_pct": round(r_exp*100, 1),
                "pref_baseline_pct": round(pref_acc_mean*100, 1),
            },
            "outcomes": dict(outcomes),
            "token_breakdown": breakdown,
            "n_benefit": n_benefit,
        }

    # Save analysis
    out = RESULTS_DIR / (f"process_stage2p_analysis_{args.stage}.json")
    with open(out, "w") as f:
        json.dump(results_by_model, f, indent=2)
    print(f"\nSaved analysis to {out}")

    # Generate report
    lines = [
        f"# Stage 2P: Process-only formal interventional pilot",
        f"\n> Stage: {args.stage}",
        f"> Generated from `{__file__}`",
        f"> Bootstrap: {N_BOOTSTRAP} replicates, question-clustered, {int(ALPHA*100)}% alpha",
        f"> Random baseline: analytical expectation at matched K* (not single draw)",
        "",
        "## Policy comparison (per model)",
        "",
    ]

    for model in model_ids:
        md = results_by_model[model]
        lines.append(f"### {model.split('-')[0]}")
        lines.append(f"- K* = {md['k_star']} ({md['prefix_state_distribution']['visible_unfinished']} visible + {md['prefix_state_distribution']['empty_unfinished']} empty)")
        lines.append(f"- Prefix baseline: {md['primary_comparison']['pref_baseline_pct']:.1f}%")
        lines.append("")
        lines.append("| Policy | Accuracy | Mean total tokens | K used |")
        lines.append("|--------|------:|------:|------:|")
        for pname, pdata in sorted(md["policies"].items()):
            lines.append(f"| {pname:25s} | {pdata['accuracy_pct']:.1f}% | {pdata['mean_total_tokens']:.0f} | {pdata['k_used']} |")
        lines.append("")

        pc = md["primary_comparison"]
        lines.append("**Primary comparison: Process-only vs Random expected**")
        lines.append(f"- ΔAccuracy = {pc['delta_accuracy_pct']:.1f}%")
        lines.append(f"- 95% CI [{pc['ci_lower_pct']:.1f}%, {pc['ci_upper_pct']:.1f}%]")
        lines.append(f"- p = {pc['p_value']:.4f}")
        lines.append(f"- Significant: {pc['significant']}")
        lines.append("")

        lines.append("**Outcome breakdown (for unfinished cases)**")
        lines.append(f"- Benefit (prefix wrong → continuation right): {md['outcomes'].get('benefit', 0)}")
        lines.append(f"- Harm (prefix right → continuation wrong): {md['outcomes'].get('harm', 0)}")
        lines.append(f"- Unchanged: {md['outcomes'].get('unchanged', 0)}")
        lines.append(f"- Unresolved (continuation unparsed, no fallback): {md['outcomes'].get('unresolved', 0)}")
        lines.append(f"- Oracle max benefit (continue-only-on-gain=1): {md['n_benefit']}")
        lines.append("")

    report_text = "\n".join(lines)
    report_path = RESULTS_DIR / f"process_stage2p_report_{args.stage}.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"Saved report to {report_path}")

if __name__ == "__main__":
    main()