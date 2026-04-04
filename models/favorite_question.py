from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FavoriteIndexItem:
    question_id: str
    subject: str
    question_content: str


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
