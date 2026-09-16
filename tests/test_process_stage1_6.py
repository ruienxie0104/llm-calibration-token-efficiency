import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).parents[1] / "experiments" / "v3-budget-pilot"
sys.path.insert(0, str(SCRIPT_DIR))
MODULE_PATH = SCRIPT_DIR / "analyze_process_confidence_stage1_6.py"
SPEC = importlib.util.spec_from_file_location("analyze_process_confidence_stage1_6", MODULE_PATH)
stage1_6 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = stage1_6
SPEC.loader.exec_module(stage1_6)


def minimal_record(**updates):
    record = {
        "case_id": "model|question|1",
        "question_id": "question",
        "model": "model",
        "replicate": 1,
        "level": 3,
        "subject": "algebra",
        "question_chars": 100,
        "low_budget": 512,
        "high_budget": 1024,
        "low_completion_tokens": 500,
        "high_completion_tokens": 700,
        "incremental_token_proxy": 200,
        "low_near_cap": 0,
        "low_correct": 0,
        "high_correct": 1,
        "gain": 1,
        "benefit": 1,
        "harm": 0,
        "low_has_parsed_answer": 0,
        "confidence": 90,
        "confidence_missing": 0,
        "confidence_total_tokens": 100,
        "activity_sequence": ["calculate", "verify", "conclude"],
    }
    record.update(updates)
    return record


def test_process_state_distinguishes_complete_visible_and_empty():
    assert stage1_6.process_state(minimal_record(low_has_parsed_answer=1)) == "complete"
    assert stage1_6.process_state(minimal_record()) == "visible_unfinished"
    assert (
        stage1_6.process_state(minimal_record(activity_sequence=[]))
        == "empty_unfinished"
    )


def test_interaction_profile_uses_state_but_removes_conclude_shortcuts():
    record = minimal_record(confidence=80)
    features = stage1_6.profile_features(record, "P3_state_interaction", 0.5)
    assert features["interaction::confidence_x_state::visible_unfinished"] == 0.8
    assert features["interaction::confidence_x_state::complete"] == 0.0
    assert all("conclude" not in key for key in features)
    assert features["structural_last_verify"] == 1.0


def test_confidence_imputation_uses_training_indices_only():
    records = [
        minimal_record(confidence=20),
        minimal_record(confidence=80),
        minimal_record(confidence=100),
    ]
    assert stage1_6.fit_confidence_imputer(records, [0, 1]) == 0.5


def test_selective_policy_charges_only_queried_confidence():
    records = []
    for index in range(4):
        records.append(
            minimal_record(
                case_id=f"case-{index}",
                question_id=f"q-{index}",
                low_completion_tokens=512,
                high_completion_tokens=700,
                incremental_token_proxy=188,
                high_correct=int(index < 2),
                gain=int(index < 2),
                benefit=int(index < 2),
                confidence_total_tokens=128,
            )
        )
    predictions = {
        "P0_process_only": np.asarray([0.9, 0.8, 0.2, 0.1]),
        "P3_state_interaction": np.asarray([0.9, 0.8, 0.2, 0.1]),
    }
    result = stage1_6.cost_aware_policy_simulation(records, predictions)
    row = result["fractions"]["0.25"]["selective_25pct"]
    assert row["confidence_queried"] == 1
    assert row["confidence_overhead_total"] == 128
    assert row["upgraded"] == 0


def test_reliability_uses_current_correctness_not_benefit():
    records = [
        minimal_record(confidence=100, low_correct=1, benefit=0),
        minimal_record(confidence=0, low_correct=0, benefit=1),
    ]
    result = stage1_6.reliability_summary(records)
    assert result["brier"] == 0.0
