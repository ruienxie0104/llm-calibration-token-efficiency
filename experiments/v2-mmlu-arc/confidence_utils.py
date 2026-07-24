"""Helpers for context-preserving confidence reassessment."""

from __future__ import annotations


def make_confidence_prompt_with_context(
    question, choices, predicted_answer, model_response, model_thinking=""
):
    """Reconstruct the answer turn and include the complete reasoning response."""
    if isinstance(choices, dict):
        choices_text = "\n".join(f"  {key}. {value}" for key, value in choices.items())
    elif isinstance(choices, list):
        letters = ["A", "B", "C", "D", "E"]
        choices_text = "\n".join(
            f"  {letters[index]}. {value}" for index, value in enumerate(choices)
        )
    else:
        choices_text = str(choices)

    user_message = f"""Solve this problem step by step. Show your reasoning clearly.

Question: {question}

Choices:
{choices_text}

Think step by step, then give your answer as a single letter after 'Answer:'."""

    reasoning_parts = [part for part in (model_thinking, model_response) if part]
    assistant_context = "\n\n".join(reasoning_parts)
    confidence_message = f"""You previously answered "{predicted_answer}" for this question.
Based on your complete response above, how confident are you that "{predicted_answer}" is the correct answer?

Give ONLY a single number from 0 to 100 (0 = completely unsure, 100 = absolutely certain). Do not include any other text."""

    return [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_context},
        {"role": "user", "content": confidence_message},
    ]

