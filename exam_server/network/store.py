from __future__ import annotations

import shutil
from pathlib import Path

try:
    from ..core.datetime_utils import format_datetime, now_text, parse_datetime
    from ..core.defaults import ACCOUNTS_TEMPLATE, CONNECTION_TEMPLATE, SERVER_CONFIG_TEMPLATE
    from ..core.json_store import JsonStore
    from ..core.paths import ACCOUNTS_FILE, CONFIG_FILE, CONNECTION_FILE, EXAM_BANK_DIR
    from ..core.utils import safe_filename_part
    from ..data.models import ExamAnswerSheet, ExamPaper
except ImportError:
    from core.datetime_utils import format_datetime, now_text, parse_datetime
    from core.defaults import ACCOUNTS_TEMPLATE, CONNECTION_TEMPLATE, SERVER_CONFIG_TEMPLATE
    from core.json_store import JsonStore
    from core.paths import ACCOUNTS_FILE, CONFIG_FILE, CONNECTION_FILE, EXAM_BANK_DIR
    from core.utils import safe_filename_part
    from data.models import ExamAnswerSheet, ExamPaper


class ExamServerStore:
    def __init__(self):
        self.config_store = JsonStore(CONFIG_FILE, SERVER_CONFIG_TEMPLATE)
        self.accounts_store = JsonStore(ACCOUNTS_FILE, ACCOUNTS_TEMPLATE)
        self.connection_store = JsonStore(CONNECTION_FILE, CONNECTION_TEMPLATE)

    def load_config(self) -> dict:
        return self.config_store.load()

    def save_config(self, data: dict) -> None:
        self.config_store.save(data)

    def load_accounts(self) -> dict:
        return self.accounts_store.load()

    def list_exam_dirs(self) -> list[Path]:
        if not EXAM_BANK_DIR.exists():
            return []
        return sorted([item for item in EXAM_BANK_DIR.iterdir() if item.is_dir()], key=lambda item: item.name.lower())

    def list_exams(self) -> list[dict]:
        exams = []
        for exam_dir in self.list_exam_dirs():
            question_file = exam_dir / "exam_questions.json"
            if not question_file.exists():
                continue
            paper = ExamPaper(**JsonStore(question_file, {}).load())
            exams.append(
                {
                    "exam_id": paper.exam_id,
                    "exam_name": paper.exam_name,
                    "start_time": format_datetime(paper.start_time),
                    "end_time": format_datetime(paper.end_time),
                    "duration_minutes": paper.duration_minutes,
                    "exam_password": paper.exam_password,
                    "show_score_immediately": paper.show_score_immediately,
                    "show_correct_answer": paper.show_correct_answer,
                    "disallow_reentry_after_submit": paper.disallow_reentry_after_submit,
                    "enabled_subjects": [name for name, subject in paper.subjects.items() if subject.enabled and subject.choice_questions],
                    "folder_name": exam_dir.name,
                }
            )
        exams.sort(key=lambda item: parse_datetime(item["start_time"]) or item["start_time"])
        return exams

    def load_exam_paper(self, exam_name: str) -> dict:
        return JsonStore(EXAM_BANK_DIR / exam_name / "exam_questions.json", {}).load()

    def load_exam_answers(self, exam_name: str) -> dict:
        return JsonStore(EXAM_BANK_DIR / exam_name / "exam_answers.json", {}).load()

    def save_exam_metadata(self, exam_name: str, metadata: dict) -> None:
        question_file = EXAM_BANK_DIR / exam_name / "exam_questions.json"
        answer_file = EXAM_BANK_DIR / exam_name / "exam_answers.json"
        question_data = JsonStore(question_file, {}).load()
        answer_data = JsonStore(answer_file, {}).load()
        for key in [
            "exam_id",
            "exam_name",
            "start_time",
            "end_time",
            "duration_minutes",
            "exam_password",
            "show_score_immediately",
            "show_correct_answer",
            "disallow_reentry_after_submit",
        ]:
            question_data[key] = metadata[key]
            answer_data[key] = metadata[key]
        JsonStore(question_file, question_data).save(question_data)
        JsonStore(answer_file, answer_data).save(answer_data)
        if exam_name == metadata["exam_name"]:
            return
        old_dir = EXAM_BANK_DIR / exam_name
        new_dir = EXAM_BANK_DIR / metadata["exam_name"]
        old_dir.rename(new_dir)
        old_user = new_dir / f"{exam_name}_user.json"
        new_user = new_dir / f"{metadata['exam_name']}_user.json"
        if old_user.exists():
            old_user.rename(new_user)

    def delete_exam(self, exam_name: str) -> None:
        exam_dir = EXAM_BANK_DIR / exam_name
        if not exam_dir.exists():
            return
        shutil.rmtree(exam_dir)

    def load_connections(self) -> dict:
        return self.connection_store.load()

    def save_connections(self, payload: dict) -> None:
        self.connection_store.save(payload)

    def upsert_connection(self, item: dict) -> None:
        data = self.load_connections()
        connections = data.get("connections", [])
        for index, current in enumerate(connections):
            if current.get("client_id") == item.get("client_id"):
                connections[index] = current | item
                self.save_connections({"connections": connections})
                return
        connections.append(item)
        self.save_connections({"connections": connections})

    def remove_connection(self, client_id: str) -> None:
        data = self.load_connections()
        connections = [item for item in data.get("connections", []) if item.get("client_id") != client_id]
        self.save_connections({"connections": connections})

    def exam_user_store(self, exam_name: str) -> JsonStore:
        return JsonStore(EXAM_BANK_DIR / exam_name / f"{exam_name}_user.json", {"records": []})

    def exam_submission_dir(self, exam_name: str) -> Path:
        directory = EXAM_BANK_DIR / exam_name / "user_submission"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def upsert_exam_record(self, exam_name: str, record: dict) -> None:
        store = self.exam_user_store(exam_name)
        data = store.load()
        records = data.get("records", [])
        for index, item in enumerate(records):
            if item.get("client_id") == record.get("client_id"):
                records[index] = item | record
                store.save({"records": records})
                return
        records.append(record)
        store.save({"records": records})

    def save_submission_payload(self, exam_name: str, payload: dict, username: str, client_id: str, device_name: str) -> Path:
        filename = (
            f"{safe_filename_part(username)}_"
            f"{safe_filename_part(client_id)}_"
            f"{safe_filename_part(device_name)}_submission.json"
        )
        target = self.exam_submission_dir(exam_name) / filename
        JsonStore(target, payload).save(payload)
        return target

    def submission_payload_path(self, exam_name: str, username: str, client_id: str, device_name: str) -> Path:
        filename = (
            f"{safe_filename_part(username)}_"
            f"{safe_filename_part(client_id)}_"
            f"{safe_filename_part(device_name)}_submission.json"
        )
        return self.exam_submission_dir(exam_name) / filename

    def load_submission_payload(self, exam_name: str, record: dict) -> dict:
        target = self.submission_payload_path(
            exam_name,
            str(record.get("username", "")),
            str(record.get("client_id", "")),
            str(record.get("device_name", "")),
        )
        if not target.exists():
            candidates = sorted(
                self.exam_submission_dir(exam_name).glob(f"*_{safe_filename_part(str(record.get('client_id', '')), 'unknown')}_*_submission.json")
            )
            if not candidates:
                raise FileNotFoundError(f"未找到交卷数据文件: {target.name}")
            target = candidates[0]
        return JsonStore(target, {}).load()

    def list_submitted_scores(self, exam_name: str) -> list[dict]:
        records = self.exam_user_store(exam_name).load().get("records", [])
        submitted = [item for item in records if item.get("submission_state") == "submitted"]
        submitted.sort(
            key=lambda item: (
                int(item.get("score") or 0),
                format_datetime(item.get("submitted_at")) or "",
            ),
            reverse=True,
        )
        return submitted

    def score_exam(self, exam_name: str, answers_payload: dict) -> dict:
        answer_sheet = ExamAnswerSheet(**self.load_exam_answers(exam_name))
        paper = ExamPaper(**self.load_exam_paper(exam_name))
        submitted = answers_payload.get("subjects", {})
        total_score = 0
        total_possible = 0
        details: dict[str, dict] = {}
        for subject_name, subject in paper.subjects.items():
            if not subject.enabled or not subject.choice_questions:
                continue
            submitted_questions = submitted.get(subject_name, {}).get("choice_questions", [])
            submitted_map = {int(item["id"]): item.get("selected", "") for item in submitted_questions}
            answer_subject = answer_sheet.subjects.get(subject_name)
            answer_map = {item.id: item for item in (answer_subject.choice_questions if answer_subject else [])}
            details[subject_name] = {"choice_questions": []}
            for question in subject.choice_questions:
                total_possible += question.score
                answer_item = answer_map.get(question.id)
                selected = submitted_map.get(question.id, "")
                is_correct = bool(answer_item and selected == answer_item.answer)
                if is_correct:
                    total_score += question.score
                details[subject_name]["choice_questions"].append(
                    {
                        "id": question.id,
                        "question": question.question,
                        "options": question.options,
                        "score": question.score,
                        "selected": selected,
                        "correct_answer": answer_item.answer if answer_item else "",
                        "explanation": answer_item.explanation if answer_item else "",
                        "is_correct": is_correct,
                    }
                )
        return {
            "exam_id": paper.exam_id,
            "exam_name": paper.exam_name,
            "score": total_score,
            "total_score": total_possible,
            "show_score_immediately": paper.show_score_immediately,
            "show_correct_answer": paper.show_correct_answer,
            "details": details,
            "submitted_at": now_text(),
        }

    def build_submission_result(self, exam_name: str, record: dict) -> dict:
        payload = self.load_submission_payload(exam_name, record)
        result = self.score_exam(exam_name, payload)
        result["submitted_at"] = format_datetime(record.get("submitted_at"), result["submitted_at"])
        return result
