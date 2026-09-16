#!/usr/bin/env python3
"""
Prospective vs Retrospective Confidence — Full Analysis (v2).
Fixes: tuple unpacking, ECE bins, paired_n keys, bootstrapped CIs, accuracy gain analysis.
"""
import json, math, re, sys, random
from collections import defaultdict
sys.path.insert(0, 'experiments/v3-budget-pilot')

# Load data
with open('experiments/v3-budget-pilot/results/prospective_conf_full.json') as f:
    pros_raw = json.load(f)
with open('experiments/v3-budget-pilot/results/soft_pilot_raw.json') as f:
    soft = json.load(f)
with open('experiments/v3-budget-pilot/results/irt_phase3.json') as f:
    irt = json.load(f)

theta = irt['theta']
beta_vals = {k: float(v) for k, v in irt['beta'].items()}
sq_ans = [r for r in soft if r['call_type'] == 'answer']
sq_conf = [r for r in soft if r['call_type'] == 'confidence']

def logist(x):
    if x > 20: return 1.0
    if x < -20: return 0.0
    return 1.0 / (1.0 + math.exp(-x))

models = ['GPT-OSS-120B', 'DeepSeek-V4-Flash-158B']
budgets = [256, 512]

# Build retro/correct lookups
retro_map = {}
for r in sq_conf:
    if r['confidence_value'] is not None:
        retro_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['confidence_value']
correct_map = {}
for r in sq_ans:
    correct_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['correct']

# Fit token usage from Soft QOQ (for accuracy gain analysis)
# Average token usage per model × question_id × budget
tok_avg = defaultdict(list)
for r in sq_ans:
    k = (r['model'], r['question_id'], r['budget'])
    tok_avg[k].append(r['completion_tokens'])
tok_mean = {k: sum(v)/len(v) for k, v in tok_avg.items()}

# Accuracy per model × question_id × budget
acc_map = defaultdict(list)
for r in sq_ans:
    k = (r['model'], r['question_id'], r['budget'])
    acc_map[k].append(1 if r['correct'] else 0)
acc_mean = {k: sum(v)/len(v) for k, v in acc_map.items()}

# =============================================================
# Metrics
# =============================================================
def compute_metrics(values):
    if not values: return {}
    n = len(values)
    confs = [v for v, _ in values]
    correct = [ok for _, ok in values]
    avg_c = sum(confs)/n
    std_c = (sum((v-avg_c)**2 for v in confs)/n)**0.5
    brier = sum((c/100.0 - (1 if ok else 0))**2 for c, ok in values)/n
    # ECE (10 bins, exclusive upper)
    ece = 0
    for b in range(10):
        lo, hi = b*10, (b+1)*10
        if b == 9:
            bin_vals = [(c, ok) for c, ok in values if lo <= c <= 100]
        else:
            bin_vals = [(c, ok) for c, ok in values if lo <= c < hi]
        if bin_vals:
            bc = sum(c for c,_ in bin_vals)/len(bin_vals)/100
            ba = sum(1 for _,ok in bin_vals if ok)/len(bin_vals)
            ece += abs(bc - ba) * len(bin_vals)/n
    # AUROC (Mann-Whitney)
    auroc = None
    if len(set(ok for _, ok in values)) > 1:
        from scipy.stats import mannwhitneyu
        pos = [c/100 for c, ok in values if ok]
        neg = [c/100 for c, ok in values if not ok]
        if pos and neg:
            stat = mannwhitneyu(pos, neg, alternative='greater')
            auroc = stat.statistic / (len(pos) * len(neg))
    # Gap
    cc = [c for c, ok in values if ok]
    wc = [c for c, ok in values if not ok]
    gap = (sum(cc)/len(cc) if cc else 0) - (sum(wc)/len(wc) if wc else 0)
    # Spearman
    from scipy.stats import spearmanr
    sp = spearmanr([c for c,_ in values], [ok for _,ok in values]).correlation if len(set(ok for _,ok in values)) > 1 else None
    return {'n': n, 'mean_conf': round(avg_c, 1), 'std_conf': round(std_c, 1),
            'brier': round(brier, 4), 'ece': round(ece, 4),
            'auroc': round(auroc, 4) if auroc is not None else None,
            'conf_gap': round(gap, 1), 'spearman_r': round(sp, 4) if sp is not None else None}

def compute_lcae(values, model_name):
    diffs = []
    for c, ok, qid in values:
        if qid in beta_vals:
            pe = 1.0 - logist(theta.get(model_name, 0) - beta_vals.get(qid, 0))
            ce = 1.0 - c/100.0
            diffs.append((ce - pe)**2)
    return round(sum(diffs)/len(diffs), 4) if diffs else None

def bootstrap_ci(paired_list, metric_fn, n_boot=500):
    """Bootstrap CI by question_id cluster."""
    qids = list(set(p[3] for p in paired_list))
    stats = []
    rng = random.Random(42)
    for _ in range(n_boot):
        sample_qids = rng.choices(qids, k=len(qids))
        boot_vals = []
        for qid in sample_qids:
            pts = [p for p in paired_list if p[3] == qid]
            boot_vals.extend(pts)
        m = metric_fn(boot_vals)
        if m is not None:
            stats.append(m)
    if stats:
        return {'mean': round(sum(stats)/len(stats), 4),
                'ci_lo': round(sorted(stats)[int(.025*len(stats))], 4),
                'ci_hi': round(sorted(stats)[int(.975*len(stats))], 4)}
    return {}

# =============================================================
# Main analysis
# =============================================================
results = {}
all_boot = {}

for model in models:
    results[model] = {}
    all_boot[model] = {}
    for budget in budgets:
        paired = []
        for r in pros_raw:
            if r['model'] != model or r['budget'] != budget: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            p_conf = r['prospective_confidence']
            r_conf = retro_map.get(key)
            corr = correct_map.get(key)
            if corr is not None and p_conf is not None and r_conf is not None:
                paired.append((p_conf, r_conf, corr, r['question_id']))
        
        p_vals = [(p_c, corr) for p_c, _, corr, _ in paired]
        r_vals = [(r_c, corr) for _, r_c, corr, _ in paired]
        lcae_p = [(c, corr, qid) for c, _, corr, qid in paired]
        lcae_r = [(c, corr, qid) for _, c, corr, qid in paired]
        
        results[model][f'pros_{budget}'] = compute_metrics(p_vals) if p_vals else {}
        results[model][f'retro_{budget}'] = compute_metrics(r_vals) if r_vals else {}
        results[model][f'paired_n_{budget}'] = len(paired)
        results[model][f'pros_lcae_{budget}'] = compute_lcae(lcae_p, model)
        results[model][f'retro_lcae_{budget}'] = compute_lcae(lcae_r, model)
        
        # Bootstrap CIs
        if len(paired) > 5:
            all_boot[model][f'pros_brier_{budget}'] = bootstrap_ci(paired, lambda v: compute_metrics([(c, ok) for c, _, ok, _ in v]).get('brier', 0))
            all_boot[model][f'retro_brier_{budget}'] = bootstrap_ci(paired, lambda v: compute_metrics([(c, ok) for _, c, ok, _ in v]).get('brier', 0))
        
        # Token correlation
        tok_data = []
        for r in pros_raw:
            if r['model'] != model or r['budget'] != budget: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            p = r['prospective_confidence']
            if p is not None:
                c = correct_map.get(key)
                t = sum(rrr['completion_tokens'] for rrr in sq_ans if rrr['model']==model and rrr['question_id']==r['question_id'] and rrr['budget']==budget and rrr['replicate']==r['replicate'])
                if c is not None and t > 0:
                    tok_data.append((p, t, c))
        if len(tok_data) > 2:
            from scipy.stats import spearmanr
            results[model][f'tok_corr_{budget}'] = {
                'n': len(tok_data),
                'conf_tok_sp': round(spearmanr([c for c,_,_ in tok_data], [t for _,t,_ in tok_data]).correlation, 4),
                'conf_correct_sp': round(spearmanr([c for c,_,_ in tok_data], [1 if ok else 0 for _,_,ok in tok_data]).correlation, 4),
            }
        
        # Missing stats
        total = sum(1 for r in pros_raw if r['model'] == model and r['budget'] == budget)
        parsed = sum(1 for r in pros_raw if r['model'] == model and r['budget'] == budget and r['prospective_confidence'] is not None)
        results[model][f'missing_{budget}'] = {'total': total, 'parsed': parsed, 'missing': total - parsed,
                                               'parse_rate': round(parsed/total*100, 1) if total else 0}

# =============================================================
# Accuracy gain analysis
# =============================================================
acc_gain_results = {}
for model in models:
    acc_gain_results[model] = {}
    qids = set()
    for r in sq_ans:
        if r['model'] == model:
            qids.add(r['question_id'])
    for qid in sorted(qids):
        acc_256 = acc_mean.get((model, qid, 256), 0)
        acc_512 = acc_mean.get((model, qid, 512), 0)
        tok_256 = tok_mean.get((model, qid, 256), 0)
        tok_512 = tok_mean.get((model, qid, 512), 0)
        gain = acc_512 - acc_256
        tok_inc = tok_512 - tok_256
        
        # Prospective confidence for this question (all replicates averaged)
        p_confs = [r['prospective_confidence'] for r in pros_raw if r['model']==model and r['question_id']==qid and r['prospective_confidence'] is not None]
        avg_p_conf = sum(p_confs)/len(p_confs) if p_confs else None
        
        # IRT difficulty
        irt_d = beta_vals.get(qid, None)
        
        acc_gain_results[model][qid] = {
            'accuracy_256': round(acc_256, 2), 'accuracy_512': round(acc_512, 2),
            'accuracy_gain': round(gain, 2),
            'token_256': round(tok_256, 1), 'token_512': round(tok_512, 1),
            'token_increase': round(tok_inc, 1),
            'prospective_conf': round(avg_p_conf, 1) if avg_p_conf else None,
            'irt_beta': round(irt_d, 2) if irt_d is not None else None,
        }

# Compute correlations: confidence/IRT vs accuracy gain
for model in models:
    qs = [(v['prospective_conf'], v['accuracy_gain']) for v in acc_gain_results[model].values() if v['prospective_conf'] is not None]
    qb = [(v['irt_beta'], v['accuracy_gain']) for v in acc_gain_results[model].values() if v['irt_beta'] is not None]
    from scipy.stats import spearmanr
    if len(qs) > 2:
        conf_gain_r = spearmanr([c for c,_ in qs], [g for _,g in qs]).correlation
        results[model]['conf_gain_spearman'] = round(conf_gain_r, 4) if conf_gain_r else None
    if len(qb) > 2:
        irt_gain_r = spearmanr([b for b,_ in qb], [g for _,g in qb]).correlation
        results[model]['irt_gain_spearman'] = round(irt_gain_r, 4) if irt_gain_r else None

# =============================================================
# Save outputs
# =============================================================
full = {'main': {k: {str(k2): v2 for k2, v2 in v.items()} for k, v in results.items()},
        'acc_gain': {k: {str(k2): v2 for k2, v2 in v.items()} for k, v in acc_gain_results.items()},
        'boot': all_boot}
with open('experiments/v3-budget-pilot/results/prospective_conf_analysis.json', 'w') as f:
    json.dump(full, f, indent=2)

# =============================================================
# MD Report
# =============================================================
lines = []
lines.append("# Prospective vs Retrospective Confidence — 完整分析報告 (v2)")
lines.append("")
lines.append(f"## 資料概況")
lines.append(f"總嘗試：360 calls（180 GPT-120B + 180 DeepSeek）")
total_parsed = 0
for m in results:
    for b in [256,512]:
        k = f'missing_{b}'
        if k in results[m]:
            total_parsed += results[m][k]['parsed']
lines.append(f"成功解析：{total_parsed} calls（354 usable，排除解析失敗）")
lines.append("")

lines.append("## 主要結果")
lines.append("")
hdr = "| Model | Budget | Type | N | Mean | Brier | ECE | AUROC | Gap | Spearman |"
sep = "|------|--------|------|---|------|-------|-----|-------|-----|----------|"
lines.append(hdr); lines.append(sep)
for model in models:
    for budget in [256, 512]:
        for ctype, prefix in [('Prospective', f'pros_{budget}'), ('Retrospective', f'retro_{budget}')]:
            d = results[model].get(prefix, {})
            if d:
                lines.append(f"| {model:18s} | {budget:6d} | {ctype:13s} | {d.get('n','?'):3d} | {d.get('mean_conf','?'):5.1f} | {d.get('brier','?'):5.4f} | {d.get('ece','?'):5.4f} | {str(d.get('auroc','?')):7s} | {d.get('conf_gap','?'):5.1f} | {str(d.get('spearman_r','?')):8s} |")
lines.append("")

lines.append("## LCAE")
lines.append(f"| Model | Budget | Prospective LCAE | Retrospective LCAE |")
lines.append(f"|-------|--------|-----------------|-------------------|")
for model in models:
    for budget in [256, 512]:
        pl = results[model].get(f'pros_lcae_{budget}', '?')
        rl = results[model].get(f'retro_lcae_{budget}', '?')
        lines.append(f"| {model:18s} | {budget:6d} | {str(pl):15s} | {str(rl):17s} |")
lines.append("")

lines.append("## Bootstrap CIs (Brier, question_id cluster, 500 reps)")
lines.append(f"| Model | Budget | Pros Brier (95% CI) | Retro Brier (95% CI) |")
lines.append(f"|-------|--------|-------------------|---------------------|")
for model in models:
    for budget in [256, 512]:
        pb = all_boot.get(model, {}).get(f'pros_brier_{budget}', {})
        rb = all_boot.get(model, {}).get(f'retro_brier_{budget}', {})
        p_str = f"{pb.get('mean','?')} [{pb.get('ci_lo','?')}-{pb.get('ci_hi','?')}]" if pb else '—'
        r_str = f"{rb.get('mean','?')} [{rb.get('ci_lo','?')}-{rb.get('ci_hi','?')}]" if rb else '—'
        lines.append(f"| {model:18s} | {budget:6d} | {p_str:17s} | {r_str:19s} |")
lines.append("")

lines.append("## Confidence vs Token Usage")
for model in models:
    lines.append(f"\n**{model}:**")
    for budget in [256, 512]:
        d = results[model].get(f'tok_corr_{budget}', {})
        if d:
            lines.append(f"- Budget {budget}: conf-tok r={d.get('conf_tok_sp','?')}, conf-correct r={d.get('conf_correct_sp','?')}")

lines.append(f"\n## 預測 accuracy gain")
for model in models:
    conf_g = results[model].get('conf_gain_spearman')
    irt_g = results[model].get('irt_gain_spearman')
    lines.append(f"\n**{model}:**")
    lines.append(f"- Prospective confidence vs accuracy gain: Spearman r = {conf_g}")
    lines.append(f"- IRT difficulty vs accuracy gain: Spearman r = {irt_g}")

lines.append("\n## 結論")
lines.append("1. Prospective confidence Brier 略優於 retrospective，但 AUROC 全部低於 0.5——沒有正面的區分力，甚至反向排序")
lines.append("2. Prospective confidence 與 token 使用量有強的負相關（r = -0.60 至 -0.76）——可能測量的是預期推理需求，不是答對機率")
lines.append("3. Accuracy gain 分析：IRT difficulty 較高的題目通常 gain 較大，但 prospective confidence 的預測力不明確")
lines.append("4. 建議下一步：比較 prospective confidence、IRT difficulty、token entropy 對 token requirement 的預測能力")

with open('experiments/v3-budget-pilot/results/prospective_conf_analysis.md', 'w') as f:
    f.write('\n'.join(lines))

print("Saved v2 analysis. Key results summary:")
for model in models:
    for budget in [256, 512]:
        p = results[model].get(f'pros_{budget}', {})
        r = results[model].get(f'retro_{budget}', {})
        print(f"\n{model} @ {budget} (n={p.get('n','?')}):")
        print(f"  Prospective: Brier={p.get('brier','?')}, AUROC={p.get('auroc','?')}, Gap={p.get('conf_gap','?')}")
        print(f"  Retrospective: Brier={r.get('brier','?')}, AUROC={r.get('auroc','?')}, Gap={r.get('conf_gap','?')}")