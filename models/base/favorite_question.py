from __future__ import annotations

from dataclasses import dataclass, field


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
    question_type: str = "choice"
    payload: dict = field(default_factory=dict)
