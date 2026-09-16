#!/usr/bin/env python3
"""
Prospective vs Retrospective Confidence — Full Analysis.
Compares Brier, ECE, AUROC, LCAE, confidence gap, and token correlation.
"""
import json, math, re, sys
from collections import defaultdict
sys.path.insert(0, 'experiments/v3-budget-pilot')
from answer_utils import is_correct

# Load data
with open('experiments/v3-budget-pilot/results/prospective_conf_full.json') as f:
    pros_raw = json.load(f)
with open('experiments/v3-budget-pilot/results/soft_pilot_raw.json') as f:
    soft = json.load(f)
with open('experiments/v3-budget-pilot/results/irt_phase3.json') as f:
    irt = json.load(f)

theta = irt['theta']
beta = {k: float(v) for k, v in irt['beta'].items()}
sq_ans = [r for r in soft if r['call_type'] == 'answer']
sq_conf = [r for r in soft if r['call_type'] == 'confidence']

def logist(x):
    if x > 20: return 1.0
    if x < -20: return 0.0
    return 1.0 / (1.0 + math.exp(-x))

models = ['GPT-OSS-120B', 'DeepSeek-V4-Flash-158B']
budgets = [256, 512]

# Build lookup: (model, qid, budget, rep) -> retrospective confidence, correctness
retro_map = {}
for r in sq_conf:
    if r['confidence_value'] is not None:
        key = (r['model'], r['question_id'], r['budget'], r['replicate'])
        retro_map[key] = r['confidence_value']

correct_map = {}
for r in sq_ans:
    key = (r['model'], r['question_id'], r['budget'], r['replicate'])
    correct_map[key] = r['correct']

# Build prospective lookup
pros_map = {}
pros_missing = 0
pros_total = 0
for r in pros_raw:
    key = (r['model'], r['question_id'], r['budget'], r['replicate'])
    pros_total += 1
    if r['prospective_confidence'] is not None:
        pros_map[key] = r['prospective_confidence']
    else:
        pros_missing += 1

# =============================================================
# Aggregated Results
# =============================================================
def compute_metrics(values):
    """values: list of (confidence, correctness_bool)"""
    if not values: return {}
    n = len(values)
    confs = [v for v, _ in values]
    correct = [ok for _, ok in values]
    avg_c = sum(confs)/n
    std_c = (sum((v-avg_c)**2 for v in confs)/n)**0.5
    c_range = (min(confs), max(confs))
    brier = sum((c/100.0 - (1 if ok else 0))**2 for c, ok in values)/n
    # ECE (10 bins)
    ece = 0
    for b in range(10):
        lo, hi = b*10, (b+1)*10
        bin_vals = [(c, ok) for c, ok in values if lo <= c <= hi]
        if bin_vals:
            bin_conf = sum(c for c,_ in bin_vals)/len(bin_vals)/100
            bin_acc = sum(1 for _,ok in bin_vals if ok)/len(bin_vals)
            ece += abs(bin_conf - bin_acc) * len(bin_vals)/n
    # AUROC
    # AUROC (manual)
    auroc = None
    if len(set(ok for _, ok in values)) > 1:
        from scipy.stats import mannwhitneyu
        pos = [c/100 for c, ok in values if ok]
        neg = [c/100 for c, ok in values if not ok]
        if pos and neg:
            stat = mannwhitneyu(pos, neg, alternative='greater')
            auroc = stat.statistic / (len(pos) * len(neg))
    # Confidence gap
    correct_c = [c for c, ok in values if ok]
    wrong_c = [c for c, ok in values if not ok]
    gap = (sum(correct_c)/len(correct_c) if correct_c else 0) - (sum(wrong_c)/len(wrong_c) if wrong_c else 0)
    # Spearman correlation
    from scipy.stats import spearmanr, mannwhitneyu
    sp = spearmanr([c for c,_ in values], [ok for _,ok in values]).correlation if len(set(ok for _,ok in values)) > 1 else None
    return {
        'n': n, 'mean_conf': round(avg_c, 1), 'std_conf': round(std_c, 1),
        'conf_range': c_range, 'brier': round(brier, 4), 'ece': round(ece, 4),
        'auroc': round(auroc, 4) if auroc is not None else None,
        'conf_gap': round(gap, 1), 'spearman_r': round(sp, 4) if sp is not None else None
    }

def compute_lcae(values, model_name):
    """values: list of (confidence, correctness_bool, question_id)"""
    diffs = []
    for c, ok, qid in values:
        if qid in beta:
            pe = 1.0 - logist(theta.get(model_name, 0) - beta.get(qid, 0))
            ce = 1.0 - c/100.0
            diffs.append((max(0,min(1,ce)) - max(0,min(1,pe)))**2)
    return round(sum(diffs)/len(diffs), 4) if diffs else None

results = {}
all_data = []

for model in models:
    results[model] = {}
    for budget in budgets:
        # Paired: matched by (model, qid, budget, rep)
        paired = []
        pros_only = []
        retro_only = []
        for r in pros_raw:
            if r['model'] != model or r['budget'] != budget: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            p_conf = r['prospective_confidence']
            r_conf = retro_map.get(key)
            correct = correct_map.get(key)
            if correct is None: continue
            if p_conf is not None:
                pros_only.append((p_conf, correct))
                pros_only_full = (p_conf, correct, r['question_id'])
            if r_conf is not None:
                retro_only.append((r_conf, correct))
                retro_only_full = (r_conf, correct, r['question_id'])
            if p_conf is not None and r_conf is not None and correct is not None:
                paired.append((p_conf, r_conf, correct, r['question_id']))
        
        p_vals = [(c, ok) for c, ok, _, _ in paired]
        r_vals = [(c, ok) for _, c, ok, _ in paired]
        lcae_p_vals = [(c, ok, qid) for c, _, ok, qid in paired]
        lcae_r_vals = [(c, ok, qid) for _, c, ok, qid in paired]
        
        p_uniq = list(set((c, ok) for c, ok, _, _ in paired))
        results[model][f'pros_{budget}'] = compute_metrics(p_vals) if p_vals else {}
        results[model][f'retro_{budget}'] = compute_metrics(r_vals) if r_vals else {}
        results[model][f'paired_n'] = len(paired)
        
        # LCAE
        results[model][f'pros_lcae_{budget}'] = compute_lcae(lcae_p_vals, model)
        results[model][f'retro_lcae_{budget}'] = compute_lcae(lcae_r_vals, model)
        
        # Token correlation
        tok_data = []
        for r in sq_ans:
            if r['model'] != model or r['budget'] != budget: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            p = pros_map.get(key)
            if p is not None:
                tok_data.append((p, r['completion_tokens'], r['correct']))
        tok_n = len(tok_data)
        if tok_n > 1:
            from scipy.stats import spearmanr
            sp_conf_tok = spearmanr([c for c,_,_ in tok_data], [t for _,t,_ in tok_data]).correlation
            sp_conf_corr = spearmanr([c for c,_,_ in tok_data], [1 if ok else 0 for _,_,ok in tok_data]).correlation
            # Low-conf vs high-conf token usage
            low = [t for c,t,ok in tok_data if c < 70]
            high = [t for c,t,ok in tok_data if c >= 90]
            results[model][f'tok_corr_{budget}'] = {
                'n': tok_n, 'conf_tok_sp': round(sp_conf_tok, 4),
                'conf_correct_sp': round(sp_conf_corr, 4),
                'low_conf_mean_tok': round(sum(low)/len(low), 1) if low else None,
                'high_conf_mean_tok': round(sum(high)/len(high), 1) if high else None,
                'low_conf_n': len(low), 'high_conf_n': len(high),
            }
        
        # Missing stats
        total_pros = sum(1 for r in pros_raw if r['model'] == model and r['budget'] == budget)
        parsed_pros = sum(1 for r in pros_raw if r['model'] == model and r['budget'] == budget and r['prospective_confidence'] is not None)
        results[model][f'missing_{budget}'] = {
            'total': total_pros, 'parsed': parsed_pros, 'missing': total_pros - parsed_pros,
            'parse_rate': round(parsed_pros/total_pros*100, 1) if total_pros > 0 else 0,
        }

# Save JSON
with open('experiments/v3-budget-pilot/results/prospective_conf_analysis.json', 'w') as f:
    json.dump({k: {str(k2): v2 for k2, v2 in v.items()} for k, v in results.items()}, f, indent=2)

# =============================================================
# MD Report
# =============================================================
lines = []
lines.append("# Prospective vs Retrospective Confidence Analysis")
lines.append("> 360 paired calls, matched by model/question_id/budget/replicate\n")

lines.append("## 1. Parse / Missing Statistics")
for model in models:
    for budget in budgets:
        m = results[model].get(f'missing_{budget}', {})
        lines.append(f"- {model} @ {budget}: {m.get('parsed','?')}/{m.get('total','?')} parsed ({m.get('parse_rate','?')}%)")
lines.append("")

lines.append("## 2. Prospective vs Retrospective Confidence (Paired)")
lines.append("")
hdr = "| Model | Budget | Type | N | Mean | Brier | ECE | AUROC | Gap | Spearman |"
sep = "|------|--------|------|---|------|-------|-----|-------|-----|----------|"
lines.append(hdr); lines.append(sep)
for model in models:
    for budget in budgets:
        for ctype, prefix in [('Prospective', f'pros_{budget}'), ('Retrospective', f'retro_{budget}')]:
            d = results[model].get(prefix, {})
            if d:
                lines.append(f"| {model:18s} | {budget:6d} | {ctype:13s} | {d.get('n','?'):3d} | {d.get('mean_conf','?'):5.1f} | {d.get('brier','?'):5.4f} | {d.get('ece','?'):5.4f} | {str(d.get('auroc','?')):7s} | {d.get('conf_gap','?'):5.1f} | {str(d.get('spearman_r','?')):8s} |")
lines.append("")

lines.append("## 3. LCAE Comparison")
lines.append("")
lines.append(f"| Model | Budget | Prospective LCAE | Retrospective LCAE | Hard LCAE |")
lines.append(f"|-------|--------|-----------------|-------------------|-----------|")
for model in models:
    for budget in budgets:
        pl = results[model].get(f'pros_lcae_{budget}', 'N/A')
        rl = results[model].get(f'retro_lcae_{budget}', 'N/A')
        hl = irt.get('lcae', {}).get(model, 'N/A')
        lines.append(f"| {model:18s} | {budget:6d} | {str(pl):15s} | {str(rl):17s} | {str(hl):9s} |")
lines.append("")
lines.append("*Note: Prospective/Soft LCAE uses Phase 3 IRT parameters (anchored LCAE)*\n")

lines.append("## 4. Confidence vs Actual Tokens")
lines.append("")
for model in models:
    lines.append(f"\n**{model}:**")
    for budget in budgets:
        d = results[model].get(f'tok_corr_{budget}', {})
        if d:
            lines.append(f"- Budget {budget}: conf-tok Spearman r = {d.get('conf_tok_sp','?')}")
            lines.append(f"  - conf-correct Spearman r = {d.get('conf_correct_sp','?')}")
            lines.append(f"  - Low-conf (<70) mean tok: {d.get('low_conf_mean_tok','?')} (n={d.get('low_conf_n','?')})")
            lines.append(f"  - High-conf (>=90) mean tok: {d.get('high_conf_mean_tok','?')} (n={d.get('high_conf_n','?')})")

lines.append("\n## 5. Missing Data Note")
lines.append("GPT-OSS-120B had ~3% parse failures (6/180 calls). These were consistently on one hard counting_and_probability question")
lines.append("where `done_reason=length` cut the thinking process before confidence could be output. All failures excluded from analysis.\n")

lines.append("## 6. Limitations")
lines.append("- Anchored LCAE uses Phase 3 IRT params, not Soft-specific calibration")
lines.append("- Paired analysis only covers matched calls; unmatched calls excluded")
lines.append("- Small sample (n=90 per model×budget) limits AUROC reliability\n")

lines.append("## 7. Next Steps")
lines.append("- If prospective shows improvement → external budget controller")
lines.append("- If similar → compare with IRT difficulty, token entropy, hybrid signal")
lines.append("- If still overconfident → post-hoc scaling or percentile-based allocation\n")

with open('experiments/v3-budget-pilot/results/prospective_conf_analysis.md', 'w') as f:
    f.write('\n'.join(lines))

print("Saved prospective_conf_analysis.json and prospective_conf_analysis.md")
# Print summary
for model in models:
    for budget in budgets:
        p = results[model].get(f'pros_{budget}', {})
        r = results[model].get(f'retro_{budget}', {})
        pl = results[model].get(f'pros_lcae_{budget}', '?')
        rl = results[model].get(f'retro_lcae_{budget}', '?')
        print(f"\n{model} @ {budget} (n={p.get('n','?')}):")
        print(f"  Prospective: Brier={p.get('brier','?')}, LCAE={pl}, AUROC={p.get('auroc','?')}, Gap={p.get('conf_gap','?')}")
        print(f"  Retrospective: Brier={r.get('brier','?')}, LCAE={rl}, AUROC={r.get('auroc','?')}, Gap={r.get('conf_gap','?')}")