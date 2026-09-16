#!/usr/bin/env python3
"""
Step 0: Zero-cost diagnosis of existing Soft QOQ data.
Outputs: cost-revenue matrix, oracle curve, signal evaluation, pilot recommendations.
"""
import json, math, sys, os, random
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, 'experiments/v3-budget-pilot')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr, mannwhitneyu

# Load data
with open('experiments/v3-budget-pilot/results/soft_pilot_raw.json') as f:
    soft = json.load(f)
with open('experiments/v3-budget-pilot/results/prospective_conf_full.json') as f:
    pros = json.load(f)

sq_ans = [r for r in soft if r['call_type'] == 'answer']
sq_conf = [r for r in soft if r['call_type'] == 'confidence']

models = ['GPT-OSS-120B', 'DeepSeek-V4-Flash-158B']
out_dir = Path('experiments/v3-budget-pilot/results/step0_figures')
out_dir.mkdir(parents=True, exist_ok=True)

results = {}

for model in models:
    print(f"\n{'='*60}")
    print(f"  {model}")
    print(f"{'='*60}")
    
    # ================================================================
    # 1. Actual cost analysis
    # ================================================================
    print("\n--- 1. Actual Cost Analysis ---")
    for budget in [256, 512]:
        rr = [r for r in sq_ans if r['model']==model and r['budget']==budget]
        tokens = [r['completion_tokens'] for r in rr]
        truncated = sum(1 for r in rr if r['completion_tokens']>=budget*0.9)
        unparsed = sum(1 for r in rr if not r.get('parsed_answer',''))
        has_answer = sum(1 for r in rr if r.get('parsed_answer',''))
        print(f"  Budget {budget}: n={len(rr)}, avg_tok={sum(tokens)/len(rr):.0f}, "
              f"truncated={truncated}, unparsed={unparsed}, answer_rate={has_answer/len(rr)*100:.0f}%")
    
    # ================================================================
    # 2. Revenue matrix (per question)
    # ================================================================
    print("\n--- 2. Revenue Matrix ---")
    qdata = {}
    for r in sq_ans:
        if r['model']!=model: continue
        qid = r['question_id']
        if qid not in qdata:
            qdata[qid] = {'256_acc':[], '512_acc':[], '256_tok':[], '512_tok':[]}
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
        gain = pH - pL
        gain_data.append((qid, pL, pH, gain, cL, cH, cH-cL))
    
    n_pos = sum(1 for _,_,_,g,_,_,_ in gain_data if g > 0)
    n_zero = sum(1 for _,_,_,g,_,_,_ in gain_data if g == 0)
    n_neg = sum(1 for _,_,_,g,_,_,_ in gain_data if g < 0)
    print(f"  Positive gain: {n_pos}/{len(gain_data)}")
    print(f"  Zero gain:     {n_zero}/{len(gain_data)}")
    print(f"  Negative gain: {n_neg}/{len(gain_data)}")
    
    # Scatter plot: ΔC vs ΔP
    fig, ax = plt.subplots(figsize=(8,6))
    dc = [d[6] for d in gain_data]
    dp = [d[3] for d in gain_data]
    ax.scatter(dc, dp, alpha=0.7)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('ΔCost (tokens)')
    ax.set_ylabel('ΔAccuracy (pp)')
    ax.set_title(f'{model}: Per-question Cost-Benefit (Hard IRT difficulty colors not available)')
    fig.savefig(out_dir / f'{model}_cost_benefit.png', dpi=150)
    plt.close(fig)
    print(f"  Saved scatter: {model}_cost_benefit.png")
    
    # ================================================================
    # 3. Oracle, Random, Fixed baselines with bootstrap
    # ================================================================
    print("\n--- 3. Oracle / Random / Fixed Baselines ---")
    
    def simulate(alloc_fn, lambdas, n_boot=1000):
        """For each lambda, compute cost-matching random and oracle."""
        rng = random.Random(42)
        qids_list = [d[0] for d in gain_data]
        # For each lambda, compute oracle
        oracle_accs, oracle_costs = [], []
        random_accs, random_costs = [], []
        allL_acc, allL_cost = [], []
        allH_acc, allH_cost = [], []
        
        for lam in lambdas:
            boot_o_acc, boot_o_cost = [], []
            boot_r_acc, boot_r_cost = [], []
            boot_l_acc, boot_l_cost = [], []
            boot_h_acc, boot_h_cost = [], []
            
            for b in range(n_boot):
                sample = rng.choices(list(range(len(qids_list))), k=len(qids_list))
                o_acc, o_cost = 0, 0
                r_acc, r_cost = 0, 0
                l_acc, l_cost = 0, 0
                h_acc, h_cost = 0, 0
                
                for idx in sample:
                    _, pL, pH, gain, cL, cH, dC = gain_data[idx]
                    l_acc += pL; l_cost += cL
                    h_acc += pH; h_cost += cH
                    # Oracle
                    uL = pL - lam * cL / 100  # scale lamda to tokens
                    uH = pH - lam * cH / 100
                    if uH > uL:
                        o_acc += pH; o_cost += cH
                    else:
                        o_acc += pL; o_cost += cL
                    # Random (will adjust below)
                    if rng.random() < 0.5:
                        r_acc += pH; r_cost += cH
                    else:
                        r_acc += pL; r_cost += cL
                
                n = len(sample)
                boot_o_acc.append(o_acc/n); boot_o_cost.append(o_cost/n)
                boot_r_acc.append(r_acc/n); boot_r_cost.append(r_cost/n)
                boot_l_acc.append(l_acc/n); boot_l_cost.append(l_cost/n)
                boot_h_acc.append(h_acc/n); boot_h_cost.append(h_cost/n)
            
            # Cost-matching adjustment: find random rate that matches oracle cost
            o_mean_cost = np.mean(boot_o_cost)
            # Simple linear search for matching rate
            best_rate = 0.5
            for rate in [r/100 for r in range(0, 101)]:
                r_acc, r_cost = 0, 0
                for _, pL, pH, _, cL, cH, _ in gain_data:
                    if rng.random() < rate:
                        r_acc += pH; r_cost += cH
                    else:
                        r_acc += pL; r_cost += cL
                r_acc /= len(gain_data); r_cost /= len(gain_data)
                if abs(r_cost - o_mean_cost) < abs(best_rate * (cH-cL)/len(gain_data)):
                    best_rate = rate
            
            # Recompute random with matching rate
            rng2 = random.Random(42)
            boot_r2_acc = []
            for b in range(n_boot):
                idxs = rng2.choices(range(len(gain_data)), k=len(gain_data))
                acc = 0; cost = 0
                for i in idxs:
                    _, pL, pH, _, cL, cH, _ = gain_data[i]
                    if rng2.random() < best_rate/100:
                        acc += pH; cost += cH
                    else:
                        acc += pL; cost += cL
                boot_r2_acc.append(acc/len(idxs))
            
            oracle_accs.append(np.mean(boot_o_acc))
            oracle_costs.append(np.mean(boot_o_cost))
            random_accs.append(np.mean(boot_r2_acc))
            random_costs.append(np.mean(boot_o_cost))
            allL_acc.append(np.mean(boot_l_acc))
            allL_cost.append(np.mean(boot_l_cost))
            allH_acc.append(np.mean(boot_h_acc))
            allH_cost.append(np.mean(boot_h_cost))
        
        return oracle_accs, oracle_costs, random_accs, random_costs, allL_acc, allL_cost, allH_acc, allH_cost
    
    lambdas = [0, 0.5, 1, 2, 5, 10]
    oa, oc, ra, rc, la, lc, ha, hc = simulate(None, lambdas, n_boot=500)
    
    # Print results
    for i, lam in enumerate(lambdas):
        headroom = (oa[i] - ra[i]) * 100
        print(f"  λ={lam:3.0f}: Oracle={oa[i]*100:.1f}% cost={oc[i]:.0f} | Random={ra[i]*100:.1f}% | Headroom={headroom:.1f}pp")
    print(f"  All-L: acc={la[0]*100:.1f}% cost={lc[0]:.0f}")
    print(f"  All-H: acc={ha[0]*100:.1f}% cost={hc[0]:.0f}")
    
    # Cost-accuracy curve
    fig, ax = plt.subplots(figsize=(8,6))
    ax.plot(oc, [a*100 for a in oa], 'go-', label='Oracle')
    ax.plot(rc, [a*100 for a in ra], 'rs-', label='Cost-matched Random')
    ax.scatter(lc[0], la[0]*100, c='blue', marker='o', s=100, label='All-L')
    ax.scatter(hc[0], ha[0]*100, c='red', marker='^', s=100, label='All-H')
    ax.set_xlabel('Average Cost (tokens)')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title(f'{model}: Cost-Accuracy Frontier')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(out_dir / f'{model}_cost_accuracy.png', dpi=150)
    plt.close(fig)
    
    # ================================================================
    # 4. Confidence signal evaluation
    # ================================================================
    print("\n--- 4. Signal Evaluation ---")
    
    # Build prospective confidence lookup
    pc_map = {}
    for r in pros:
        if r['model']!=model or r['prospective_confidence'] is None: continue
        pc_map[(r['question_id'], r['budget'], r['replicate'])] = r['prospective_confidence']
    
    # Conf vs tokens
    conf_tok = []
    for r in sq_ans:
        if r['model']!=model: continue
        key = (r['question_id'], r['budget'], r['replicate'])
        if key in pc_map:
            conf_tok.append((pc_map[key], r['completion_tokens'], r['correct']))
    
    if len(conf_tok) > 2:
        sp = spearmanr([c for c,_,_ in conf_tok], [t for _,t,_ in conf_tok])
        print(f"  Conf-Tok Spearman: r={sp.correlation:.4f} (p={sp.pvalue:.4f})")
        
        # Low vs high conf
        low = [t for c,t,_ in conf_tok if c < 70]
        high = [t for c,t,_ in conf_tok if c >= 90]
        print(f"  Low-conf (<70) n={len(low)}, avg_tok={np.mean(low):.0f}" if low else "  Low-conf: n=0")
        print(f"  High-conf (>=90) n={len(high)}, avg_tok={np.mean(high):.0f}" if high else "  High-conf: n=0")
        
        # Conf vs correctness AUROC
        pos = [c/100 for c,_,ok in conf_tok if ok]
        neg = [c/100 for c,_,ok in conf_tok if not ok]
        if pos and neg:
            stat = mannwhitneyu(pos, neg, alternative='greater')
            auroc = stat.statistic / (len(pos)*len(neg))
            print(f"  Conf-Correct AUROC: {auroc:.4f}")
        else:
            print("  Conf-Correct AUROC: N/A (no variation)")
    
    # Conf vs retrospective comparison (paired)
    retro_map = {}
    for r in sq_conf:
        if r['model']!=model or r['confidence_value'] is None: continue
        retro_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['confidence_value']
    
    correct_map = {}
    for r in sq_ans:
        correct_map[(r['model'], r['question_id'], r['budget'], r['replicate'])] = r['correct']
    
    for budget in [256, 512]:
        paired_p, paired_r = [], []
        for r in pros:
            if r['model']!=model or r['budget']!=budget or r['prospective_confidence'] is None: continue
            key = (r['model'], r['question_id'], r['budget'], r['replicate'])
            rc = retro_map.get(key)
            cc = correct_map.get(key)
            if rc is not None and cc is not None:
                paired_p.append((r['prospective_confidence'], cc))
                paired_r.append((rc, cc))
        
        if paired_p:
            bp = sum((c/100-(1 if ok else 0))**2 for c,ok in paired_p)/len(paired_p)
            br = sum((c/100-(1 if ok else 0))**2 for c,ok in paired_r)/len(paired_r)
            # AUROC
            pp = [c/100 for c,ok in paired_p if ok]; pn = [c/100 for c,ok in paired_p if not ok]
            rp = [c/100 for c,ok in paired_r if ok]; rn = [c/100 for c,ok in paired_r if not ok]
            ap = mannwhitneyu(pp, pn, alternative='greater').statistic/(len(pp)*len(pn)) if pp and pn else None
            ar = mannwhitneyu(rp, rn, alternative='greater').statistic/(len(rp)*len(rn)) if rp and rn else None
            print(f"  Budget {budget}: Pros Brier={bp:.4f} Retro Brier={br:.4f} | Pros AUROC={ap:.4f} Retro AUROC={ar:.4f}")
    
    # ================================================================
    # 5. Confidence call cost
    # ================================================================
    print("\n--- 5. Confidence Call Cost ---")
    for budget in [256, 512]:
        pp = [r for r in pros if r['model']==model and r['budget']==budget and r['prospective_confidence'] is not None]
        if pp:
            avg_cost = sum(r['prompt_tokens'] + r['completion_tokens'] for r in pp) / len(pp)
            avg_pros = sum(r['completion_tokens'] for r in pp) / len(pp)
            print(f"  Budget {budget}: conf_call_avg={avg_cost:.0f} tokens (prompt+completion)")
            print(f"              conf_completion_avg={avg_pros:.0f}")
    
    results[model] = {'n_questions': len(gain_data), 'n_pos_gain': n_pos}

# ================================================================
# Summary and recommendations
# ================================================================
print("\n" + "="*60)
print("  STEP 0 SUMMARY")
print("="*60)

for model in models:
    r = results[model]
    print(f"\n  {model}: {r['n_questions']} questions, {r['n_pos_gain']} positive gain")

# Save JSON
with open('experiments/v3-budget-pilot/results/step0_diagnosis.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nFigures saved to {out_dir}")
print("Step 0 diagnosis complete.")