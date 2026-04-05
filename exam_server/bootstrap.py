from __future__ import annotations

from dataclasses import asdict

from core.json_store import JsonStore
from core.question_index import QuestionIndexManager
from exam_server.defaults import ACCOUNTS_TEMPLATE, CONNECTION_TEMPLATE, SERVER_CONFIG_TEMPLATE
from exam_server.paths import ACCOUNTS_FILE, CONFIG_FILE, CONNECTION_FILE, EXAM_BANK_DIR, LOG_DIR
from models.lan_exam import ExamAnswerQuestion, ExamChoiceQuestion


def ensure_server_files() -> None:
    EXAM_BANK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JsonStore(CONFIG_FILE, SERVER_CONFIG_TEMPLATE).ensure()
    JsonStore(ACCOUNTS_FILE, ACCOUNTS_TEMPLATE).ensure()
    JsonStore(CONNECTION_FILE, CONNECTION_TEMPLATE).ensure()
    ensure_sample_exam()


def ensure_sample_exam() -> None:
    exam_dir = EXAM_BANK_DIR / "测试考试"
    question_file = exam_dir / "exam_questions.json"
    answer_file = exam_dir / "exam_answers.json"
    user_file = exam_dir / "测试考试_user.json"
    if question_file.exists() and answer_file.exists() and user_file.exists():
        return

    manager = QuestionIndexManager()
    math_bank = manager.load_bank("math", "数学基础选择题库")
    computer_bank = manager.load_bank("computer_basic", "计算机基础选择题库")
    exam_dir.mkdir(parents=True, exist_ok=True)

    subjects = {
        "chinese": {"enabled": False, "choice_questions": []},
        "math": {
            "enabled": True,
            "choice_questions": [
                asdict(ExamChoiceQuestion(id=item.id, question=item.question, options=item.options, score=3))
                for item in math_bank.questions[:5]
            ],
        },
        "english": {"enabled": False, "choice_questions": []},
        "computer_basic": {
            "enabled": True,
            "choice_questions": [
                asdict(ExamChoiceQuestion(id=item.id, question=item.question, options=item.options, score=3))
                for item in computer_bank.questions[:15]
            ],
        },
        "python": {"enabled": False, "choice_questions": []},
        "mysql": {"enabled": False, "choice_questions": []},
    }
    answers = {
        "chinese": {"enabled": False, "choice_questions": []},
        "math": {
            "enabled": True,
            "choice_questions": [
                asdict(ExamAnswerQuestion(id=item.id, answer=item.answer, explanation=item.explanation))
                for item in math_bank.questions[:5]
            ],
        },
        "english": {"enabled": False, "choice_questions": []},
        "computer_basic": {
            "enabled": True,
            "choice_questions": [
                asdict(ExamAnswerQuestion(id=item.id, answer=item.answer, explanation=item.explanation))
                for item in computer_bank.questions[:15]
            ],
        },
        "python": {"enabled": False, "choice_questions": []},
        "mysql": {"enabled": False, "choice_questions": []},
    }

    metadata = {
        "exam_id": "demo_exam_001",
        "exam_name": "测试考试",
        "start_time": "2026-04-05T08:00:00",
        "end_time": "2026-12-31T23:59:00",
        "duration_minutes": 60,
        "exam_password": "",
        "show_score_immediately": 1,
        "show_correct_answer": 1,
        "disallow_reentry_after_submit": 1,
    }
    JsonStore(question_file, metadata | {"subjects": subjects}).save(metadata | {"subjects": subjects})
    JsonStore(answer_file, metadata | {"subjects": answers}).save(metadata | {"subjects": answers})
    JsonStore(user_file, {"records": []}).save({"records": []})
