#!/usr/bin/env python3
"""
Analysis A+C: Entropy-based trace distance + Step type frequency analysis
No reference model needed. Directly compares event logs.

A) Entropy-based log-to-log distance
   - Trace entropy (Shannon entropy of activity distribution per trace)
   - Log-level entropy (normalized trace variant entropy)
   - Pairwise trace edit distance (Levenshtein) → model distance matrix
   
C) Step type frequency analysis (inspired by Berti et al. 2025)
   - Activity frequency distribution per model
   - Transition frequency (bigram) distribution per model
   - Jensen-Shannon divergence between model distributions
"""

import json, math, numpy as np
from collections import Counter, defaultdict
from itertools import combinations
from scipy.stats import entropy as scipy_entropy
from scipy.spatial.distance import jensenshannon
from scipy.cluster.hierarchy import linkage, dendrogram
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

RESULTS_DIR = "experiments/v2-mmlu-arc/results"
FIGURES_DIR = "experiments/v2-mmlu-arc/results/figures"

with open(f"{RESULTS_DIR}/traces_final.json") as f:
    all_traces = json.load(f)

MODELS = list(all_traces.keys())
ALL_ACTIVITIES = sorted(set(a for m in MODELS for t in all_traces[m] for a in t['trace']))
print(f"Models: {MODELS}")
print(f"All activities: {ALL_ACTIVITIES}")

# ============================================================
# A1: Trace-level Shannon entropy (activity distribution per trace)
# ============================================================
def trace_entropy(trace):
    """Shannon entropy of activity distribution in a single trace."""
    if not trace:
        return 0.0
    counts = Counter(trace)
    total = len(trace)
    return -sum((c/total) * math.log2(c/total) for c in counts.values())

print("\n=== A1: Trace Entropy (per-trace activity distribution) ===")
entropy_stats = {}
for m in MODELS:
    entropies = [trace_entropy(t['trace']) for t in all_traces[m]]
    entropy_stats[m] = {
        'mean': np.mean(entropies),
        'std': np.std(entropies),
        'median': np.median(entropies),
        'min': min(entropies),
        'max': max(entropies),
        'per_trace': entropies,
    }
    print(f"  {m}: mean={np.mean(entropies):.3f}, std={np.std(entropies):.3f}, median={np.median(entropies):.3f}")

# ============================================================
# A2: Log-level variant entropy (normalized)
# ============================================================
print("\n=== A2: Log-level Variant Entropy ===")
variant_entropy = {}
for m in MODELS:
    traces = all_traces[m]
    variants = Counter(tuple(t['trace']) for t in traces)
    n = len(traces)
    # Shannon entropy over variant probabilities
    var_ent = -sum((c/n) * math.log2(c/n) for c in variants.values())
    # Normalize by max possible entropy (log2(n))
    norm_ent = var_ent / math.log2(n) if n > 1 else 0
    variant_entropy[m] = {
        'num_variants': len(variants),
        'raw_entropy': var_ent,
        'normalized_entropy': norm_ent,
    }
    print(f"  {m}: {len(variants)} variants, entropy={var_ent:.3f}, normalized={norm_ent:.3f}")

# ============================================================
# A3: Pairwise trace Levenshtein distance → model distance matrix
# ============================================================
print("\n=== A3: Pairwise Model Distance (avg Levenshtein) ===")

def levenshtein(s1, s2):
    """Compute Levenshtein distance between two sequences."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            ins = prev[j+1] + 1
            dele = curr[j] + 1
            sub = prev[j] + (c1 != c2)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]

def avg_pairwise_distance(traces1, traces2, sample_size=50):
    """Average Levenshtein distance between random samples from two models."""
    import random
    random.seed(42)
    t1 = random.sample(traces1, min(sample_size, len(traces1)))
    t2 = random.sample(traces2, min(sample_size, len(traces2)))
    distances = []
    for a in t1:
        for b in t2:
            d = levenshtein(a['trace'], b['trace'])
            # Normalize by max length
            max_len = max(len(a['trace']), len(b['trace']))
            distances.append(d / max_len if max_len > 0 else 0)
    return np.mean(distances), np.std(distances)

# Compute model distance matrix
n_models = len(MODELS)
dist_matrix = np.zeros((n_models, n_models))
dist_std = np.zeros((n_models, n_models))
for i, m1 in enumerate(MODELS):
    for j, m2 in enumerate(MODELS):
        if i == j:
            # Self-distance: average intra-model distance
            avg_d, std_d = avg_pairwise_distance(all_traces[m1], all_traces[m1])
        else:
            avg_d, std_d = avg_pairwise_distance(all_traces[m1], all_traces[m2])
        dist_matrix[i][j] = avg_d
        dist_std[i][j] = std_d
    print(f"  {m1}: " + ", ".join(f"{MODELS[j]}={dist_matrix[i][j]:.3f}" for j in range(n_models)))

# ============================================================
# C1: Step type frequency distribution
# ============================================================
print("\n=== C1: Step Type Frequency Distribution ===")
step_freq = {}
for m in MODELS:
    total_steps = sum(len(t['trace']) for t in all_traces[m])
    activity_counts = Counter()
    for t in all_traces[m]:
        activity_counts.update(t['trace'])
    freq = {a: activity_counts.get(a, 0) / total_steps for a in ALL_ACTIVITIES}
    step_freq[m] = freq
    total_steps_val = total_steps
    print(f"  {m} ({total_steps_val} total steps): " + ", ".join(f"{a}={freq[a]:.3f}" for a in ALL_ACTIVITIES))

# ============================================================
# C2: Jensen-Shannon divergence between models
# ============================================================
print("\n=== C2: Jensen-Shannon Divergence (step type distribution) ===")
jsd_matrix = np.zeros((n_models, n_models))
for i, m1 in enumerate(MODELS):
    for j, m2 in enumerate(MODELS):
        p1 = np.array([step_freq[m1][a] for a in ALL_ACTIVITIES])
        p2 = np.array([step_freq[m2][a] for a in ALL_ACTIVITIES])
        # Add small epsilon to avoid zeros
        p1 = p1 + 1e-10
        p2 = p2 + 1e-10
        p1 = p1 / p1.sum()
        p2 = p2 / p2.sum()
        jsd = jensenshannon(p1, p2, base=2.0)
        jsd_matrix[i][j] = jsd
    print(f"  {m1}: " + ", ".join(f"{MODELS[j]}={jsd_matrix[i][j]:.4f}" for j in range(n_models)))

# ============================================================
# C3: Transition (bigram) frequency distribution
# ============================================================
print("\n=== C3: Transition (Bigram) Frequency ===")
bigram_freq = {}
all_bigrams = set()
for m in MODELS:
    bigram_counts = Counter()
    for t in all_traces[m]:
        for k in range(len(t['trace']) - 1):
            bg = (t['trace'][k], t['trace'][k+1])
            bigram_counts[bg] += 1
            all_bigrams.add(bg)
    total_bg = sum(bigram_counts.values())
    bigram_freq[m] = {bg: bigram_counts.get(bg, 0) / total_bg for bg in all_bigrams}
    
# JSD on bigram distributions
print("\n=== C3b: JSD on Bigram Distribution ===")
all_bigrams_sorted = sorted(all_bigrams)
jsd_bg_matrix = np.zeros((n_models, n_models))
for i, m1 in enumerate(MODELS):
    for j, m2 in enumerate(MODELS):
        p1 = np.array([bigram_freq[m1].get(bg, 0) for bg in all_bigrams_sorted]) + 1e-10
        p2 = np.array([bigram_freq[m2].get(bg, 0) for bg in all_bigrams_sorted]) + 1e-10
        p1 = p1 / p1.sum()
        p2 = p2 / p2.sum()
        jsd = jensenshannon(p1, p2, base=2.0)
        jsd_bg_matrix[i][j] = jsd
    print(f"  {m1}: " + ", ".join(f"{MODELS[j]}={jsd_bg_matrix[i][j]:.4f}" for j in range(n_models)))

# ============================================================
# Generate Visualizations
# ============================================================
print("\n=== Generating Figures ===")

# Fig A: Trace entropy violin plot
fig, ax = plt.subplots(figsize=(10, 6))
data_box = [entropy_stats[m]['per_trace'] for m in MODELS]
parts = ax.violinplot(data_box, positions=range(n_models), showmeans=True, showmedians=True)
for i, m in enumerate(MODELS):
    x = np.random.normal(i, 0.04, size=len(data_box[i]))
    ax.scatter(x, data_box[i], alpha=0.3, s=10, color=f'C{i}')
ax.set_xticks(range(n_models))
ax.set_xticklabels([m.replace('-V4-Flash-158B','').replace('-756B','').replace('-20B','-20B').replace('-120B','-120B') for m in MODELS], rotation=20, ha='right', fontsize=9)
ax.set_ylabel('Shannon Entropy (bits)')
ax.set_title('A1: Per-Trace Activity Entropy Distribution')
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_a1_trace_entropy.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_a1_trace_entropy.png")

# Fig B: Model distance heatmap
fig, ax = plt.subplots(figsize=(8, 7))
short_names = [m.replace('-V4-Flash-158B','').replace('-756B','').replace('-20B','-20B').replace('-120B','-120B') for m in MODELS]
sns.heatmap(dist_matrix, xticklabels=short_names, yticklabels=short_names, 
            annot=True, fmt='.3f', cmap='YlOrRd', ax=ax, square=True)
ax.set_title('A3: Avg Normalized Levenshtein Distance Between Models')
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_a3_levenshtein_heatmap.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_a3_levenshtein_heatmap.png")

# Fig C: Step type frequency stacked bar
fig, ax = plt.subplots(figsize=(12, 7))
colors = plt.cm.Set3(np.linspace(0, 1, len(ALL_ACTIVITIES)))
bottoms = np.zeros(n_models)
for i, activity in enumerate(ALL_ACTIVITIES):
    vals = [step_freq[m][activity] for m in MODELS]
    ax.bar(range(n_models), vals, bottom=bottoms, label=activity, color=colors[i], edgecolor='white', linewidth=0.5)
    bottoms += np.array(vals)
ax.set_xticks(range(n_models))
ax.set_xticklabels(short_names, rotation=20, ha='right', fontsize=9)
ax.set_ylabel('Frequency')
ax.set_title('C1: Step Type Frequency Distribution')
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_c1_step_frequency.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_c1_step_frequency.png")

# Fig D: JSD heatmaps (side by side: step type + bigram)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
sns.heatmap(jsd_matrix, xticklabels=short_names, yticklabels=short_names,
            annot=True, fmt='.4f', cmap='Blues', ax=ax1, square=True)
ax1.set_title('C2: JSD - Step Type Distribution')
sns.heatmap(jsd_bg_matrix, xticklabels=short_names, yticklabels=short_names,
            annot=True, fmt='.4f', cmap='Greens', ax=ax2, square=True)
ax2.set_title('C3b: JSD - Bigram Distribution')
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_c2_c3_jsd_heatmaps.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_c2_c3_jsd_heatmaps.png")

# Fig E: Hierarchical clustering from distance matrix
fig, ax = plt.subplots(figsize=(10, 7))
condensed = []
for i in range(n_models):
    for j in range(i+1, n_models):
        condensed.append(dist_matrix[i][j])
Z = linkage(condensed, method='average')
dendrogram(Z, labels=short_names, ax=ax, leaf_rotation=20)
ax.set_title('A3b: Hierarchical Clustering of Models (Levenshtein Distance)')
ax.set_ylabel('Average Normalized Levenshtein Distance')
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_a3b_dendrogram.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_a3b_dendrogram.png")

# Fig F: Transition bigram top-10 comparison
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
axes = axes.flatten()
for idx, m in enumerate(MODELS):
    bg_counts = Counter()
    for t in all_traces[m]:
        for k in range(len(t['trace']) - 1):
            bg_counts[(t['trace'][k], t['trace'][k+1])] += 1
    top = bg_counts.most_common(10)
    labels = [f"{a}→{b}" for (a,b),_ in top]
    vals = [c for _, c in top]
    axes[idx].barh(range(len(top)), vals, color=f'C{idx}')
    axes[idx].set_yticks(range(len(top)))
    axes[idx].set_yticklabels(labels, fontsize=8)
    axes[idx].invert_yaxis()
    axes[idx].set_xlabel('Count')
    axes[idx].set_title(short_names[idx])
fig.suptitle('C3c: Top-10 Transitions per Model', fontsize=14, y=1.01)
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}/fig_c3c_top_transitions.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved fig_c3c_top_transitions.png")

# ============================================================
# Save all results
# ============================================================
results = {
    'A1_trace_entropy': {m: {k: v for k, v in stats.items() if k != 'per_trace'} for m, stats in entropy_stats.items()},
    'A2_variant_entropy': variant_entropy,
    'A3_levenshtein_distance': {
        'matrix': dist_matrix.tolist(),
        'std_matrix': dist_std.tolist(),
        'models': MODELS,
    },
    'C1_step_frequency': step_freq,
    'C2_jsd_step_type': {
        'matrix': jsd_matrix.tolist(),
        'models': MODELS,
    },
    'C3_jsd_bigram': {
        'matrix': jsd_bg_matrix.tolist(),
        'models': MODELS,
        'all_bigrams': [list(bg) for bg in all_bigrams_sorted],
    },
}

with open(f"{RESULTS_DIR}/entropy_step_analysis.json", 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to {RESULTS_DIR}/entropy_step_analysis.json")
print("\nDone!")