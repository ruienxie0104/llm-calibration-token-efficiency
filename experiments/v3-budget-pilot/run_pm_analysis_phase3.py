#!/usr/bin/env python3
"""PM analysis: compare activity sequences at different budgets."""
import json, re
from collections import Counter, defaultdict
from pathlib import Path

p = Path("experiments/v3-budget-pilot/results/phase3_raw.json")
with open(p) as f:
    data = json.load(f)

ans = [r for r in data if r["call_type"] == "answer"]

# Activity labeling (simplified keyword-based, same as V2)
def label_step(text):
    text_lower = text.lower()
    if re.search(r'\\boxed\{', text): return "answer"
    if re.search(r'answer|the answer is|thus.*=.*\\boxed|final answer', text_lower): return "answer"
    if re.search(r'verify|check|confirm|validate|double.check|ensure', text_lower): return "verify"
    if re.search(r'reconsider|wait|actually|alternative|rethink|but.*not|let me re', text_lower): return "reconsider"
    if re.search(r'compute|calculate|solve|evaluate|simplify|expand|multiply|divide|add|subtract|equals|=', text_lower): return "calculate"
    if re.search(r'recall|remember|formula|definition|rule|property|theorem', text_lower): return "recall"
    if re.search(r'understand|given|we know|we have|let.*be|suppose|define|consider|assume|setup', text_lower): return "understand"
    if re.search(r'plan|strategy|approach|way to|how to|first.*will|step.*plan', text_lower): return "plan"
    if re.search(r'evaluate|compare|choice|option|which is better|alternatively', text_lower): return "evaluate"
    return "reason"

print("=== PM 分析：低預算 vs 高預算的活動頻率 ===")
print()

models = ["GPT-OSS-20B", "GPT-OSS-120B", "DeepSeek-V4-Flash-158B", "GLM-5.2-756B"]
activities = ["understand", "recall", "plan", "calculate", "reason", "evaluate", "verify", "reconsider", "answer"]

for model in models:
    print(f"\n--- {model} ---")
    for budget in [256, 1024]:
        rr = [r for r in ans if r["model"] == model and r["budget"] == budget]
        all_acts = []
        for r in rr:
            content = r.get("content", "")
            # Segment by double newlines or sentence boundaries
            segments = re.split(r'\n\n+|\.\s*', content)
            for seg in segments:
                if len(seg.strip()) > 5:
                    label = label_step(seg)
                    all_acts.append(label)
        total = len(all_acts)
        if total == 0: continue
        counts = Counter(all_acts)
        print(f"\n  Budget {budget} (total steps: {total}, n={len(rr)}):")
        for act in activities:
            pct = counts.get(act, 0) / total * 100
            bar = "█" * max(1, int(pct / 2))
            print(f"    {act:15s}: {pct:5.1f}% {bar}")

    # Activity diversity (entropy)
    print()
    for budget in [256, 1024]:
        rr = [r for r in ans if r["model"] == model and r["budget"] == budget]
        all_acts = []
        for r in rr:
            content = r.get("content", "")
            segments = re.split(r'\n\n+|\.\s*', content)
            for seg in segments:
                if len(seg.strip()) > 5:
                    all_acts.append(label_step(seg))
        total = len(all_acts)
        if total == 0: continue
        counts = Counter(all_acts)
        import math
        entropy = -sum((c/total) * math.log2(c/total) for c in counts.values())
        print(f"  {model} @ {budget}: entropy={entropy:.2f} bits, unique_acts={len(counts)}")