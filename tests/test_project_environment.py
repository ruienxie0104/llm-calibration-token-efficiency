import importlib.util
from pathlib import Path
import sys
import tomllib
import types


ROOT = Path(__file__).resolve().parents[1]
V2_DIR = ROOT / "experiments" / "v2-mmlu-arc"
sys.path.insert(0, str(V2_DIR))

from analysis_utils import avg_pairwise_distance, count_alignment_deviations, token_count
from confidence_utils import make_confidence_prompt_with_context


def test_environment_files_exist():
    expected = {
        ".env.example",
        ".python-version",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "scripts/check_environment.py",
    }
    assert expected <= {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}


def test_pyproject_declares_supported_python_and_dependencies():
    with (ROOT / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]

    assert project["requires-python"] == ">=3.12,<3.14"
    dependencies = {item.split("==", 1)[0] for item in project["dependencies"]}
    assert {
        "datasets",
        "matplotlib",
        "numpy",
        "pandas",
        "pm4py",
        "python-pptx",
        "scipy",
        "seaborn",
    } <= dependencies


def test_env_example_contains_no_real_key():
    values = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert values["OLLAMA_API_KEY"] == "replace-with-a-new-key"
    assert values["OLLAMA_API_URL"].startswith("https://")


def test_alignment_deviation_count_handles_simple_and_nested_moves():
    alignments = [
        {
            "alignment": [
                ("understand", "understand"),
                ("reason", ">>"),
                ("answer", "answer"),
                (("transition", ">>"), ("transition", "verify")),
            ]
        }
    ]
    assert count_alignment_deviations(alignments) == 2
    assert token_count({"p1": 2, "p2": 3}) == 5


def test_pairwise_distance_is_symmetric_and_deterministic():
    traces_a = [
        {"case_id": "a1", "trace": ["understand", "answer"]},
        {"case_id": "a2", "trace": ["understand", "reason", "answer"]},
    ]
    traces_b = [
        {"case_id": "b1", "trace": ["understand", "calculate", "answer"]},
        {"case_id": "b2", "trace": ["understand", "verify", "answer"]},
    ]
    forward = avg_pairwise_distance(traces_a, traces_b, sample_size=1)
    reverse = avg_pairwise_distance(traces_b, traces_a, sample_size=1)
    assert forward == reverse


def test_confidence_context_keeps_complete_thinking_and_response():
    thinking = "reasoning-start " + ("x" * 1500) + " reasoning-end"
    response = "Answer: B"
    messages = make_confidence_prompt_with_context(
        "Question?", ["A", "B"], "B", response, thinking
    )
    assistant_content = messages[1]["content"]
    assert "reasoning-start" in assistant_content
    assert "reasoning-end" in assistant_content
    assert response in assistant_content


def test_failed_api_case_is_retried_and_replaced(tmp_path, monkeypatch):
    if "pm4py" not in sys.modules:
        monkeypatch.setitem(sys.modules, "pm4py", types.ModuleType("pm4py"))

    spec = importlib.util.spec_from_file_location(
        "experiment_v2_for_test", V2_DIR / "experiment_v2.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "MODELS", [("test-model", "TestModel")])
    monkeypatch.setattr(module, "OUTPUT_DIR", str(tmp_path))
    question = {
        "id": "Q1",
        "benchmark": "test",
        "subject": "test",
        "question": "Choose A.",
        "choices": ["A", "B"],
        "answer_letter": "A",
        "answer_text": "A",
    }

    def failed_call(model, prompt):
        return {
            "response": "",
            "thinking": "",
            "elapsed": 1,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error": "temporary failure",
        }

    monkeypatch.setattr(module, "call_ollama_api", failed_call)
    first_run = module.run_experiment([question])
    assert len(first_run["TestModel"]) == 1
    assert first_run["TestModel"][0]["error"] == "temporary failure"
    assert module.build_traces(first_run) == {}
    assert not (tmp_path / "raw_responses_v2.json").exists()

    def successful_call(model, prompt):
        is_confidence = isinstance(prompt, list)
        return {
            "response": "90" if is_confidence else "Answer: A",
            "thinking": "" if is_confidence else "A is correct.",
            "elapsed": 1,
            "prompt_tokens": 2,
            "completion_tokens": 2,
            "total_tokens": 4,
            "error": None,
        }

    monkeypatch.setattr(module, "call_ollama_api", successful_call)
    second_run = module.run_experiment([question])
    assert len(second_run["TestModel"]) == 1
    assert second_run["TestModel"][0]["error"] is None
    assert len(module.build_traces(second_run)["TestModel"]) == 1
    assert (tmp_path / "raw_responses_v2.json").is_file()
