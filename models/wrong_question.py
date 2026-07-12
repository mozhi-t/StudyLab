from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WrongQuestion:
    question_id: str
    question_num: int
    bank_name: str
    bank_question_id: int
    subject: str
    question: str
    options: dict[str, str]
    answer: str
    explanation: str
    error_count: int = 1
    question_type: str = "choice"
    payload: dict = field(default_factory=dict)
