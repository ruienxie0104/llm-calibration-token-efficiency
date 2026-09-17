import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "v3-budget-pilot"
sys.path.insert(0, str(SCRIPT_DIR))

import analyze_process_confidence_audit as audit  # noqa: E402


def row(question_id, confidence, state="complete"):
    return audit.canonical_row(
        source="test",
        protocol="test",
        state_definition="test",
        confidence_timing="retrospective",
        model="model",
        question_id=question_id,
        replicate=1,
        budget=1,
        process_state=state,
        confidence=confidence,
        confidence_missing=confidence is None,
        correct=True,
        answer_completion_tokens=1,
        confidence_total_tokens=1,
        benefit=None,
    )


def test_visible_response_state_uses_current_brace_aware_parser():
    state, answer, correct = audit.state_from_visible_response(
        "work \\boxed{\\frac{2}{21}}", "2/21"
    )
    assert state == "complete"
    assert answer == "\\frac{2}{21}"
    assert correct
    assert audit.state_from_visible_response("partial working", "1")[0] == "visible_unfinished"
    assert audit.state_from_visible_response("", "1")[0] == "empty_unfinished"


def test_cluster_bootstrap_handles_nonoverlapping_state_question_sets():
    left = [row("q1", 100), row("q2", 100)]
    right = [row("q2", 0, "visible_unfinished"), row("q3", 0, "visible_unfinished")]
    result = audit.bootstrap_confidence_difference(left, right, draws=200, seed=7)
    assert result["estimate"] == 100
    assert result["valid_draws"] > 0
    assert result["ci_low"] == 100
    assert result["ci_high"] == 100


def test_existing_sources_build_common_schema():
    phase3 = audit.build_phase3_rows(audit.PHASE3_INPUT)
    soft = audit.build_soft_rows(audit.SOFT_INPUT, audit.PROSPECTIVE_INPUT)
    assert len(phase3) == 720
    assert len(soft) == 720
    assert {row["confidence_timing"] for row in phase3} == {"retrospective"}
    assert {row["confidence_timing"] for row in soft} == {"prospective", "retrospective"}
    assert all(row["process_state"] in audit.STATE_ORDER for row in phase3 + soft)
