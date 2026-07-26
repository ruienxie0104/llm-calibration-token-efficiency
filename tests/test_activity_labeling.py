import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
V2_DIR = ROOT / "experiments" / "v2-mmlu-arc"
sys.path.insert(0, str(V2_DIR))

from experiment_v2 import (
    build_event_log,
    build_traces,
    extract_answer,
    label_step,
    segment_cot,
)
from export_activity_label_sample import export_sample


def test_specific_activity_labels_take_precedence_over_reason():
    assert label_step("Because it is uncertain, let me verify the result.") == "verify"
    assert label_step("Wait, that was incorrect because I used the wrong sign.") == "reconsider"
    assert label_step("First derive x, then substitute it into the equation.") == "plan"
    assert label_step("Recall the formula for the area.") == "recall"
    assert label_step("Option C cannot be correct because it violates the premise.") == "evaluate"
    assert label_step("Compute 2 x 3 before continuing.") == "calculate"
    assert label_step("Explain why x belongs to the domain.") == "reason"
    assert label_step("Given the two-dimensional subspace, identify the target.") == "understand"


def test_segmentation_preserves_markdown_final_answer():
    response = (
        "First derive x, then substitute it.\n\n"
        "Therefore the conclusion follows.\n\n"
        "**Answer:** B"
    )
    steps = segment_cot(response)

    assert steps[-1] == "**Answer:** B"
    assert [label_step(step) for step in steps] == ["plan", "reason", "answer"]
    assert segment_cot("--------------------------------") == []


def test_answer_extraction_accepts_boxed_and_choice_formats():
    cases = {
        r"\boxed{D}": "D",
        r"\boxed{\text{B}}": "B",
        r"\boxed{\text{C. }\;\text{final choice}}": "C",
        "Therefore the correct choice is A.": "A",
        "This matches option B.": "B",
    }

    for response, expected in cases.items():
        assert extract_answer(response, {}) == expected


def test_trace_records_observed_and_synthetic_events():
    results = {
        "TestModel": [
            {
                "question_id": "Q1",
                "benchmark": "test",
                "thinking": "Because A implies B.",
                "response": "**Answer:** A",
                "correct": True,
                "elapsed": 1,
                "total_tokens": 5,
                "confidence": 90,
                "error": None,
            }
        ]
    }

    trace = build_traces(results)["TestModel"][0]
    assert trace["observed_trace"] == ["reason", "answer"]
    assert trace["trace"] == ["understand", "reason", "answer"]
    assert trace["synthetic_events"] == [
        {
            "position": 0,
            "activity": "understand",
            "reason": "missing_start_boundary",
        }
    ]

    _, event_frame = build_event_log({"TestModel": [trace]})
    assert event_frame["synthetic"].tolist() == ["True", "False", "False"]


def test_annotation_export_is_balanced_and_deterministic(tmp_path):
    raw = {}
    model_names = (
        "GPT-OSS-20B",
        "DeepSeek-V4-Flash-158B",
        "GPT-OSS-120B",
        "GLM-5.2-756B",
    )
    for model in model_names:
        raw[model] = [
            {
                "question_id": f"{model}_Q1",
                "benchmark": "test",
                "thinking": "\n\n".join(f"{index}. Compute {index} + 1." for index in range(5)),
                "response": "Answer: A",
                "error": None,
            }
        ]

    input_path = tmp_path / "raw.json"
    first_output = tmp_path / "first.csv"
    second_output = tmp_path / "second.csv"
    input_path.write_text(json.dumps(raw))

    export_sample(input_path, first_output, sample_size=8, seed=42)
    export_sample(input_path, second_output, sample_size=8, seed=42)

    assert first_output.read_text() == second_output.read_text()
    with first_output.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 8
    assert {model: sum(row["model"] == model for row in rows) for model in model_names} == {
        model: 2 for model in model_names
    }
    assert all(not row["human_activity"] for row in rows)
