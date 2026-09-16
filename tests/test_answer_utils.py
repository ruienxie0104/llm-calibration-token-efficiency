import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "experiments"
    / "v3-budget-pilot"
    / "answer_utils.py"
)
SPEC = importlib.util.spec_from_file_location("v3_answer_utils", MODULE_PATH)
answer_utils = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(answer_utils)


def test_extract_boxed_handles_nested_braces():
    assert answer_utils.extract_boxed(r"reasoning \boxed{\frac{2}{21}}") == r"\frac{2}{21}"


def test_fraction_presentation_variants_are_equivalent():
    assert answer_utils.is_correct(r"\frac{5}{9}", r"\frac 59")
    assert answer_utils.is_correct(r"\frac{33}{100}", r"\dfrac{33}{100}")
    assert answer_utils.is_correct(r"\tfrac{3}{4}", "0.75")


def test_degree_marker_does_not_change_numeric_answer():
    assert answer_utils.is_correct(r"75^\circ", "75")


def test_distinct_fractions_remain_distinct():
    assert not answer_utils.is_correct(r"\frac{2}{21}", r"\frac{22}{1}")
