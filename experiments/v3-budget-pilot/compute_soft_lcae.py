#!/usr/bin/env python3
"""Compute LCAE on Soft Pilot and Soft IDS data using Phase 3 IRT parameters (free)."""
import json, math
from collections import defaultdict

def logist(x):
    if x > 20: return 1.0
    if x < -20: return 0.0
    return 1.0 / (1.0 + math.exp(-x))

# Load Phase 3 IRT params
with open('experiments/v3-budget-pilot/results/irt_phase3.json') as f:
    irt = json.load(f)
theta = irt['theta']
beta = {k: float(v) for k, v in irt['beta'].items()}
items = irt['items']

# Load soft data
with open('experiments/v3-budget-pilot/results/soft_pilot_raw.json') as f:
    soft_qoq = json.load(f)
with open('experiments/v3-budget-pilot/results/soft_ids_raw.json') as f:
    soft_ids = json.load(f)

models = ['GPT-OSS-120B', 'DeepSeek-V4-Flash-158B']
datasets = [('Soft QOQ', soft_qoq), ('Soft IDS', soft_ids)]

print("=" * 75)
print("LCAE ON SOFT DATA (using Phase 3 IRT parameters)")
print("=" * 75)

for dset_name, data in datasets:
    conf_calls = [r for r in data if r['call_type'] == 'confidence']
    print(f"\n--- {dset_name} ---")
    print(f"{'Model':25s} {'Budget':>6s} {'LCAE':>8s} {'N':>5s} {'AvgConf':>8s} {'Acc':>8s} {'Brier':>8s}")
    print('-' * 75)
    
    for model in models:
        for budget in [256, 512]:
            mc = [r for r in conf_calls if r['model'] == model and r['budget'] == budget]
            ans = [r for r in data if r['call_type'] == 'answer' and r['model'] == model and r['budget'] == budget]
            
            if not ans: continue
            acc = sum(1 for r in ans if r['correct']) / len(ans)
            
            # LCAE
            diffs = []
            for r in mc:
                qid = r['question_id']
                if qid in beta and r['confidence_value'] is not None:
                    pe = 1.0 - logist(theta.get(model, 0) - beta.get(qid, 0))
                    ce = 1.0 - (r['confidence_value'] / 100.0)
                    pe = max(0.0, min(1.0, pe))
                    ce = max(0.0, min(1.0, ce))
                    diffs.append((ce - pe) ** 2)
            
            lcae = sum(diffs) / len(diffs) if diffs else 0
            
            # Brier
            conf_vals = [(r['confidence_value'], r.get('correct')) for r in mc if r['confidence_value'] is not None]
            brier = sum((v/100.0 - (1 if ok else 0))**2 for v, ok in conf_vals) / len(conf_vals) if conf_vals else 0
            
            avg_conf = sum(v for v, _ in conf_vals) / len(conf_vals) if conf_vals else 0
            
            print(f"{model:25s} {budget:6d} {lcae:.4f} {len(diffs):5d} {avg_conf:7.1f}% {acc*100:7.1f}% {brier:.4f}")

# Compare with Hard LCAE
print("\n" + "=" * 75)
print("HARD vs SOFT LCAE COMPARISON")
print("=" * 75)
print(f"{'Model':25s} {'Condition':>12s} {'256 LCAE':>10s} {'512 LCAE':>10s}")
print('-' * 75)

for model in models:
    # Hard LCAE from Phase 3
    h_lcae = irt.get('lcae', {}).get(model, 0)
    print(f"{model:25s} {'Hard':>12s} {'—':>10s} {h_lcae:.4f}")
    
    for dset_name, data in datasets:
        conf_calls = [r for r in data if r['call_type'] == 'confidence']
        for budget in [256, 512]:
            mc = [r for r in conf_calls if r['model'] == model and r['budget'] == budget]
            diffs = []
            for r in mc:
                qid = r['question_id']
                if qid in beta and r['confidence_value'] is not None:
                    pe = 1.0 - logist(theta.get(model, 0) - beta.get(qid, 0))
                    ce = 1.0 - (r['confidence_value'] / 100.0)
                    diffs.append((max(0,min(1,pe)) - max(0,min(1,ce))) ** 2)
            lcae = sum(diffs) / len(diffs) if diffs else 0
            label = f"{dset_name} @ {budget}"
            print(f"{'':25s} {label:>12s} {lcae:.4f}")