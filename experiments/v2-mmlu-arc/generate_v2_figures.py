#!/usr/bin/env python3
"""Generate figures for experiment v2 report."""
import json, os, warnings
warnings.filterwarnings("ignore")
os.environ['PM4PY_SHOW_WARNINGS'] = '0'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "results")
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

with open(f"{OUTPUT_DIR}/raw_responses_v2.json") as f:
    raw = json.load(f)
with open(f"{OUTPUT_DIR}/traces_final.json") as f:
    traces_data = json.load(f)
with open(f"{OUTPUT_DIR}/conformance_final.json") as f:
    conformance = json.load(f)

models = list(raw.keys())
short_names = {
    'GPT-OSS-20B': 'GPT-OSS\n20B',
    'DeepSeek-V4-Flash-158B': 'DeepSeek-V4\nFlash',
    'GPT-OSS-120B': 'GPT-OSS\n120B',
    'GLM-4.7-357B': 'GLM-4.7\n357B',
    'GLM-5.2-756B': 'GLM-5.2\n756B',
}
colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']

# ---- Figure 1: Accuracy & Token Efficiency ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

accuracies = [sum(1 for r in raw[m] if r['correct'])/len(raw[m])*100 for m in models]
avg_tokens = [sum(r['total_tokens'] for r in raw[m])/len(raw[m]) for m in models]
avg_times = [sum(r['elapsed'] for r in raw[m])/len(raw[m]) for m in models]

x = np.arange(len(models))
width = 0.35

bars1 = ax1.bar(x - width/2, accuracies, width, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax1.set_ylabel('Accuracy (%)', fontsize=12)
ax1.set_title('Model Accuracy', fontsize=13, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([short_names[m] for m in models], fontsize=9)
ax1.set_ylim(0, 110)
ax1.axhline(y=50, color='gray', linestyle='--', alpha=0.3, label='Random (25% for 4-choice)')
ax1.legend(fontsize=8)
for bar, acc in zip(bars1, accuracies):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{acc:.0f}%',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

tokens_per_correct = []
for m in models:
    correct = sum(1 for r in raw[m] if r['correct'])
    total_tokens = sum(r['total_tokens'] for r in raw[m])
    tokens_per_correct.append(total_tokens / correct if correct > 0 else 0)

bars2 = ax2.bar(x, tokens_per_correct, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax2.set_ylabel('Tokens per Correct Answer', fontsize=12)
ax2.set_title('Token Efficiency', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([short_names[m] for m in models], fontsize=9)
for bar, tpc in zip(bars2, tokens_per_correct):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, f'{tpc:.0f}',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig1_accuracy_token_efficiency.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 1 saved")

# ---- Figure 2: Path Structure Metrics ----
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

import statistics
avg_steps = [statistics.mean([t['num_steps'] for t in traces_data[m]]) for m in models]
std_steps = [statistics.stdev([t['num_steps'] for t in traces_data[m]]) for m in models]
loops = [statistics.mean([t['num_loops'] for t in traces_data[m]]) for m in models]
verify_rates = [sum(1 for t in traces_data[m] if t['has_verify'])/len(traces_data[m])*100 for m in models]
variants = [95, 89, 87, 89, 100]  # from discovery
deviations = [conformance[m]['total_deviations'] for m in models]

# Panel A: Steps
ax = axes[0, 0]
bars = ax.bar(x, avg_steps, yerr=std_steps, color=colors, alpha=0.85, capsize=5, edgecolor='black', linewidth=0.5)
ax.set_ylabel('Avg Steps', fontsize=11)
ax.set_title('(A) Reasoning Path Length', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([short_names[m] for m in models], fontsize=8)
for bar, s in zip(bars, avg_steps):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{s:.1f}',
             ha='center', va='bottom', fontsize=9)

# Panel B: Loops
ax = axes[0, 1]
bars = ax.bar(x, loops, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.set_ylabel('Avg Loop Count', fontsize=11)
ax.set_title('(B) Self-Correction Loops', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([short_names[m] for m in models], fontsize=8)
for bar, l in zip(bars, loops):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, f'{l:.2f}',
             ha='center', va='bottom', fontsize=9)

# Panel C: Verify Rate
ax = axes[1, 0]
bars = ax.bar(x, verify_rates, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.set_ylabel('Verify Rate (%)', fontsize=11)
ax.set_title('(C) Verification Behavior', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([short_names[m] for m in models], fontsize=8)
for bar, v in zip(bars, verify_rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{v:.0f}%',
             ha='center', va='bottom', fontsize=9)

# Panel D: Deviations (note GLM-4.7 uses TBR)
ax = axes[1, 1]
dev_colors = colors.copy()
bars = ax.bar(x, deviations, color=dev_colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.set_ylabel('Total Deviations', fontsize=11)
ax.set_title('(D) Conformance Deviations vs Reference', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([short_names[m] for m in models], fontsize=8)
# Mark GLM-4.7 as TBR
for i, m in enumerate(models):
    if conformance[m].get('alignment') == 'timeout':
        bars[i].set_hatch('//')
        bars[i].set_alpha(0.6)
for bar, d in zip(bars, deviations):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30, f'{d}',
             ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig2_path_structure.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 2 saved")

# ---- Figure 3: Activity Distribution ----
fig, ax = plt.subplots(figsize=(12, 6))

activities_order = ['understand', 'recall', 'plan', 'calculate', 'reason', 'evaluate', 'verify', 'reconsider', 'answer']
activity_colors = plt.cm.Set3(np.linspace(0, 1, len(activities_order)))
activity_color_map = dict(zip(activities_order, activity_colors))

bottoms = np.zeros(len(models))
for act in activities_order:
    values = []
    for m in models:
        total = sum(len(t['trace']) for t in traces_data[m])
        count = sum(1 for t in traces_data[m] for a in t['trace'] if a == act)
        values.append(count / total * 100 if total > 0 else 0)
    bars = ax.bar(x, values, bottom=bottoms, color=activity_color_map[act], 
                  edgecolor='white', linewidth=0.3, label=act)
    bottoms += np.array(values)

ax.set_ylabel('Activity Distribution (%)', fontsize=12)
ax.set_title('Reasoning Step Activity Distribution by Model', fontsize=13, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([short_names[m] for m in models], fontsize=9)
ax.legend(loc='upper right', fontsize=8, ncol=3)
ax.set_ylim(0, 100)

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig3_activity_distribution.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 3 saved")

# ---- Figure 4: Calibration (Brier vs Confidence Gap) ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

with open(f"{OUTPUT_DIR}/calibration_final.json") as f:
    calib = json.load(f)

brier_scores = [calib[m]['brier_score'] for m in models]
conf_gaps = [calib[m]['confidence_gap'] for m in models]
avg_confs = [calib[m]['avg_confidence'] for m in models]

# Panel A: Brier Score (lower is better)
bars = ax1.bar(x, brier_scores, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax1.set_ylabel('Brier Score (lower = better)', fontsize=11)
ax1.set_title('(A) Brier Calibration Score', fontsize=12, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([short_names[m] for m in models], fontsize=8)
ax1.axhline(y=0, color='black', linewidth=0.5)
for bar, b in zip(bars, brier_scores):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f'{b:.3f}',
             ha='center', va='bottom', fontsize=9)

# Panel B: Confidence Gap (positive = well-calibrated)
bars = ax2.bar(x, conf_gaps, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
ax2.set_ylabel('Confidence Gap (positive = better)', fontsize=11)
ax2.set_title('(B) Confidence Gap (Correct - Wrong)', fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([short_names[m] for m in models], fontsize=8)
ax2.axhline(y=0, color='black', linewidth=0.5)
for bar, g in zip(bars, conf_gaps):
    y = bar.get_height()
    va = 'bottom' if y >= 0 else 'top'
    offset = 2 if y >= 0 else -2
    ax2.text(bar.get_x() + bar.get_width()/2, y + offset, f'{g:+.1f}',
             ha='center', va=va, fontsize=9)

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig4_calibration.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 4 saved")

# ---- Figure 5: Trace Length Box Plot ----
fig, ax = plt.subplots(figsize=(10, 6))

trace_lengths = [[t['num_steps'] for t in traces_data[m]] for m in models]
bp = ax.boxplot(trace_lengths, labels=[short_names[m] for m in models], 
                patch_artist=True, widths=0.6, showfliers=True,
                medianprops=dict(color='black', linewidth=2))
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.set_ylabel('Trace Length (number of steps)', fontsize=12)
ax.set_title('Reasoning Trace Length Distribution', fontsize=13, fontweight='bold')
ax.set_ylim(0, max(max(tl) for tl in trace_lengths) * 1.1)

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig5_trace_length_box.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 5 saved")

# ---- Figure 6: Token vs Accuracy Scatter ----
fig, ax = plt.subplots(figsize=(10, 7))

for i, m in enumerate(models):
    tokens = [r['total_tokens'] for r in raw[m] if not r.get('error')]
    correct = [r['correct'] for r in raw[m] if not r.get('error')]
    correct_tok = [t for t, c in zip(tokens, correct) if c]
    wrong_tok = [t for t, c in zip(tokens, correct) if not c]
    
    ax.scatter(correct_tok, [1]*len(correct_tok), color=colors[i], alpha=0.5, s=30, label=f'{m} (correct)')
    if wrong_tok:
        ax.scatter(wrong_tok, [0]*len(wrong_tok), color=colors[i], alpha=0.5, s=30, marker='x', label=f'{m} (wrong)')

ax.set_yticks([0, 1])
ax.set_yticklabels(['Wrong', 'Correct'], fontsize=11)
ax.set_xlabel('Total Tokens', fontsize=12)
ax.set_title('Token Usage vs Answer Correctness', fontsize=13, fontweight='bold')
ax.legend(fontsize=7, loc='upper right', ncol=2)

plt.tight_layout()
plt.savefig(f"{FIG_DIR}/fig6_token_vs_accuracy.png", dpi=150, bbox_inches='tight')
plt.close()
print("Figure 6 saved")

print(f"\nAll figures saved to {FIG_DIR}/")
