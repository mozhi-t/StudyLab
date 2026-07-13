from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from config.settings import PAGE_SIZE, QUESTION_BANK_DIR, QUESTION_BANK_INDEX_NAME, QUESTION_INDEX_TEMPLATE, SUBJECTS, question_bank_index_file
from core.base.datetime_utils import format_datetime, parse_datetime
from core.base.errors import raise_app_error
from core.base.json_store import JsonStore
from models.base import BankMeta
from models.choice import QuestionBank
from models.python.question import PythonQuestionBank


class QuestionIndexManager:
    def _subject_store(self, subject: str) -> JsonStore:
        return JsonStore(question_bank_index_file(subject), QUESTION_INDEX_TEMPLATE, "E003", "E004", "E009")

    def load_index(self) -> dict[str, list[BankMeta]]:
        return {
            subject: [BankMeta(**item) for item in self._subject_store(subject).load()]
            for subject in SUBJECTS
        }

    def save_index(self, index: dict[str, list[BankMeta]]) -> None:
        for subject in SUBJECTS:
            self.save_subject_index(subject, index.get(subject, []))

    def load_subject_index(self, subject: str) -> list[BankMeta]:
        return [BankMeta(**item) for item in self._subject_store(subject).load()]

    def save_subject_index(self, subject: str, items: list[BankMeta]) -> None:
        self._subject_store(subject).save([asdict(item) for item in items])

    def list_banks(self, subject: str | None = None, keyword: str = "", page: int = 1, page_size: int = PAGE_SIZE) -> tuple[list[BankMeta], int]:
        subjects = [subject] if subject else list(SUBJECTS)
        items = []
        for current_subject in subjects:
            items.extend(self.load_subject_index(current_subject))
        keyword_lower = keyword.strip().lower()
        if keyword_lower:
            items = [item for item in items if keyword_lower in item.name.lower()]
        items.sort(key=lambda item: parse_datetime(item.create_time) or datetime.min, reverse=True)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return items[start:end], len(items)

    def refresh_index(self) -> dict[str, int]:
        try:
            new_index = {subject: [] for subject in SUBJECTS}
            for subject in SUBJECTS:
                subject_dir = QUESTION_BANK_DIR / subject
                for file_path in sorted(subject_dir.glob("*.json")):
                    if file_path.name == QUESTION_BANK_INDEX_NAME:
                        continue
                    bank = self._read_bank(file_path)
                    new_index[subject].append(
                        BankMeta(
                            name=bank.name,
                            subject=bank.subject,
                            create_time=format_datetime(bank.create_time),
                        )
                    )
            self.save_index(new_index)
            return {subject: len(items) for subject, items in new_index.items()}
        except Exception as exc:
            raise_app_error("E005", str(exc))

    def remove_bank(self, subject: str, bank_name: str) -> None:
        file_path = QUESTION_BANK_DIR / subject / f"{bank_name}.json"
        try:
            if file_path.exists():
                file_path.unlink()
            index = [item for item in self.load_subject_index(subject) if item.name != bank_name]
            self.save_subject_index(subject, index)
        except OSError as exc:
            raise_app_error("E008", str(exc))

    def load_bank(self, subject: str, bank_name: str) -> QuestionBank | PythonQuestionBank:
        file_path = QUESTION_BANK_DIR / subject / f"{bank_name}.json"
        if not file_path.exists():
            raise_app_error("E024", f"{subject}/{bank_name}")
        return self._read_bank(file_path)

    def add_downloaded_bank(self, payload: dict) -> None:
        bank = PythonQuestionBank(**payload) if payload.get("question_type") == "python_programming" else QuestionBank(**payload)
        file_path = QUESTION_BANK_DIR / bank.subject / f"{bank.name}.json"
        JsonStore(file_path, payload, "E006", "E007", "E009").save(payload)
        index = [item for item in self.load_subject_index(bank.subject) if item.name != bank.name]
        index.append(BankMeta(name=bank.name, subject=bank.subject, create_time=format_datetime(bank.create_time)))
        self.save_subject_index(bank.subject, index)

    def _read_bank(self, file_path: Path) -> QuestionBank | PythonQuestionBank:
        raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
        try:
            if "create_time" in raw:
                raw["create_time"] = format_datetime(raw.get("create_time"))
            if raw.get("question_type") == "python_programming":
                return PythonQuestionBank(**raw)
            return QuestionBank(**raw)
        except (TypeError, ValueError) as exc:
            raise_app_error("E007", str(exc))
