#!/usr/bin/env python3
"""Deterministic event extraction for the process-allocation proof of concept.

Only observable response text is used.  The module intentionally avoids API calls
and model-generated labels so that the first PoC is cheap and reproducible.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence


ACTIVITIES = (
    "understand_setup",
    "recall",
    "plan",
    "calculate",
    "reason",
    "verify",
    "backtrack",
    "conclude",
    "other",
)


@dataclass(frozen=True)
class Event:
    index: int
    activity: str
    text: str


def segment_trace(text: str) -> list[str]:
    """Split an observable response into coarse reasoning segments.

    Display-math blocks and paragraphs are preserved when possible.  Very short
    fragments are joined to the following segment to reduce punctuation noise.
    """
    if not text or not text.strip():
        return []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", normalized)
    segments: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if "\\[" in block or "\\begin{" in block or len(block) <= 240:
            pieces = [block]
        else:
            pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\\])", block)
        for piece in pieces:
            piece = re.sub(r"\s+", " ", piece).strip()
            if not piece:
                continue
            if segments and len(piece) < 8:
                segments[-1] = f"{segments[-1]} {piece}".strip()
            else:
                segments.append(piece)
    return segments


def label_segment(text: str) -> str:
    """Assign one mutually exclusive activity using ordered transparent rules."""
    value = text.lower()
    if re.search(r"\\boxed\s*\{|final answer|the answer is|therefore.{0,50}answer", value):
        return "conclude"
    if re.search(
        r"\b(check|verify|validate|confirm|double[- ]check|sanity check|ensure)\b",
        value,
    ):
        return "verify"
    if re.search(
        r"\b(wait|reconsider|actually|instead|alternative|backtrack|try again|"
        r"this (?:is|was) wrong|cannot be|contradiction)\b",
        value,
    ):
        return "backtrack"
    if re.search(r"\b(plan|strategy|approach|we will|first,? we need|goal is to)\b", value):
        return "plan"
    if re.search(
        r"\b(recall|by (?:the|a) theorem|formula|definition|identity|property|rule)\b",
        value,
    ):
        return "recall"
    if re.search(
        r"\b(let|given|suppose|assume|define|denote|we have|we know|consider)\b",
        value,
    ):
        return "understand_setup"
    if re.search(
        r"(?:=|\\frac|\\sqrt|\bcompute\b|\bcalculate\b|\bsolve\b|\bsimplif|"
        r"\bexpand\b|\bsubstitut|\bmultiply\b|\bdivide\b)",
        value,
    ):
        return "calculate"
    if re.search(
        r"\b(therefore|thus|hence|because|implies|so that|consequently|which means)\b",
        value,
    ):
        return "reason"
    return "other"


def extract_events(text: str) -> list[Event]:
    return [
        Event(index=index, activity=label_segment(segment), text=segment)
        for index, segment in enumerate(segment_trace(text))
    ]


def activity_sequence(events_or_text: Sequence[Event] | str) -> list[str]:
    events = extract_events(events_or_text) if isinstance(events_or_text, str) else events_or_text
    return [event.activity for event in events]


def _entropy(values: Iterable[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if not total:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def base_process_features(events_or_text: Sequence[Event] | str) -> dict[str, float]:
    events = extract_events(events_or_text) if isinstance(events_or_text, str) else events_or_text
    sequence = activity_sequence(events)
    counts = Counter(sequence)
    features: dict[str, float] = {
        "process_step_count": float(len(sequence)),
        "process_unique_activities": float(len(counts)),
        "process_activity_entropy": _entropy(sequence),
        "process_transition_count": float(max(0, len(sequence) - 1)),
        "process_loop_count": float(
            sum(1 for left, right in zip(sequence, sequence[1:]) if left == right)
        ),
        "process_has_verify": float("verify" in counts),
        "process_has_backtrack": float("backtrack" in counts),
        "process_has_conclude": float("conclude" in counts),
    }
    denominator = max(1, len(sequence))
    for activity in ACTIVITIES:
        features[f"process_count_{activity}"] = float(counts[activity])
        features[f"process_share_{activity}"] = counts[activity] / denominator
        features[f"process_last_{activity}"] = float(bool(sequence and sequence[-1] == activity))
    transition_counts = Counter(zip(sequence, sequence[1:]))
    for (left, right), count in sorted(transition_counts.items()):
        features[f"transition::{left}->{right}"] = float(count)
    return features


@dataclass
class DFGModel:
    counts: dict[str, Counter[str]]
    totals: Counter[str]
    vocabulary_size: int
    alpha: float = 1.0

    def score(self, sequence: Sequence[str], prefix: str) -> dict[str, float]:
        transitions = list(zip(sequence, sequence[1:]))
        if not transitions:
            return {
                f"{prefix}_mean_log_probability": 0.0,
                f"{prefix}_unseen_transition_share": 0.0,
            }
        log_probabilities = []
        unseen = 0
        for left, right in transitions:
            count = self.counts.get(left, Counter())[right]
            total = self.totals[left]
            probability = (count + self.alpha) / (
                total + self.alpha * self.vocabulary_size
            )
            log_probabilities.append(math.log(probability))
            unseen += int(count == 0)
        return {
            f"{prefix}_mean_log_probability": sum(log_probabilities) / len(transitions),
            f"{prefix}_unseen_transition_share": unseen / len(transitions),
        }


def fit_dfg(sequences: Iterable[Sequence[str]], alpha: float = 1.0) -> DFGModel:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for sequence in sequences:
        for left, right in zip(sequence, sequence[1:]):
            counts[left][right] += 1
            totals[left] += 1
    return DFGModel(
        counts=dict(counts),
        totals=totals,
        vocabulary_size=len(ACTIVITIES),
        alpha=alpha,
    )


def dfg_conformance_features(
    sequence: Sequence[str],
    all_model: DFGModel,
    benefit_model: DFGModel,
    no_benefit_model: DFGModel,
) -> dict[str, float]:
    features = {}
    features.update(all_model.score(sequence, "dfg_all"))
    features.update(benefit_model.score(sequence, "dfg_benefit"))
    features.update(no_benefit_model.score(sequence, "dfg_no_benefit"))
    features["dfg_benefit_logp_advantage"] = (
        features["dfg_benefit_mean_log_probability"]
        - features["dfg_no_benefit_mean_log_probability"]
    )
    return features
