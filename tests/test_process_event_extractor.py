import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "experiments"
    / "v3-budget-pilot"
    / "process_event_extractor.py"
)
SPEC = importlib.util.spec_from_file_location("process_event_extractor", MODULE_PATH)
extractor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = extractor
SPEC.loader.exec_module(extractor)


def test_activity_sequence_uses_observable_prefix_only():
    text = (
        "Let x be the unknown value.\n\n"
        "Using the quadratic formula, compute x = 3.\n\n"
        "Check that x satisfies the original equation.\n\n"
        r"Therefore the final answer is \boxed{3}."
    )
    assert extractor.activity_sequence(text) == [
        "understand_setup",
        "recall",
        "verify",
        "conclude",
    ]


def test_backtracking_and_loops_become_features():
    events = [
        extractor.Event(0, "calculate", "calculate"),
        extractor.Event(1, "calculate", "calculate again"),
        extractor.Event(2, "backtrack", "wait"),
    ]
    features = extractor.base_process_features(events)
    assert features["process_loop_count"] == 1
    assert features["process_has_backtrack"] == 1
    assert features["transition::calculate->calculate"] == 1


def test_dfg_features_are_finite_for_unseen_transition():
    all_model = extractor.fit_dfg([["understand_setup", "calculate"]])
    benefit_model = extractor.fit_dfg([["calculate", "verify"]])
    no_benefit_model = extractor.fit_dfg([["calculate", "backtrack"]])
    features = extractor.dfg_conformance_features(
        ["understand_setup", "conclude"],
        all_model,
        benefit_model,
        no_benefit_model,
    )
    assert features["dfg_all_unseen_transition_share"] == 1
    assert isinstance(features["dfg_benefit_logp_advantage"], float)
