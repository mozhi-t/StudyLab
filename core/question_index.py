from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from config.settings import PAGE_SIZE, QUESTION_BANK_DIR, QUESTION_BANK_INDEX_FILE, QUESTION_INDEX_TEMPLATE, SUBJECTS
from core.errors import raise_app_error
from core.json_store import JsonStore
from models.question_bank import BankMeta, QuestionBank


class QuestionIndexManager:
    def __init__(self):
        self.store = JsonStore(QUESTION_BANK_INDEX_FILE, QUESTION_INDEX_TEMPLATE, "E003", "E004", "E009")

    def load_index(self) -> dict[str, list[BankMeta]]:
        raw = self.store.load()
        return {
            subject: [BankMeta(**item) for item in raw.get(subject, [])]
            for subject in SUBJECTS
        }

    def save_index(self, index: dict[str, list[BankMeta]]) -> None:
        self.store.save({subject: [asdict(item) for item in items] for subject, items in index.items()})

    def list_banks(self, subject: str | None = None, keyword: str = "", page: int = 1, page_size: int = PAGE_SIZE) -> tuple[list[BankMeta], int]:
        index = self.load_index()
        items = []
        for current_subject, entries in index.items():
            if subject and current_subject != subject:
                continue
            items.extend(entries)
        keyword_lower = keyword.strip().lower()
        if keyword_lower:
            items = [item for item in items if keyword_lower in item.name.lower()]
        items.sort(key=lambda item: item.create_time, reverse=True)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return items[start:end], len(items)

    def refresh_index(self) -> dict[str, int]:
        try:
            new_index = {subject: [] for subject in SUBJECTS}
            for subject in SUBJECTS:
                subject_dir = QUESTION_BANK_DIR / subject
                for file_path in sorted(subject_dir.glob("*.json")):
                    bank = self._read_bank(file_path)
                    new_index[subject].append(
                        BankMeta(
                            name=bank.name,
                            subject=bank.subject,
                            create_time=bank.create_time,
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
            index = self.load_index()
            index[subject] = [item for item in index[subject] if item.name != bank_name]
            self.save_index(index)
        except OSError as exc:
            raise_app_error("E008", str(exc))

    def load_bank(self, subject: str, bank_name: str) -> QuestionBank:
        file_path = QUESTION_BANK_DIR / subject / f"{bank_name}.json"
        if not file_path.exists():
            raise_app_error("E024", f"{subject}/{bank_name}")
        return self._read_bank(file_path)

    def add_downloaded_bank(self, payload: dict) -> None:
        bank = QuestionBank(**payload)
        file_path = QUESTION_BANK_DIR / bank.subject / f"{bank.name}.json"
        JsonStore(file_path, payload, "E006", "E007", "E009").save(payload)
        index = self.load_index()
        index[bank.subject] = [item for item in index[bank.subject] if item.name != bank.name]
        index[bank.subject].append(BankMeta(name=bank.name, subject=bank.subject, create_time=bank.create_time))
        self.save_index(index)

    def _read_bank(self, file_path: Path) -> QuestionBank:
        raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
        try:
            return QuestionBank(**raw)
        except TypeError as exc:
            raise_app_error("E007", str(exc))
