from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BankMeta:
    name: str
    subject: str
    create_time: str


@dataclass
class QuestionItem:
    id: int
    question: str
    options: dict[str, str]
    answer: str
    explanation: str


@dataclass
class QuestionBank:
    name: str
    subject: str
    create_time: str
    difficulty: int
    total_questions: int
    questions: list[QuestionItem] = field(default_factory=list)

    def __post_init__(self):
        self.questions = [item if isinstance(item, QuestionItem) else QuestionItem(**item) for item in self.questions]
