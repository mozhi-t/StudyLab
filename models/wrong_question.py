from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WrongIndexItem:
    question_id: str
    subject: str
    question_content: str
    error_count: int


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
