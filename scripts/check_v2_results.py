#!/usr/bin/env python3
"""Validate the canonical V2 reproducibility artifact set."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "experiments" / "v2-mmlu-arc" / "results"
EXPECTED_MODELS = (
    "GPT-OSS-20B",
    "DeepSeek-V4-Flash-158B",
    "GPT-OSS-120B",
    "GLM-5.2-756B",
)
EXPECTED_MODEL_SET = set(EXPECTED_MODELS)
EXPECTED_CASES_PER_MODEL = 100
REQUIRED_JSON_FILES = (
    "raw_responses_v2.json",
    "traces_final.json",
    "calibration_final.json",
    "conformance_final.json",
    "conformance_deepseek_ref.json",
    "discovery_final.json",
    "entropy_step_analysis.json",
)
REQUIRED_FILES = REQUIRED_JSON_FILES + ("full_metrics_final.csv",)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_square_matrix(matrix, size):
    return (
        isinstance(matrix, list)
        and len(matrix) == size
        and all(isinstance(row, list) and len(row) == size for row in matrix)
    )


def is_symmetric(matrix, tolerance=1e-12):
    if not isinstance(matrix, list) or any(not isinstance(row, list) for row in matrix):
        return False
    if any(len(row) != len(matrix) for row in matrix):
        return False
    try:
        return all(
            abs(matrix[row][column] - matrix[column][row]) <= tolerance
            for row in range(len(matrix))
            for column in range(len(matrix))
        )
    except TypeError:
        return False


def load_json(path, problems):
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        problems.append(f"Unreadable JSON: {path.name} ({error})")
        return None


def check_model_mapping(value, artifact_name, problems):
    if not isinstance(value, dict):
        problems.append(f"Invalid: {artifact_name} must contain a model mapping")
        return False

    model_set = set(value)
    missing = sorted(EXPECTED_MODEL_SET - model_set)
    unexpected = sorted(model_set - EXPECTED_MODEL_SET)
    if missing:
        problems.append(f"Invalid: {artifact_name} missing models: {', '.join(missing)}")
    if unexpected:
        problems.append(f"Invalid: {artifact_name} has unexpected models: {', '.join(unexpected)}")
    return not missing and not unexpected


def validate_raw_responses(raw, problems):
    question_ids_by_model = {}
    if not check_model_mapping(raw, "raw_responses_v2.json", problems):
        if not isinstance(raw, dict):
            return question_ids_by_model

    for model in EXPECTED_MODELS:
        rows = raw.get(model)
        if not isinstance(rows, list):
            problems.append(f"Invalid: raw responses for {model} must be a list")
            continue
        if len(rows) != EXPECTED_CASES_PER_MODEL:
            problems.append(
                f"Invalid: {model} has {len(rows)} raw responses; "
                f"expected {EXPECTED_CASES_PER_MODEL}"
            )

        valid_rows = [row for row in rows if isinstance(row, dict)]
        if len(valid_rows) != len(rows):
            problems.append(f"Invalid: {model} has {len(rows) - len(valid_rows)} non-object rows")

        question_ids = [row.get("question_id") for row in valid_rows]
        valid_question_ids = [value for value in question_ids if isinstance(value, str) and value]
        if len(valid_question_ids) != len(question_ids):
            problems.append(f"Invalid: {model} has missing or invalid question_id values")
        duplicate_count = len(valid_question_ids) - len(set(valid_question_ids))
        if duplicate_count:
            problems.append(f"Invalid: {model} has {duplicate_count} duplicate question_id values")
        question_ids_by_model[model] = set(valid_question_ids)

        failed = [row for row in valid_rows if row.get("error") or row.get("confidence_error")]
        invalid_answers = [
            row for row in valid_rows if row.get("predicted_letter") not in {"A", "B", "C", "D"}
        ]
        invalid_confidences = [
            row
            for row in valid_rows
            if not is_number(row.get("confidence")) or not 0 <= row["confidence"] <= 100
        ]
        invalid_correct = [row for row in valid_rows if not isinstance(row.get("correct"), bool)]
        missing_content = [
            row
            for row in valid_rows
            if not str(row.get("thinking", "")).strip() and not str(row.get("response", "")).strip()
        ]
        invalid_tokens = [
            row
            for row in valid_rows
            if not is_number(row.get("total_tokens")) or row["total_tokens"] < 0
        ]

        checks = (
            (failed, "API/confidence errors"),
            (invalid_answers, "invalid predicted answers"),
            (invalid_confidences, "invalid confidence values"),
            (invalid_correct, "invalid correctness flags"),
            (missing_content, "empty reasoning/response entries"),
            (invalid_tokens, "invalid token counts"),
        )
        for invalid_rows, description in checks:
            if invalid_rows:
                problems.append(f"Invalid: {model} has {len(invalid_rows)} {description}")

    available_sets = [
        (model, question_ids_by_model[model])
        for model in EXPECTED_MODELS
        if model in question_ids_by_model
    ]
    if available_sets:
        reference_model, reference_ids = available_sets[0]
        for model, question_ids in available_sets[1:]:
            if question_ids != reference_ids:
                problems.append(
                    f"Invalid: raw question set for {model} differs from {reference_model}"
                )
    return question_ids_by_model


def validate_traces(traces, raw_question_ids, problems):
    if not check_model_mapping(traces, "traces_final.json", problems):
        if not isinstance(traces, dict):
            return

    for model in EXPECTED_MODELS:
        rows = traces.get(model)
        if not isinstance(rows, list):
            problems.append(f"Invalid: traces for {model} must be a list")
            continue
        if len(rows) != EXPECTED_CASES_PER_MODEL:
            problems.append(
                f"Invalid: {model} has {len(rows)} traces; expected {EXPECTED_CASES_PER_MODEL}"
            )

        valid_rows = [row for row in rows if isinstance(row, dict)]
        question_ids = [
            row.get("question_id")
            for row in valid_rows
            if isinstance(row.get("question_id"), str) and row["question_id"]
        ]
        if len(question_ids) != len(valid_rows):
            problems.append(f"Invalid: {model} traces have missing or invalid question_id values")
        if len(question_ids) != len(set(question_ids)):
            problems.append(f"Invalid: {model} traces contain duplicate question_id values")
        if model in raw_question_ids and set(question_ids) != raw_question_ids[model]:
            problems.append(f"Invalid: {model} trace question set does not match raw responses")

        malformed_traces = 0
        inconsistent_steps = 0
        invalid_metadata = 0
        invalid_provenance = 0
        case_ids = []
        for row in valid_rows:
            trace = row.get("trace")
            if (
                not isinstance(trace, list)
                or not trace
                or any(not isinstance(activity, str) or not activity for activity in trace)
            ):
                malformed_traces += 1
            elif row.get("num_steps") != len(trace):
                inconsistent_steps += 1

            if not isinstance(row.get("correct"), bool) or not is_number(row.get("confidence")):
                invalid_metadata += 1
            case_id = row.get("case_id")
            if isinstance(case_id, str) and case_id:
                case_ids.append(case_id)
            else:
                invalid_metadata += 1

            observed_trace = row.get("observed_trace")
            synthetic_events = row.get("synthetic_events")
            if (
                not isinstance(observed_trace, list)
                or row.get("num_observed_steps") != len(observed_trace)
                or not isinstance(synthetic_events, list)
            ):
                invalid_provenance += 1
            elif isinstance(trace, list):
                for event in synthetic_events:
                    if not isinstance(event, dict):
                        invalid_provenance += 1
                        break
                    position = event.get("position")
                    activity = event.get("activity")
                    if (
                        not isinstance(position, int)
                        or isinstance(position, bool)
                        or not 0 <= position < len(trace)
                        or trace[position] != activity
                    ):
                        invalid_provenance += 1
                        break

        if malformed_traces:
            problems.append(f"Invalid: {model} has {malformed_traces} malformed traces")
        if inconsistent_steps:
            problems.append(f"Invalid: {model} has {inconsistent_steps} incorrect num_steps values")
        if invalid_metadata:
            problems.append(f"Invalid: {model} has {invalid_metadata} invalid trace metadata values")
        if invalid_provenance:
            problems.append(
                f"Invalid: {model} has {invalid_provenance} traces without valid "
                "observed/synthetic provenance"
            )
        if len(case_ids) != len(set(case_ids)):
            problems.append(f"Invalid: {model} traces contain duplicate case_id values")


def validate_calibration(calibration, problems):
    if not check_model_mapping(calibration, "calibration_final.json", problems):
        if not isinstance(calibration, dict):
            return

    for model in EXPECTED_MODELS:
        metrics = calibration.get(model)
        if not isinstance(metrics, dict):
            problems.append(f"Invalid: calibration metrics for {model} must be an object")
            continue
        if metrics.get("brier_count") != EXPECTED_CASES_PER_MODEL:
            problems.append(
                f"Invalid: {model} calibration covers {metrics.get('brier_count')} cases; "
                f"expected {EXPECTED_CASES_PER_MODEL}"
            )
        brier = metrics.get("brier_score")
        if not is_number(brier) or not 0 <= brier <= 1:
            problems.append(f"Invalid: {model} has an invalid Brier score")


def validate_model_objects(value, artifact_name, problems):
    if not check_model_mapping(value, artifact_name, problems):
        if not isinstance(value, dict):
            return
    for model in EXPECTED_MODELS:
        if not isinstance(value.get(model), dict):
            problems.append(f"Invalid: {artifact_name} entry for {model} must be an object")


def validate_discovery(discovery, problems):
    if not check_model_mapping(discovery, "discovery_final.json", problems):
        if not isinstance(discovery, dict):
            return
    for model in EXPECTED_MODELS:
        result = discovery.get(model)
        variants = result.get("variants") if isinstance(result, dict) else None
        if (
            not isinstance(variants, int)
            or isinstance(variants, bool)
            or not 1 <= variants <= EXPECTED_CASES_PER_MODEL
        ):
            problems.append(f"Invalid: discovery variants for {model} must be an integer from 1–100")


def validate_matrix_section(section, section_name, matrix_key, problems):
    if not isinstance(section, dict):
        problems.append(f"Invalid: entropy section {section_name} must be an object")
        return
    models = section.get("models")
    if models != list(EXPECTED_MODELS):
        problems.append(f"Invalid: {section_name} model order does not match canonical order")

    matrix = section.get(matrix_key)
    size = len(EXPECTED_MODELS)
    if not is_square_matrix(matrix, size):
        problems.append(f"Invalid: {section_name}.{matrix_key} must be a {size}x{size} matrix")
        return
    if any(not is_number(value) or value < 0 for row in matrix for value in row):
        problems.append(f"Invalid: {section_name}.{matrix_key} contains invalid distances")
        return
    if not is_symmetric(matrix):
        problems.append(f"Invalid: {section_name}.{matrix_key} is not symmetric")
    if any(abs(matrix[index][index]) > 1e-12 for index in range(size)):
        problems.append(f"Invalid: {section_name}.{matrix_key} diagonal is not zero")


def validate_entropy(entropy, problems):
    if not isinstance(entropy, dict):
        problems.append("Invalid: entropy_step_analysis.json must contain an object")
        return

    model_sections = ("A1_trace_entropy", "A2_variant_entropy", "C1_step_frequency")
    for section_name in model_sections:
        section = entropy.get(section_name)
        if not isinstance(section, dict) or set(section) != EXPECTED_MODEL_SET:
            problems.append(f"Invalid: {section_name} does not contain exactly the canonical models")

    matrix_sections = (
        ("A3_levenshtein_distance", "matrix"),
        ("C2_jsd_step_type", "matrix"),
        ("C3_jsd_bigram", "matrix"),
    )
    for section_name, matrix_key in matrix_sections:
        validate_matrix_section(entropy.get(section_name), section_name, matrix_key, problems)

    levenshtein = entropy.get("A3_levenshtein_distance")
    if isinstance(levenshtein, dict):
        validate_matrix_section(levenshtein, "A3_levenshtein_distance", "std_matrix", problems)


def validate_metrics_csv(path, problems):
    try:
        with path.open(newline="") as file:
            rows = list(csv.DictReader(file))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        problems.append(f"Unreadable CSV: {path.name} ({error})")
        return

    if not rows or "Model" not in rows[0]:
        problems.append("Invalid: full_metrics_final.csv must contain a Model column")
        return
    models = [row.get("Model") for row in rows]
    if len(models) != len(EXPECTED_MODELS):
        problems.append(
            f"Invalid: full_metrics_final.csv has {len(models)} rows; "
            f"expected {len(EXPECTED_MODELS)}"
        )
    if len(models) != len(set(models)):
        problems.append("Invalid: full_metrics_final.csv contains duplicate model rows")
    missing = sorted(EXPECTED_MODEL_SET - set(models))
    unexpected = sorted(set(models) - EXPECTED_MODEL_SET)
    if missing:
        problems.append(f"Invalid: full_metrics_final.csv missing models: {', '.join(missing)}")
    if unexpected:
        problems.append(
            f"Invalid: full_metrics_final.csv has unexpected models: {', '.join(unexpected)}"
        )


def validate_results_dir(results_dir):
    results_dir = Path(results_dir)
    problems = []
    for filename in REQUIRED_FILES:
        if not (results_dir / filename).is_file():
            problems.append(f"Missing: {filename}")

    loaded = {}
    for filename in REQUIRED_JSON_FILES:
        path = results_dir / filename
        if path.is_file():
            loaded[filename] = load_json(path, problems)

    raw_question_ids = {}
    raw = loaded.get("raw_responses_v2.json")
    if raw is not None:
        raw_question_ids = validate_raw_responses(raw, problems)
    traces = loaded.get("traces_final.json")
    if traces is not None:
        validate_traces(traces, raw_question_ids, problems)
    calibration = loaded.get("calibration_final.json")
    if calibration is not None:
        validate_calibration(calibration, problems)
    conformance = loaded.get("conformance_final.json")
    if conformance is not None:
        validate_model_objects(conformance, "conformance_final.json", problems)
    deepseek_conformance = loaded.get("conformance_deepseek_ref.json")
    if deepseek_conformance is not None:
        validate_model_objects(
            deepseek_conformance,
            "conformance_deepseek_ref.json",
            problems,
        )
    discovery = loaded.get("discovery_final.json")
    if discovery is not None:
        validate_discovery(discovery, problems)
    entropy = loaded.get("entropy_step_analysis.json")
    if entropy is not None:
        validate_entropy(entropy, problems)

    metrics_path = results_dir / "full_metrics_final.csv"
    if metrics_path.is_file():
        validate_metrics_csv(metrics_path, problems)
    return problems


def main() -> int:
    problems = validate_results_dir(RESULTS_DIR)
    if problems:
        print("V2 result set is not ready:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("V2 result set is complete and structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
