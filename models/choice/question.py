from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuestionItem:
    id: int
    question: str
    options: dict[str, str]
    answer: str
    explanation: str
    source_question_id: str | None = None
    source_bank_name: str | None = None
    source_bank_question_id: int | None = None
    source_subject: str | None = None


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
