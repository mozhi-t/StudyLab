from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FavoriteQuestion:
    question_id: str
    bank_name: str
    bank_question_id: int
    subject: str
    question: str
    options: dict[str, str]
    answer: str
    explanation: str
