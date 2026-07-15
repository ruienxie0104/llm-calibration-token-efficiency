#!/usr/bin/env python3
"""Generate visualization charts for the pilot report."""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# Color scheme
COLORS = {
    'primary': '#1B3A5C',
    'accent': '#2E8B8B',
    'highlight': '#C8553D',
    'light': '#E8ECEF',
    'gray': '#6B7280',
}

MODEL_COLORS = {
    'GPT-OSS-20B': '#4A90D9',
    'DeepSeek-V4-Flash-158B': '#2E8B8B',
    'GPT-OSS-120B': '#5B9BD5',
    'GLM-4.7-357B': '#C8553D',
    'GLM-5.2-756B': '#1B3A5C',
}

MODELS_ORDER = ['GPT-OSS-20B', 'DeepSeek-V4-Flash-158B', 'GPT-OSS-120B', 'GLM-4.7-357B', 'GLM-5.2-756B']
MODEL_LABELS = ['GPT-OSS\n20B', 'DeepSeek-V4\nFlash 158B', 'GPT-OSS\n120B', 'GLM-4.7\n357B', 'GLM-5.2\n756B']

OUTPUT_DIR = "pilot_real_results/figures"
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load data
with open('pilot_real_results/raw_responses.json') as f:
    raw = json.load(f)
with open('pilot_real_results/traces.json') as f:
    traces = json.load(f)
with open('pilot_real_results/conformance.json') as f:
    conformance = json.load(f)

metrics_df = pd.read_csv('pilot_real_results/path_quality_metrics.csv')

# ============================================================
# Figure 1: Accuracy & Token Efficiency
# ============================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Accuracy
acc_values = []
tok_per_correct = []
for m in MODELS_ORDER:
    responses = raw[m]
    correct = sum(1 for r in responses if r['correct'])
    acc_values.append(correct / 20 * 100)
    total_tok = sum(r.get('total_tokens', 0) for r in responses)
    tok_per_correct.append(total_tok / correct if correct > 0 else 0)

bars1 = ax1.bar(range(5), acc_values, color=[MODEL_COLORS[m] for m in MODELS_ORDER], edgecolor='white', linewidth=0.5)
ax1.set_xticks(range(5))
ax1.set_xticklabels(MODEL_LABELS, fontsize=9)
ax1.set_ylabel('Accuracy (%)', fontsize=11)
ax1.set_title('Accuracy by Model', fontsize=13, color=COLORS['primary'], fontweight='bold')
ax1.set_ylim(80, 105)
ax1.axhline(y=100, color=COLORS['gray'], linestyle='--', alpha=0.3)
for bar, val in zip(bars1, acc_values):
    ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5, 
             f'{val:.0f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

# Token efficiency
bars2 = ax2.bar(range(5), tok_per_correct, color=[MODEL_COLORS[m] for m in MODELS_ORDER], edgecolor='white', linewidth=0.5)
ax2.set_xticks(range(5))
ax2.set_xticklabels(MODEL_LABELS, fontsize=9)
ax2.set_ylabel('Tokens per Correct Answer', fontsize=11)
ax2.set_title('Token Efficiency (Lower = Better)', fontsize=13, color=COLORS['primary'], fontweight='bold')
for bar, val in zip(bars2, tok_per_correct):
    ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 10, 
             f'{val:.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig1_accuracy_token_efficiency.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig1")

# ============================================================
# Figure 2: Reasoning Path Structure (Steps, Variants, Deviations)
# ============================================================

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Avg Steps
steps = [sum(t['num_steps'] for t in traces[m])/len(traces[m]) for m in MODELS_ORDER]
step_stds = [np.std([t['num_steps'] for t in traces[m]]) for m in MODELS_ORDER]
bars = axes[0].bar(range(5), steps, yerr=step_stds, color=[MODEL_COLORS[m] for m in MODELS_ORDER], 
                    edgecolor='white', linewidth=0.5, capsize=3)
axes[0].set_xticks(range(5))
axes[0].set_xticklabels(MODEL_LABELS, fontsize=9)
axes[0].set_ylabel('Average Steps', fontsize=11)
axes[0].set_title('Reasoning Path Length', fontsize=13, color=COLORS['primary'], fontweight='bold')
for bar, val in zip(bars, steps):
    axes[0].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, 
                 f'{val:.1f}', ha='center', va='bottom', fontsize=10)

# Variants
variants = []
for m in MODELS_ORDER:
    from collections import Counter
    patterns = Counter(tuple(t['trace']) for t in traces[m])
    variants.append(len(patterns))
bars = axes[1].bar(range(5), variants, color=[MODEL_COLORS[m] for m in MODELS_ORDER], 
                    edgecolor='white', linewidth=0.5)
axes[1].set_xticks(range(5))
axes[1].set_xticklabels(MODEL_LABELS, fontsize=9)
axes[1].set_ylabel('Number of Variants', fontsize=11)
axes[1].set_title('Path Diversity (Unique Trace Patterns)', fontsize=13, color=COLORS['primary'], fontweight='bold')
for bar, val in zip(bars, variants):
    axes[1].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.3, 
                 f'{val}', ha='center', va='bottom', fontsize=10)

# Deviations
devs = []
for m in MODELS_ORDER:
    d = conformance.get(m, {})
    devs.append(d.get('total_deviations', 0) if d.get('total_deviations') else 0)
bars = axes[2].bar(range(5), devs, color=[MODEL_COLORS[m] for m in MODELS_ORDER], 
                    edgecolor='white', linewidth=0.5)
axes[2].set_xticks(range(5))
axes[2].set_xticklabels(MODEL_LABELS, fontsize=9)
axes[2].set_ylabel('Total Deviations', fontsize=11)
axes[2].set_title('Conformance Deviations (vs Best Model)', fontsize=13, color=COLORS['primary'], fontweight='bold')
for bar, val in zip(bars, devs):
    axes[2].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 10, 
                 f'{val}', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig2_path_structure.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig2")

# ============================================================
# Figure 3: Activity Distribution (Stacked Bar)
# ============================================================

fig, ax = plt.subplots(figsize=(12, 6))

# Get activity distribution per model
all_activities = set()
for m in MODELS_ORDER:
    for t in traces[m]:
        all_activities.update(t['trace'])
all_activities = sorted(all_activities)

activity_colors = {
    'understand': '#4A90D9',
    'recall': '#7B68EE',
    'plan': '#9370DB',
    'calculate': '#2E8B8B',
    'reason': '#F4A460',
    'verify': '#32CD32',
    'reconsider': '#C8553D',
    'answer': '#1B3A5C',
}

bottoms = np.zeros(5)
for act in all_activities:
    values = []
    for m in MODELS_ORDER:
        count = sum(t['trace'].count(act) for t in traces[m])
        total = sum(len(t['trace']) for t in traces[m])
        values.append(count / total * 100 if total > 0 else 0)
    
    bars = ax.barh(range(5), values, left=bottoms, 
                   color=activity_colors.get(act, '#888888'), label=act, edgecolor='white', linewidth=0.3)
    bottoms += np.array(values)

ax.set_yticks(range(5))
ax.set_yticklabels([m.replace('-', '\n') for m in MODELS_ORDER], fontsize=9)
ax.set_xlabel('Activity Distribution (%)', fontsize=11)
ax.set_title('Reasoning Activity Composition by Model', fontsize=13, color=COLORS['primary'], fontweight='bold')
ax.legend(loc='upper right', bbox_to_anchor=(1.12, 1.0), fontsize=9)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig3_activity_distribution.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig3")

# ============================================================
# Figure 4: Token vs Accuracy Scatter
# ============================================================

fig, ax = plt.subplots(figsize=(10, 7))

for i, m in enumerate(MODELS_ORDER):
    responses = raw[m]
    correct = sum(1 for r in responses if r['correct'])
    avg_tok = sum(r.get('total_tokens', 0) for r in responses) / len(responses)
    acc = correct / 20 * 100
    
    ax.scatter(avg_tok, acc, s=200, c=MODEL_COLORS[m], edgecolors='white', linewidth=2, zorder=5)
    ax.annotate(m, (avg_tok, acc), textcoords="offset points", xytext=(10, 5), 
                fontsize=9, fontweight='bold')
    
    # Individual questions as small dots
    for r in responses:
        r_acc = 100 if r['correct'] else 0
        ax.scatter(r.get('total_tokens', 0), r_acc + np.random.uniform(-1.5, 1.5), 
                   c=MODEL_COLORS[m], alpha=0.15, s=15)

ax.set_xlabel('Total Tokens (per question)', fontsize=12)
ax.set_ylabel('Accuracy (%)', fontsize=12)
ax.set_title('Token Usage vs Accuracy', fontsize=14, color=COLORS['primary'], fontweight='bold')
ax.set_ylim(85, 102)
ax.axhline(y=95, color=COLORS['gray'], linestyle='--', alpha=0.3)
ax.axhline(y=100, color=COLORS['gray'], linestyle='--', alpha=0.3)
ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig4_token_vs_accuracy.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig4")

# ============================================================
# Figure 5: Trace Length Distribution (Box Plot)
# ============================================================

fig, ax = plt.subplots(figsize=(10, 6))

data_box = [[t['num_steps'] for t in traces[m]] for m in MODELS_ORDER]
bp = ax.boxplot(data_box, labels=MODEL_LABELS, patch_artist=True, widths=0.6,
                medianprops=dict(color='white', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='#C8553D', markersize=5))

for patch, m in zip(bp['boxes'], MODELS_ORDER):
    patch.set_facecolor(MODEL_COLORS[m])
    patch.set_alpha(0.8)

ax.set_ylabel('Number of Steps', fontsize=12)
ax.set_title('Reasoning Trace Length Distribution', fontsize=14, color=COLORS['primary'], fontweight='bold')
ax.grid(True, alpha=0.2, axis='y')

# Add mean markers
for i, m in enumerate(MODELS_ORDER):
    mean_val = np.mean([t['num_steps'] for t in traces[m]])
    ax.scatter(i+1, mean_val, marker='D', color='white', s=30, zorder=5, edgecolors=COLORS['primary'])

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig5_trace_length_box.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig5")

# ============================================================
# Figure 6: Overthinking Case Study (GLM-5.2 Q3)
# ============================================================

fig, ax = plt.subplots(figsize=(10, 6))

# Show step count vs correctness for GLM-5.2
glm52 = traces['GLM-5.2-756B']
glm52_steps = [t['num_steps'] for t in glm52]
glm52_correct = [t['correct'] for t in glm52]
glm52_tok = [t['total_tokens'] for t in glm52]

colors_point = [COLORS['accent'] if c else COLORS['highlight'] for c in glm52_correct]
ax.scatter(range(1, 21), glm52_steps, c=colors_point, s=100, edgecolors='white', linewidth=1.5, zorder=5)
ax.set_xlabel('Question ID', fontsize=12)
ax.set_ylabel('Number of Steps', fontsize=12)
ax.set_title('GLM-5.2: Steps per Question (Red = Wrong Answer)', fontsize=13, color=COLORS['primary'], fontweight='bold')
ax.set_xticks(range(1, 21))
ax.axhline(y=np.mean(glm52_steps), color=COLORS['gray'], linestyle='--', alpha=0.3, label=f'Mean = {np.mean(glm52_steps):.1f}')
ax.legend(fontsize=10)

# Annotate Q3
ax.annotate('Q3: 55 steps, 5572 tokens\n(Overthinking)', 
            xy=(3, 55), xytext=(7, 50),
            arrowprops=dict(arrowstyle='->', color=COLORS['highlight']),
            fontsize=9, color=COLORS['highlight'], fontweight='bold')

ax.grid(True, alpha=0.2, axis='y')
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig6_overthinking_case.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved fig6")

print("\nAll figures saved to", OUTPUT_DIR)