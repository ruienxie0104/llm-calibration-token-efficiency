#!/usr/bin/env python3
"""Small offline regression tests for Stage 2 action construction."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_process_stage2 import classify_prefix, make_record, planned_actions  # noqa: E402


class Stage2RunnerTests(unittest.TestCase):
    def test_complete_prefix_has_answer(self) -> None:
        state, events, answer = classify_prefix("Work. Therefore \\boxed{42}.")
        self.assertEqual(state, "complete")
        self.assertEqual(answer, "42")
        self.assertTrue(events)

    def test_unfinished_states(self) -> None:
        self.assertEqual(classify_prefix("Let x = 2. Then")[0], "visible_unfinished")
        self.assertEqual(classify_prefix("")[0], "empty_unfinished")

    def test_branching_is_only_for_empty_gate1_or_formal(self) -> None:
        self.assertEqual(planned_actions("gate0", "empty_unfinished"), ["continuation", "fresh_high"])
        self.assertEqual(planned_actions("gate1", "complete"), ["continuation"])
        self.assertEqual(planned_actions("gate1", "empty_unfinished"), ["continuation", "branch_1", "branch_2"])

    def test_record_rescores_answer_and_keeps_context_mode(self) -> None:
        question = {"id": "q", "level": 3, "subject": "Algebra", "answer": "42"}
        response = {"content": "\\boxed{42}", "thinking": "", "done_reason": "stop",
                    "prompt_tokens": 4, "completion_tokens": 2, "latency_seconds": 0.1, "error": None}
        record = make_record("gate0", "GPT-OSS-120B", question, "prefix", 512, response)
        self.assertTrue(record["correct"])
        self.assertEqual(record["process_state"], "complete")
        continuation = make_record("gate0", "GPT-OSS-120B", question, "continuation", 512,
                                   response, prefix=record, context_mode="visible_prefix_only")
        self.assertEqual(continuation["context_mode"], "visible_prefix_only")
        self.assertEqual(continuation["prefix_process_state"], "complete")


if __name__ == "__main__":
    unittest.main()
