"""Pure utility functions shared by V2 analysis scripts."""

from __future__ import annotations

import random


def token_count(value):
    """Normalize PM4Py token diagnostics across supported result shapes."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        return sum(int(count) for count in value.values() if isinstance(count, (int, float)))
    return 0


def move_label(move_side):
    """Return the activity/skip label from simple or transition-aware alignment moves."""
    if isinstance(move_side, (tuple, list)) and move_side:
        return move_side[-1]
    return move_side


def count_alignment_deviations(aligned_traces):
    """Count log/model moves; synchronous moves are not deviations."""
    deviations = 0
    for aligned_trace in aligned_traces:
        for move in aligned_trace.get("alignment", []):
            if not isinstance(move, (tuple, list)) or len(move) != 2:
                continue
            log_label = move_label(move[0])
            model_label = move_label(move[1])
            if (log_label == ">>") != (model_label == ">>"):
                deviations += 1
    return deviations


def levenshtein(sequence_1, sequence_2):
    """Compute Levenshtein distance between two sequences."""
    if len(sequence_1) < len(sequence_2):
        return levenshtein(sequence_2, sequence_1)
    if len(sequence_2) == 0:
        return len(sequence_1)
    previous = list(range(len(sequence_2) + 1))
    for index_1, item_1 in enumerate(sequence_1):
        current = [index_1 + 1]
        for index_2, item_2 in enumerate(sequence_2):
            insertion = previous[index_2 + 1] + 1
            deletion = current[index_2] + 1
            substitution = previous[index_2] + (item_1 != item_2)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def avg_pairwise_distance(traces_1, traces_2, sample_size=50, seed=42):
    """Average normalized Levenshtein distance between deterministic trace samples."""
    def sample(traces):
        population = list(traces)
        signature = "\x1f".join(
            sorted(str(trace.get("case_id", trace.get("trace", ""))) for trace in population)
        )
        rng = random.Random(f"{seed}:{signature}")
        return rng.sample(population, min(sample_size, len(population)))

    sample_1 = sample(traces_1)
    sample_2 = sample(traces_2)
    distances = []
    for trace_1 in sample_1:
        for trace_2 in sample_2:
            sequence_1 = trace_1["trace"]
            sequence_2 = trace_2["trace"]
            max_length = max(len(sequence_1), len(sequence_2))
            distance = levenshtein(sequence_1, sequence_2)
            distances.append(distance / max_length if max_length > 0 else 0)
    if not distances:
        return 0.0, 0.0
    mean = sum(distances) / len(distances)
    variance = sum((distance - mean) ** 2 for distance in distances) / len(distances)
    return mean, variance**0.5
