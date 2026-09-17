import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "v3-budget-pilot"
sys.path.insert(0, str(SCRIPT_DIR))

import analyze_process_stage3 as analysis  # noqa: E402
import prepare_process_stage3_questions as preparer  # noqa: E402
import run_process_stage3 as runner  # noqa: E402


def rows():
    return [
        {"qid": "a", "level": 3, "state": "complete", "visible": False, "low": 1, "high": 1,
         "gain": 0, "prefix_tokens": 10, "continuation_tokens": 20, "continuation_parseable": True},
        {"qid": "b", "level": 4, "state": "visible_unfinished", "visible": True, "low": 0, "high": 1,
         "gain": 1, "prefix_tokens": 10, "continuation_tokens": 40, "continuation_parseable": True},
        {"qid": "c", "level": 3, "state": "empty_unfinished", "visible": False, "low": 0, "high": 0,
         "gain": 0, "prefix_tokens": 10, "continuation_tokens": 60, "continuation_parseable": False},
    ]


def test_visible_policy_only_continues_visible_unfinished():
    result = analysis.visible_policy(rows())
    assert result["n_continue"] == 1
    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["continuation_cost"] == 40


def test_cost_calibrated_random_exactly_matches_expected_continuation_cost():
    result = analysis.cost_calibrated_random(rows())
    assert result["probability"] == pytest.approx(1 / 3)
    assert result["target_continuation_cost"] == pytest.approx(40)
    assert result["expected_continuation_cost"] == pytest.approx(40)
    assert result["cost_identity_error"] == pytest.approx(0)


def test_count_and_cost_oracles_respect_their_constraints():
    policy = analysis.fixed_and_question_policies(rows())
    assert policy["oracle_count_matched"]["n_continue"] == 1
    oracle = analysis.oracle_cost_constrained(rows(), budget=40)
    assert oracle["used_continuation_cost"] <= 40
    assert oracle["accuracy"] == pytest.approx(2 / 3)


def test_bootstrap_is_question_clustered_and_deterministic():
    by_model = {model: rows() for model in analysis.EXPECTED_MODELS}
    first = analysis.bootstrap_delta(by_model, ["a", "b", "c"], n_bootstrap=100, seed=19)
    second = analysis.bootstrap_delta(by_model, ["a", "b", "c"], n_bootstrap=100, seed=19)
    assert first == second
    assert first["cluster_unit"] == "question_id"


def test_random_ledger_replay_is_deterministic_and_reports_cost_interval():
    first = analysis.random_ledger_replay(rows(), draws=100, seed=29)
    second = analysis.random_ledger_replay(rows(), draws=100, seed=29)
    assert first == second
    assert first["cost_p025"] <= first["mean_tokens"] <= first["cost_p975"]


def test_preparer_finds_ids_in_results_as_well_as_data(tmp_path):
    data_dir, results_dir = tmp_path / "data", tmp_path / "results"
    data_dir.mkdir()
    results_dir.mkdir()
    (data_dir / "old.json").write_text(json.dumps({"id": "test/algebra/1.json"}), encoding="utf-8")
    (results_dir / "raw.json").write_text(json.dumps({"records": [{"question_id": "test/geometry/2.json"}]}), encoding="utf-8")
    excluded, inspected = preparer.historic_ids([data_dir, results_dir], tmp_path / "out.json")
    assert excluded == {"test/algebra/1.json", "test/geometry/2.json"}
    assert len(inspected) == 2


def test_runner_state_uses_visible_content_not_hidden_thinking():
    assert runner.compute_process_state("", None) == "empty_unfinished"
    assert runner.compute_process_state("work in visible content", None) == "visible_unfinished"
    assert runner.compute_process_state("", "42") == "complete"


def test_checkpoint_prefers_a_successful_retry(tmp_path):
    path = tmp_path / "checkpoint.json"
    failed = {"stage": "smoke", "model": "GPT-OSS-120B", "question_id": "test/a.json", "action": "prefix", "error": "timeout"}
    succeeded = {**failed, "error": None, "content": "done"}
    path.write_text(json.dumps({"schema": {}, "records": [failed, succeeded]}), encoding="utf-8")
    records, done, _ = runner.load_checkpoint(path)
    assert len(records) == 1
    assert records[0]["error"] is None
    assert len(done) == 1


def test_formal_runner_rejects_partial_models(monkeypatch):
    questions = [{"id": f"test/{number}.json"} for number in range(60)]
    monkeypatch.setattr(runner, "load_questions", lambda stage: questions)
    with pytest.raises(ValueError, match="exactly"):
        runner.validate_configuration("formal", ["GPT-OSS-120B"], questions, None)
