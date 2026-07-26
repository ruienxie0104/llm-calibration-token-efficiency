import csv
import json

from scripts.check_v2_results import (
    EXPECTED_CASES_PER_MODEL,
    EXPECTED_MODELS,
    validate_results_dir,
)


def write_json(path, value):
    path.write_text(json.dumps(value))


def write_canonical_result_set(results_dir):
    results_dir.mkdir()
    raw = {}
    traces = {}
    calibration = {}
    conformance = {}
    deepseek_conformance = {}
    discovery = {}

    for model in EXPECTED_MODELS:
        raw[model] = []
        traces[model] = []
        for index in range(EXPECTED_CASES_PER_MODEL):
            question_id = f"Q{index:03d}"
            raw[model].append(
                {
                    "model": model,
                    "question_id": question_id,
                    "predicted_letter": "A",
                    "correct": True,
                    "thinking": "Reasoning.",
                    "response": "Answer: A",
                    "confidence": 90,
                    "total_tokens": 10,
                    "error": None,
                    "confidence_error": None,
                }
            )
            traces[model].append(
                {
                    "case_id": f"{model}_{question_id}",
                    "model": model,
                    "question_id": question_id,
                    "trace": ["understand", "answer"],
                    "num_steps": 2,
                    "observed_trace": ["understand", "answer"],
                    "num_observed_steps": 2,
                    "synthetic_events": [],
                    "correct": True,
                    "confidence": 90,
                }
            )

        calibration[model] = {"brier_count": 100, "brier_score": 0.01}
        conformance[model] = {"avg_fitness": 1.0, "total_deviations": 0}
        deepseek_conformance[model] = {
            "reference_model": "DeepSeek-V4-Flash-158B",
            "avg_fitness": 1.0,
            "alignment_deviations": 0,
        }
        discovery[model] = {"variants": 1}

    zero_matrix = [[0.0 for _ in EXPECTED_MODELS] for _ in EXPECTED_MODELS]
    entropy = {
        "A1_trace_entropy": {model: {"mean": 0.0} for model in EXPECTED_MODELS},
        "A2_variant_entropy": {
            model: {"num_variants": 1, "normalized_entropy": 0.0}
            for model in EXPECTED_MODELS
        },
        "A3_levenshtein_distance": {
            "matrix": zero_matrix,
            "std_matrix": zero_matrix,
            "models": list(EXPECTED_MODELS),
        },
        "C1_step_frequency": {
            model: {"understand": 0.5, "answer": 0.5} for model in EXPECTED_MODELS
        },
        "C2_jsd_step_type": {
            "matrix": zero_matrix,
            "models": list(EXPECTED_MODELS),
        },
        "C3_jsd_bigram": {
            "matrix": zero_matrix,
            "models": list(EXPECTED_MODELS),
            "all_bigrams": [["understand", "answer"]],
        },
    }

    write_json(results_dir / "raw_responses_v2.json", raw)
    write_json(results_dir / "traces_final.json", traces)
    write_json(results_dir / "calibration_final.json", calibration)
    write_json(results_dir / "conformance_final.json", conformance)
    write_json(results_dir / "conformance_deepseek_ref.json", deepseek_conformance)
    write_json(results_dir / "discovery_final.json", discovery)
    write_json(results_dir / "entropy_step_analysis.json", entropy)

    with (results_dir / "full_metrics_final.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Model", "Accuracy"])
        writer.writeheader()
        for model in EXPECTED_MODELS:
            writer.writerow({"Model": model, "Accuracy": "100%"})


def test_complete_canonical_result_set_is_accepted(tmp_path):
    results_dir = tmp_path / "results"
    write_canonical_result_set(results_dir)

    assert validate_results_dir(results_dir) == []


def test_legacy_model_and_incomplete_cases_are_rejected(tmp_path):
    results_dir = tmp_path / "results"
    write_canonical_result_set(results_dir)

    raw_path = results_dir / "raw_responses_v2.json"
    raw = json.loads(raw_path.read_text())
    raw["GLM-4.7-357B"] = raw[EXPECTED_MODELS[0]]
    raw[EXPECTED_MODELS[0]][0]["error"] = "temporary failure"
    raw[EXPECTED_MODELS[0]][0]["predicted_letter"] = None
    raw[EXPECTED_MODELS[0]][0]["confidence"] = None
    write_json(raw_path, raw)

    problems = validate_results_dir(results_dir)
    assert any("unexpected models: GLM-4.7-357B" in problem for problem in problems)
    assert any("API/confidence errors" in problem for problem in problems)
    assert any("invalid predicted answers" in problem for problem in problems)
    assert any("invalid confidence values" in problem for problem in problems)


def test_asymmetric_or_nonzero_diagonal_distance_is_rejected(tmp_path):
    results_dir = tmp_path / "results"
    write_canonical_result_set(results_dir)

    entropy_path = results_dir / "entropy_step_analysis.json"
    entropy = json.loads(entropy_path.read_text())
    matrix = entropy["A3_levenshtein_distance"]["matrix"]
    matrix[0][1] = 0.25
    matrix[2][2] = 0.1
    write_json(entropy_path, entropy)

    problems = validate_results_dir(results_dir)
    assert "Invalid: A3_levenshtein_distance.matrix is not symmetric" in problems
    assert "Invalid: A3_levenshtein_distance.matrix diagonal is not zero" in problems
