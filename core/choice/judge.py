from __future__ import annotations


class ChoiceJudge:
    """Judge a choice answer against the question's expected answer."""

    @staticmethod
    def judge(selected_answer: str, correct_answer: str) -> bool:
        return selected_answer == correct_answer
