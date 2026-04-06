from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExamChoiceQuestion:
    id: int
    question: str
    options: dict[str, str]
    score: int


@dataclass
class ExamAnswerQuestion:
    id: int
    answer: str
    explanation: str


@dataclass
class ExamSubjectPaper:
    enabled: bool = False
    choice_questions: list[ExamChoiceQuestion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.choice_questions = [
            item if isinstance(item, ExamChoiceQuestion) else ExamChoiceQuestion(**item)
            for item in self.choice_questions
        ]


@dataclass
class ExamSubjectAnswer:
    enabled: bool = False
    choice_questions: list[ExamAnswerQuestion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.choice_questions = [
            item if isinstance(item, ExamAnswerQuestion) else ExamAnswerQuestion(**item)
            for item in self.choice_questions
        ]


@dataclass
class ExamPaper:
    exam_id: str
    exam_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    exam_password: str
    show_score_immediately: int
    show_correct_answer: int
    disallow_reentry_after_submit: int = 1
    subjects: dict[str, ExamSubjectPaper] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.subjects = {
            name: item if isinstance(item, ExamSubjectPaper) else ExamSubjectPaper(**item)
            for name, item in self.subjects.items()
        }


@dataclass
class ExamAnswerSheet:
    exam_id: str
    exam_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    exam_password: str
    show_score_immediately: int
    show_correct_answer: int
    disallow_reentry_after_submit: int = 1
    subjects: dict[str, ExamSubjectAnswer] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.subjects = {
            name: item if isinstance(item, ExamSubjectAnswer) else ExamSubjectAnswer(**item)
            for name, item in self.subjects.items()
        }
