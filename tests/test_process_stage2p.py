import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "v3-budget-pilot"
sys.path.insert(0, str(SCRIPT_DIR))

import analyze_process_stage2p as analysis  # noqa: E402
import run_process_stage2p as runner  # noqa: E402


def api_result(content="", error=None):
    return {
        "content": content,
        "thinking": "",
        "completion_tokens": 3 if not error else 0,
        "prompt_tokens": 5 if not error else 0,
        "total_tokens": 8 if not error else 0,
        "done_reason": "stop" if not error else None,
        "elapsed": 0.01,
        "error": error,
        "request_meta": {},
    }, None


def test_error_retry_replaces_record_and_skips_continuation(tmp_path, monkeypatch):
    question = {"id": "test/algebra/example.json", "problem": "1+0?", "answer": "1"}
    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "load_questions", lambda stage: [question])
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)

    calls = []

    def fail_prefix(*args, **kwargs):
        calls.append(args[1])
        return api_result(error="temporary failure")

    monkeypatch.setattr(runner, "api_call", fail_prefix)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_process_stage2p.py", "--stage", "gate0", "--models", "GPT-OSS-120B", "--execute"],
    )
    runner.main()

    checkpoint = tmp_path / runner.SMOKE_OUT
    first_records = json.loads(checkpoint.read_text())["records"]
    assert len(calls) == 1
    assert len(first_records) == 1
    assert first_records[0]["action"] == "prefix"
    assert first_records[0]["error"]

    calls.clear()
    monkeypatch.setattr(
        runner,
        "api_call",
        lambda *args, **kwargs: (calls.append(args[1]) or api_result("Work. \\boxed{1}")),
    )
    runner.main()

    final_records = json.loads(checkpoint.read_text())["records"]
    keys = [runner.record_key(record) for record in final_records]
    assert len(calls) == 2
    assert len(final_records) == 2
    assert len(keys) == len(set(keys))
    assert not any(record["error"] for record in final_records)


def test_formal_configuration_rejects_filtered_or_partial_runs():
    questions = runner.load_questions("formal")
    assert len(questions) == 60
    with pytest.raises(ValueError, match="question-ids"):
        runner.validate_run_configuration(
            "formal", list(runner.FORMAL_MODELS), questions, [questions[0]["id"]]
        )
    with pytest.raises(ValueError, match="exactly these models"):
        runner.validate_run_configuration("formal", [runner.FORMAL_MODELS[0]], questions)


def test_rebuilt_manifest_matches_committed_smoke_questions():
    manifest = runner.load_manifest()
    manifest_ids = {question["id"] for question in manifest["splits"]["gate0"]}
    smoke_path = SCRIPT_DIR / "results" / runner.SMOKE_OUT
    smoke_ids = {record["question_id"] for record in json.loads(smoke_path.read_text())["records"]}
    assert smoke_ids
    assert smoke_ids <= manifest_ids
    all_questions = [
        question for split in ("gate0", "gate1", "formal") for question in manifest["splits"][split]
    ]
    assert len(all_questions) == 90
    assert runner.question_ids_sha256(all_questions) == manifest["all_question_ids_sha256"]
    assert manifest["all_question_ids_sha256"] == (
        "6929cb63e2cfca3547b9a4e9c1d202c7ff55aa28ca33db6906bfb5c1288280ac"
    )


def test_lower_cost_higher_accuracy_passes_pareto_alternative():
    ratio, parity, pareto, cost_pass = analysis.evaluate_cost_condition(
        process_accuracy=0.75,
        random_accuracy=0.70,
        process_tokens=800,
        random_tokens=1000,
    )
    assert ratio == pytest.approx(0.8)
    assert not parity
    assert pareto
    assert cost_pass
