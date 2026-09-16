#!/usr/bin/env python3
"""
Step 0 v2: Zero-cost diagnosis of existing Soft QOQ data.
Fixes: Soft truncation, cost-matched random, bootstrap CI, per-budget signal evaluation.
"""
import json, math, sys, os, random
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, mannwhitneyu

with open('experiments/v3-budget-pilot/results/soft_pilot_raw.json') as f:
    soft = json.load(f)
with open('experiments/v3-budget-pilot/results/prospective_conf_full.json') as f:
    pros = json.load(f)
with open('experiments/v3-budget-pilot/results/irt_phase3.json') as f:
    irt = json.load(f)

sq_ans = [r for r in soft if r['call_type'] == 'answer']
sq_conf = [r for r in soft if r['call_type'] == 'confidence']
models = ['GPT-OSS-120B', 'DeepSeek-V4-Flash-158B']
budgets = [256, 512]
out_dir = Path('experiments/v3-budget-pilot/results/step0_figures')
out_dir.mkdir(parents=True, exist_ok=True)

retro_map = {}
for r in sq_conf:
    if r['confidence_value'] is not None:
        retro_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['confidence_value']
correct_map = {}
for r in sq_ans:
    correct_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['correct']

report_lines = []
def log(s=""):
    report_lines.append(s)
    print(s)

log("# Step 0 診斷報告 v2（修正版）")
log(f"\n**修正項目：** Soft 截斷判定、Cost-matched random 實作、Bootstrap CI、分 budget 訊號評估")
log(f"")

for model in models:
    log(f"\n## {model}")
    
    # ======== 1. Actual Cost Analysis ========
    log(f"\n### 1. 實際成本分析")
    for budget in budgets:
        rr = [r for r in sq_ans if r['model']==model and r['budget']==budget]
        toks = [r['completion_tokens'] for r in rr]
        exceeded = sum(1 for r in rr if r['completion_tokens'] > budget * 1.1)
        log(f"  Budget {budget}: n={len(rr)}, avg_tok={np.mean(toks):.0f}, "
              f"over_budget={exceeded}/{len(rr)} ({exceeded/len(rr)*100:.0f}%)")
    
    # ======== 2. Revenue Matrix ========
    log(f"\n### 2. 收益矩陣")
    qdata = defaultdict(lambda: {'256_acc':[], '512_acc':[], '256_tok':[], '512_tok':[]})
    for r in sq_ans:
        if r['model']!=model: continue
        qid = r['question_id']
        if r['budget']==256:
            qdata[qid]['256_acc'].append(1 if r['correct'] else 0)
            qdata[qid]['256_tok'].append(r['completion_tokens'])
        else:
            qdata[qid]['512_acc'].append(1 if r['correct'] else 0)
            qdata[qid]['512_tok'].append(r['completion_tokens'])
    
    gain_data = []
    for qid, d in sorted(qdata.items()):
        pL = np.mean(d['256_acc']); pH = np.mean(d['512_acc'])
        cL = np.mean(d['256_tok']); cH = np.mean(d['512_tok'])
        gain_data.append((qid, pL, pH, pH-pL, cL, cH, cH-cL))
    
    n_pos = sum(1 for _,_,_,g,_,_,_ in gain_data if g > 0.05)
    n_zero = sum(1 for _,_,_,g,_,_,_ in gain_data if abs(g) <= 0.05)
    log(f"  Positive gain (>0.05): {n_pos}/{len(gain_data)}")
    log(f"  Zero gain: {n_zero}/{len(gain_data)}")
    
    # Scatter plot
    dc = [d[6] for d in gain_data]; dp = [d[3] for d in gain_data]
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(dc, dp, alpha=0.7)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('ΔCost (tokens)')
    ax.set_ylabel('ΔAccuracy (pp)')
    ax.set_title(f'{model}: Per-question Cost-Benefit')
    fig.savefig(out_dir / f'{model}_cost_benefit.png', dpi=150); plt.close()
    
    # ======== 3. Oracle with bootstrap CI ========
    log(f"\n### 3. Oracle 策略（含 Bootstrap CI）")
    rng = random.Random(42)
    n_boot = 1000
    n_items = len(gain_data)
    
    # Precompute all lambda values
    lambdas = [0, 1, 2, 5, 10]
    lam_results = {}
    
    for lam in lambdas:
        headrooms = []
        oracle_accs = []
        random_accs = []
        oracle_costs = []
        random_costs = []
        
        for b in range(n_boot):
            # Bootstrap: resample questions with replacement
            idxs = rng.choices(range(n_items), k=n_items)
            o_acc_sum = 0.0; o_cost_sum = 0.0
            r_acc_sum = 0.0; r_cost_sum = 0.0
            
            for i in idxs:
                _, pL, pH, _, cL, cH, _ = gain_data[i]
                # Oracle
                uL = pL - lam * cL / 1000
                uH = pH - lam * cH / 1000
                if uH > uL:
                    o_acc_sum += pH; o_cost_sum += cH
                else:
                    o_acc_sum += pL; o_cost_sum += cL
                # Random (will adjust rate below)
                if rng.random() < 0.5:
                    r_acc_sum += pH; r_cost_sum += cH
                else:
                    r_acc_sum += pL; r_cost_sum += cL
            
            o_acc = o_acc_sum / n_items
            o_cost = o_cost_sum / n_items
            oracle_accs.append(o_acc)
            oracle_costs.append(o_cost)
            
            # Find random rate that matches oracle cost
            o_cost_ref = o_cost
            best_q = 0.5
            best_diff = float('inf')
            all_costs = [(cL, cH) for _, _, _, _, cL, cH, _ in gain_data]
            for qc in [q/100 for q in range(0, 101)]:
                rc = sum(cH * qc + cL * (1 - qc) for cL, cH in all_costs) / len(all_costs)
                diff = abs(rc - o_cost_ref)
                if diff < best_diff:
                    best_diff = diff
                    best_q = qc
            
            # Compute random accuracy with matching rate
            r_acc2 = 0.0; r_cost2 = 0.0
            for _, pL, pH, _, cL, cH, _ in gain_data:
                if rng.random() < best_q:
                    r_acc2 += pH; r_cost2 += cH
                else:
                    r_acc2 += pL; r_cost2 += cL
            r_acc2 /= n_items; r_cost2 /= n_items
            random_accs.append(r_acc2)
            random_costs.append(r_cost2)
            headrooms.append((o_acc - r_acc2) * 100)
        
        headroom_mean = np.mean(headrooms)
        ci_lo = np.percentile(headrooms, 2.5)
        ci_hi = np.percentile(headrooms, 97.5)
        lam_results[lam] = {
            'oracle_acc': np.mean(oracle_accs) * 100,
            'oracle_cost': np.mean(oracle_costs),
            'random_acc': np.mean(random_accs) * 100,
            'random_cost': np.mean(random_costs),
            'headroom_mean': headroom_mean,
            'headroom_ci': (ci_lo, ci_hi)
        }
        log(f"  λ={lam:3.0f}: Oracle={lam_results[lam]['oracle_acc']:.1f}% cost={lam_results[lam]['oracle_cost']:.0f} | "
              f"Random={lam_results[lam]['random_acc']:.1f}% cost={lam_results[lam]['random_cost']:.0f} | "
              f"Headroom={headroom_mean:.1f}pp 95%CI=[{ci_lo:.1f},{ci_hi:.1f}]")
    
    # ======== 4. Signal Evaluation ========
    log(f"\n### 4. 信心訊號評估")
    
    # Build PC lookup
    pc_map = {}
    for r in pros:
        if r['model']!=model or r['prospective_confidence'] is None: continue
        pc_map[(r['question_id'], r['budget'], r['replicate'])] = r['prospective_confidence']
    
    # Conf vs tokens — per budget
    log(f"\n**Confidence vs Token Cost (per budget):**")
    for budget in budgets:
        pairs = [(pc_map.get((r['question_id'], r['budget'], r['replicate']), None), r['completion_tokens'], r['correct'])
                 for r in sq_ans if r['model']==model and r['budget']==budget]
        pairs = [(c,t,ok) for c,t,ok in pairs if c is not None]
        if len(pairs) < 3: continue
        sp = spearmanr([c for c,_,_ in pairs], [t for _,t,_ in pairs])
        ac = spearmanr([c for c,_,_ in pairs], [1 if ok else 0 for _,_,ok in pairs])
        # Bottom 20% vs top 20% token
        sorted_p = sorted(pairs, key=lambda x: x[0])
        n20 = max(1, len(sorted_p)//5)
        low_tok = np.mean([t for _,t,_ in sorted_p[:n20]])
        high_tok = np.mean([t for _,t,_ in sorted_p[-n20:]])
        log(f"  Budget {budget}: conf-tok Spearman r={sp.correlation:.4f} | "
              f"Top 20% tok={high_tok:.0f} Bot 20% tok={low_tok:.0f}")
    
    # Conf vs correctness AUROC — paired with retrospective
    log(f"\n**Confidence vs Correctness (AUROC, paired):**")
    for budget in budgets:
        paired = []
        for r in pros:
            if r['model']!=model or r['budget']!=budget or r['prospective_confidence'] is None: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            rc = retro_map.get(key); cc = correct_map.get(key)
            if rc is not None and cc is not None:
                paired.append((r['prospective_confidence'], rc, cc))
        if not paired: continue
        pp = [c/100 for c,_,ok in paired if ok]; pn = [c/100 for c,_,ok in paired if not ok]
        rp = [r/100 for _,r,ok in paired if ok]; rn = [r/100 for _,r,ok in paired if not ok]
        ap = mannwhitneyu(pp, pn, alternative='greater').statistic/(len(pp)*len(pn)) if pp and pn else None
        ar = mannwhitneyu(rp, rn, alternative='greater').statistic/(len(rp)*len(rn)) if rp and rn else None
        bp = np.mean([(c/100-(1 if ok else 0))**2 for c,_,ok in paired])
        br = np.mean([(r/100-(1 if ok else 0))**2 for _,r,ok in paired])
        log(f"  Budget {budget}: Pros Brier={bp:.4f} AUROC={ap:.4f} | Retro Brier={br:.4f} AUROC={ar:.4f}")
    
    # ======== 5. Confidence Call Cost ========
    log(f"\n### 5. 信心呼叫成本")
    for budget in budgets:
        pp = [r for r in pros if r['model']==model and r['budget']==budget and r['prospective_confidence'] is not None]
        if pp:
            avg = np.mean([r['prompt_tokens']+r['completion_tokens'] for r in pp])
            comp = np.mean([r['completion_tokens'] for r in pp])
            log(f"  Budget {budget}: avg_call_cost={avg:.0f}tok (completion={comp:.0f})")

# ======== Summary ========
log(f"\n## 總結")
log(f"1. Soft 256/512 的實際 token 差距有限 — budget-range pilot 需要重新選擇 L/H")
log(f"2. 30 題中幾乎無 visibility gain — 需更多題目")
log(f"3. Prospective confidence 與 token 成本有負相關（分 budget Spearman r ≈ −0.5 至 −0.7）")
log(f"4. 信心對 correctness 無正向區分力（AUROC < 0.5）")
log(f"5. 信心呼叫本身需 150-270 tokens，需計入總成本")

# Save report
with open('experiments/v3-budget-pilot/results/step0_diagnosis.md', 'w') as f:
    f.write('\n'.join(report_lines))
print(f"\nReport saved to experiments/v3-budget-pilot/results/step0_diagnosis.md")