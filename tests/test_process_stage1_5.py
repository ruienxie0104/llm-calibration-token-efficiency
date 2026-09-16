import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).parents[1] / "experiments" / "v3-budget-pilot"
sys.path.insert(0, str(SCRIPT_DIR))
MODULE_PATH = SCRIPT_DIR / "analyze_process_stage1_5.py"
SPEC = importlib.util.spec_from_file_location("analyze_process_stage1_5", MODULE_PATH)
stage1_5 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = stage1_5
SPEC.loader.exec_module(stage1_5)


def test_structural_features_remove_every_conclude_shortcut():
    record = {
        "activity_sequence": ["understand_setup", "calculate", "conclude"],
    }
    assert stage1_5.structural_sequence(record) == ["understand_setup", "calculate"]
    features = {
        **stage1_5.last_activity_features(record),
        **stage1_5.structural_count_features(record),
    }
    assert all("conclude" not in key for key in features)
    assert features["structural_last_calculate"] == 1


def test_confidence_policy_pays_overhead_before_upgrades():
    records = []
    for index in range(4):
        records.append(
            {
                "low_budget": 512,
                "high_budget": 1024,
                "low_completion_tokens": 512,
                "high_completion_tokens": 700,
                "incremental_token_proxy": 188,
                "low_correct": 0,
                "high_correct": int(index < 2),
                "gain": int(index < 2),
                "confidence_total_tokens": 600,
            }
        )
    predictions = {
        profile: np.asarray([0.9, 0.8, 0.2, 0.1]) for profile in stage1_5.PROFILES
    }
    result = stage1_5.hard_budget_policy_simulation(
        records, predictions, fractions=(0.25,)
    )["fractions"]["0.25"]
    assert result["C4_structural"]["upgraded"] == 1
    assert result["C6_structural_confidence"]["upgraded"] == 0
    assert not result["C6_structural_confidence"]["nominal_budget_feasible"]


def test_structural_dfg_uses_sequence_without_conclude():
    record = {"activity_sequence": ["calculate", "conclude"]}
    models = (
        stage1_5.fit_dfg([["calculate", "verify"]]),
        stage1_5.fit_dfg([["calculate", "verify"]]),
        stage1_5.fit_dfg([["calculate", "backtrack"]]),
    )
    features = stage1_5.dfg_features(record, models, structural=True, prefix="structural")
    assert features["structural_dfg_all_mean_log_probability"] == 0.0
