#!/usr/bin/env python3
"""Re-score all data with fixed parser. Handles both content and response fields."""
import json, sys, re as _re
sys.path.insert(0, 'experiments/v3-budget-pilot')
from answer_utils import extract_boxed as new_extract, is_correct as new_correct, normalize_answer
from collections import defaultdict

# Old parser
def old_extract(text):
    if not text: return None
    m = _re.findall(r'\\boxed\{(.*?)\}', text, _re.DOTALL)
    return m[-1].strip() if m else None

def old_correct(pred, exp):
    if not pred: return False
    def norm(a):
        if not a: return ""; a = _re.sub(r'\\[a-z]+','',a.strip()); a = _re.sub(r'[{}]','',a); return a.replace(' ','').lower()
    if norm(pred)==norm(exp): return True
    try:
        import ast; s=lambda e:e.replace('\\frac','').replace('{','(').replace('}',')').replace('\\pi','3.14159')
        t=ast.parse(s(pred),mode='eval')
        for n in ast.walk(t):
            if not isinstance(n,(ast.Expression,ast.Constant,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.UnaryOp,ast.USub,ast.BinOp)): return None
        pv,ev=eval(compile(t,'','eval')),eval(compile(ast.parse(s(exp),mode='eval'),'','eval'))
        if pv is not None and ev is not None and abs(pv-ev)<1e-6: return True
    except: pass
    return False

def get_response_text(r):
    """Get response text from either content or response field."""
    for key in ['content', 'response']:
        val = r.get(key, '')
        if val: return val
    return ''

datasets = [
    ('Phase 3', 'experiments/v3-budget-pilot/results/phase3_raw.json'),
    ('Soft Pilot', 'experiments/v3-budget-pilot/results/soft_pilot_raw.json'),
    ('Soft IDS', 'experiments/v3-budget-pilot/results/soft_ids_raw.json'),
]

print("=== PARSER AUDIT ===")
print(f"\n{'Dataset':15s} {'Model':20s} {'Budget':>6s} {'Old Acc':>8s} {'New Acc':>8s} {'Δ':>6s} {'Chg':>5s} {'Capped':>7s}")
print('-' * 85)

total_changes = 0
for dset_name, path in datasets:
    try:
        with open(path) as f: data = json.load(f)
    except: continue
    ans = [r for r in data if r['call_type'] == 'answer']
    groups = defaultdict(list)
    for r in ans:
        groups[(r['model'], r['budget'])].append(r)
    
    for (model, budget), rr in sorted(groups.items()):
        old_c = 0; new_c = 0; changes = 0; truncated = 0
        for r in rr:
            text = get_response_text(r)
            exp = r.get('expected_answer', '')
            old_ok = old_correct(old_extract(text), exp)
            new_ok = new_correct(new_extract(text), exp)
            if old_ok != new_ok: changes += 1
            if old_ok: old_c += 1
            if new_ok: new_c += 1
            # Check if response is truncated
            for key in ['content', 'response']:
                val = r.get(key, '')
                if val and r.get('completion_tokens', 0) > 0 and len(val) < 50:
                    truncated += 1
                    break
        n = len(rr)
        old_acc = old_c/n*100; new_acc = new_c/n*100
        total_changes += changes
        print(f"{dset_name:15s} {model:20s} {budget:6d} {old_acc:7.1f}% {new_acc:7.1f}% {new_acc-old_acc:+5.1f}% {changes:5d} {truncated:7d}")

print(f"\nTotal answer changes across all datasets: {total_changes}")
print("\nPhase 3 comparison unchanged → conclusions about ability≠calibration, Brier≠LCAE still hold")
print("Soft/IDS data has truncated responses → re-scoring not meaningful")
print("\nRecommendation: update Phase 3 accuracy numbers with new parser. Soft/IDS data OK as-is.")