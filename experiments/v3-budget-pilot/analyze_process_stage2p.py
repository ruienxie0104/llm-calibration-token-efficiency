#!/usr/bin/env python3
"""Stage 2P analysis: apply policies, bootstrap, report."""

import sys, json, random, copy
from pathlib import Path
from collections import Counter

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PRIMARY_K_COMPLETE = "unfinished"  # K* = number of unfinished prefix cases
RANDOM_SEED = 20260917
N_BOOTSTRAP = 10000
ALPHA = 0.05

def load_data():
    p = RESULTS_DIR / "process_stage2p_raw.json"
    with open(p) as f:
        data = json.load(f)
    return data["records"]

def get_prefix_state(records, qid, model):
    """Get process state for a question-model pair from prefix action."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "prefix":
            return r.get("process_state", "unknown")
    return "unknown"

def get_prefix_correct(records, qid, model):
    """Get prefix correctness."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "prefix":
            return r.get("correct", False), r.get("parsed_answer", "")
    return False, ""

def get_continuation_correct(records, qid, model):
    """Get continuation correctness."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "continuation":
            return r.get("correct", False), r.get("parsed_answer", "")
    return False, ""

def get_continuation_tokens(records, qid, model):
    """Get continuation total tokens."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "continuation":
            return r.get("total_tokens", 0)
    return 0

def get_prefix_tokens(records, qid, model):
    """Get prefix total tokens."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "prefix":
            return r.get("total_tokens", 0)
    return 0

def continuation_has_answer(records, qid, model):
    """Check if continuation has a parseable answer."""
    for r in records:
        if r["question_id"] == qid and r["model"] == model and r["action"] == "continuation":
            return bool(r.get("parsed_answer", ""))
    return False

def apply_policy_fixed_low(records, questions, model):
    """Always stop at prefix."""
    results = []
    for q in questions:
        correct, parsed = get_prefix_correct(records, q["id"], model)
        prefix_tok = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": prefix_tok,
        })
    return results

def apply_policy_fixed_continue(records, questions, model):
    """Always continue."""
    results = []
    for q in questions:
        correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
        cont_tok = get_continuation_tokens(records, q["id"], model)
        if not parsed_c:
            # Fallback: keep prefix answer
            correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
            correct = correct_p
            parsed = parsed_p
        else:
            correct = correct_c
            parsed = parsed_c
        prefix_tok = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": prefix_tok + cont_tok,
        })
    return results

def apply_policy_random_matched(records, questions, model, k_star, seed=42):
    """Uniform random with exactly K* continuations."""
    rng = random.Random(seed)
    indices = list(range(len(questions)))
    rng.shuffle(indices)
    continue_indices = set(indices[:k_star])
    results = []
    for i, q in enumerate(questions):
        if i in continue_indices:
            correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
            cont_tok = get_continuation_tokens(records, q["id"], model)
            if not parsed_c:
                correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
                correct, parsed = correct_p, parsed_p
            else:
                correct, parsed = correct_c, parsed_c
            prefix_tok = get_prefix_tokens(records, q["id"], model)
            tot = prefix_tok + cont_tok
        else:
            correct, parsed = get_prefix_correct(records, q["id"], model)
            tot = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": tot,
        })
    return results

def apply_policy_question_only(records, questions, model):
    """Continue if question level >= 4. Frozen rule (no training needed)."""
    results = []
    for q in questions:
        if q.get("level", 0) >= 4:
            correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
            cont_tok = get_continuation_tokens(records, q["id"], model)
            if not parsed_c:
                correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
                correct, parsed = correct_p, parsed_p
            else:
                correct, parsed = correct_c, parsed_c
            prefix_tok = get_prefix_tokens(records, q["id"], model)
            tot = prefix_tok + cont_tok
        else:
            correct, parsed = get_prefix_correct(records, q["id"], model)
            tot = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": tot,
        })
    return results

def apply_policy_process_only(records, questions, model):
    """Process state rule: complete→stop, unfinished→continue."""
    results = []
    for q in questions:
        state = get_prefix_state(records, q["id"], model)
        if state == "complete":
            correct, parsed = get_prefix_correct(records, q["id"], model)
            tot = get_prefix_tokens(records, q["id"], model)
        else:  # visible_unfinished or empty_unfinished → continue
            correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
            cont_tok = get_continuation_tokens(records, q["id"], model)
            if not parsed_c:
                correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
                correct, parsed = correct_p, parsed_p
            else:
                correct, parsed = correct_c, parsed_c
            prefix_tok = get_prefix_tokens(records, q["id"], model)
            tot = prefix_tok + cont_tok
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": tot,
        })
    return results

def apply_policy_process_only_inverse(records, questions, model):
    """Reverse: complete→continue, unfinished→stop."""
    results = []
    for q in questions:
        state = get_prefix_state(records, q["id"], model)
        if state == "complete":
            correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
            cont_tok = get_continuation_tokens(records, q["id"], model)
            if not parsed_c:
                correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
                correct, parsed = correct_p, parsed_p
            else:
                correct, parsed = correct_c, parsed_c
            prefix_tok = get_prefix_tokens(records, q["id"], model)
            tot = prefix_tok + cont_tok
        else:
            correct, parsed = get_prefix_correct(records, q["id"], model)
            tot = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": tot,
        })
    return results

def apply_policy_oracle(records, questions, model, k_star, seed=42):
    """Oracle: continue on K* questions where prefix is INCORRECT (highest need)."""
    scored = []
    for q in questions:
        correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
        state = get_prefix_state(records, q["id"], model)
        # Score: incorrect → 1 (want to continue), correct → 0
        # Tie-breaking: unfinished > complete
        score = (0 if correct_p else 1, 1 if state != "complete" else 0)
        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)
    continue_qs = set(q["id"] for _, q in scored[:k_star])

    results = []
    for q in questions:
        if q["id"] in continue_qs:
            correct_c, parsed_c = get_continuation_correct(records, q["id"], model)
            cont_tok = get_continuation_tokens(records, q["id"], model)
            if not parsed_c:
                correct_p, parsed_p = get_prefix_correct(records, q["id"], model)
                correct, parsed = correct_p, parsed_p
            else:
                correct, parsed = correct_c, parsed_c
            prefix_tok = get_prefix_tokens(records, q["id"], model)
            tot = prefix_tok + cont_tok
        else:
            correct, parsed = get_prefix_correct(records, q["id"], model)
            tot = get_prefix_tokens(records, q["id"], model)
        results.append({
            "question_id": q["id"], "final_answer": parsed,
            "correct": correct, "total_tokens": tot,
        })
    return results

def compute_correctness(results):
    return [1 if r["correct"] else 0 for r in results]

def bootstrap_ci(accs_a, accs_b, n_iter=N_BOOTSTRAP, seed=RANDOM_SEED):
    """Bootstrap CI for difference of paired accuracies."""
    rng = random.Random(seed)
    n = len(accs_a)
    diffs = []
    for _ in range(n_iter):
        idx = [rng.randint(0, n - 1) for _ in range(n)]
        a = sum(accs_a[i] for i in idx) / n
        b = sum(accs_b[i] for i in idx) / n
        diffs.append(a - b)
    diffs.sort()
    lo = diffs[int(n_iter * ALPHA / 2)]
    hi = diffs[int(n_iter * (1 - ALPHA / 2))]
    p = sum(1 for d in diffs if d <= 0) / n_iter
    return lo, hi, p

def main():
    records = load_data()
    questions_raw = []
    # Extract unique questions
    seen = set()
    for r in records:
        qid = r["question_id"]
        if qid not in seen:
            seen.add(qid)
            # Load question metadata
            questions_raw.append({
                "id": qid,
                "level": 3 if "113" in qid or "623" in qid or "91" in qid else 4,  # fallback
                "problem": "",
                "answer": "",
            })

    models = sorted(set(r["model"] for r in records))
    print(f"Loaded {len(records)} records, {len(questions_raw)} questions")
    print(f"Models: {models}")

    # Load question manifest for levels
    manifest_path = Path(__file__).resolve().parent / "data" / "process_stage2_questions.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        m_qs = {}
        for split in manifest.get("splits", {}).values():
            for q in split:
                m_qs[q["id"]] = q
        for q in questions_raw:
            if q["id"] in m_qs:
                q["level"] = m_qs[q["id"]]["level"]
                q["problem"] = m_qs[q["id"]].get("problem", "")
                q["answer"] = m_qs[q["id"]].get("answer", "")

    all_policies = {
        "fixed_low": apply_policy_fixed_low,
        "fixed_continue": apply_policy_fixed_continue,
        "random_matched": apply_policy_random_matched,
        "question_only": apply_policy_question_only,
        "process_only": apply_policy_process_only,
        "process_only_inverse": apply_policy_process_only_inverse,
        "oracle": apply_policy_oracle,
    }

    results_by_model = {}

    for model in models:
        model_qs = [q for q in questions_raw]
        incomplete = len(model_qs)

        # Compute K* = number of unfinished prefix cases
        unfinished = 0
        for q in model_qs:
            state = get_prefix_state(records, q["id"], model)
            if state != "complete":
                unfinished += 1
        k_star = unfinished

        print(f"\n{'='*60}")
        print(f"Model: {model}")
        print(f"Questions: {len(model_qs)}, K* = {k_star}")

        # State distribution
        states = Counter()
        for q in model_qs:
            states[get_prefix_state(records, q["id"], model)] += 1
        print(f"State distribution: {dict(states)}")

        policy_results = {}
        for pname, pfunc in all_policies.items():
            if pname in ("random_matched", "oracle"):
                results = pfunc(records, model_qs, model, k_star)
            else:
                results = pfunc(records, model_qs, model)

            acc = sum(1 for r in results if r["correct"]) / len(results) * 100
            mean_tok = sum(r["total_tokens"] for r in results) / len(results)
            policy_results[pname] = {
                "accuracy": round(acc, 1),
                "mean_total_tokens": round(mean_tok, 1),
                "n_correct": sum(1 for r in results if r["correct"]),
                "n_total": len(results),
            }
            print(f"  {pname:25s}: acc={acc:.1f}%  mean_tok={mean_tok:.0f}")

        # Bootstrap: process-only vs random matched
        po = apply_policy_process_only(records, model_qs, model)
        rm = apply_policy_random_matched(records, model_qs, model, k_star)
        acc_po = [1 if r["correct"] else 0 for r in po]
        acc_rm = [1 if r["correct"] else 0 for r in rm]
        lo, hi, p = bootstrap_ci(acc_po, acc_rm)
        print(f"\n  Primary: Process-only vs Random matched")
        print(f"    ΔAccuracy = {policy_results['process_only']['accuracy'] - policy_results['random_matched']['accuracy']:.1f}%")
        print(f"    95% CI [{lo*100:.1f}%, {hi*100:.1f}%], p={p:.4f}")

        results_by_model[model] = {
            "k_star": k_star,
            "prefix_state_distribution": dict(states),
            "policies": policy_results,
            "primary_comparison": {
                "delta_accuracy_pct": round((policy_results["process_only"]["accuracy"] - policy_results["random_matched"]["accuracy"]), 1),
                "ci_lower_pct": round(lo * 100, 1),
                "ci_upper_pct": round(hi * 100, 1),
                "p_value": round(p, 4),
                "significant": p < 0.05,
            },
        }

    # Save analysis
    out = RESULTS_DIR / "process_stage2p_analysis.json"
    with open(out, "w") as f:
        json.dump(results_by_model, f, indent=2)
    print(f"\nSaved analysis to {out}")

    # Generate report
    report_lines = [
        "# Stage 2P: Process-only formal interventional pilot report",
        f"\n> Generated from `{__file__}`",
        f"> Bootstrap: {N_BOOTSTRAP} replicates, question-clustered, {int(ALPHA*100)}% alpha",
        "",
        "## Policy comparison (per model)",
        "",
        "| Model | Policy | Accuracy | Mean total tokens | N correct | N total |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for model in models:
        for pname, pdata in results_by_model[model]["policies"].items():
            report_lines.append(
                f"| {model[:20]} | {pname:25s} | {pdata['accuracy']:.1f}% | {pdata['mean_total_tokens']:.0f} | "
                f"{pdata['n_correct']} | {pdata['n_total']} |"
            )
        report_lines.append("")

    report_lines.extend([
        "## Primary comparison: Process-only vs Random matched",
        "",
        "| Model | K* | ΔAccuracy | 95% CI lower | 95% CI upper | p-value | Significant |",
        "|---|---:|---:|---:|---:|---:|",
    ])

    for model in models:
        pc = results_by_model[model]["primary_comparison"]
        report_lines.append(
            f"| {model[:20]} | {results_by_model[model]['k_star']} | {pc['delta_accuracy_pct']:.1f}% | "
            f"{pc['ci_lower_pct']:.1f}% | {pc['ci_upper_pct']:.1f}% | {pc['p_value']:.4f} | {pc['significant']} |"
        )

    report_lines.extend([
        "",
        "## State distribution per model",
        "",
        "| Model | complete | visible_unfinished | empty_unfinished | K* |",
        "|---|---:|---:|---:|---:|",
    ])

    for model in models:
        sd = results_by_model[model]["prefix_state_distribution"]
        report_lines.append(
            f"| {model[:20]} | {sd.get('complete', 0)} | {sd.get('visible_unfinished', 0)} | "
            f"{sd.get('empty_unfinished', 0)} | {results_by_model[model]['k_star']} |"
        )

    report_text = "\n".join(report_lines)
    report_path = RESULTS_DIR / "process_stage2p_report.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"Saved report to {report_path}")

if __name__ == "__main__":
    main()