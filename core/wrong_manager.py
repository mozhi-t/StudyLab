from __future__ import annotations

from dataclasses import asdict

from config.settings import PAGE_SIZE, SUBJECTS, WRONG_DIR, WRONG_INDEX_FILE, WRONG_INDEX_TEMPLATE
from core.json_store import JsonStore
from models.wrong_question import WrongIndexItem, WrongQuestion


class WrongManager:
    def __init__(self):
        self.index_store = JsonStore(WRONG_INDEX_FILE, WRONG_INDEX_TEMPLATE, "E010", "E011", "E012")

    def _subject_store(self, subject: str) -> JsonStore:
        return JsonStore(WRONG_DIR / f"{subject}.json", [], "E010", "E011", "E012")

    def load_index(self) -> dict[str, list[WrongIndexItem]]:
        raw = self.index_store.load()
        return {
            subject: [WrongIndexItem(**item) for item in raw.get(subject, [])]
            for subject in SUBJECTS
        }

    def add_wrong(self, payload: WrongQuestion) -> None:
        store = self._subject_store(payload.subject)
        data = [WrongQuestion(**item) for item in store.load()]
        found = False
        for item in data:
            if item.question_id == payload.question_id:
                item.error_count += 1
                found = True
                payload = item
                break
        if not found:
            data.append(payload)
        store.save([asdict(item) for item in data])
        self._rebuild_subject_index(payload.subject, data)

    def list_wrongs(self, subject: str | None = None, keyword: str = "", page: int = 1, page_size: int = PAGE_SIZE) -> tuple[list[WrongQuestion], int]:
        items: list[WrongQuestion] = []
        subjects = [subject] if subject else list(SUBJECTS)
        for current in subjects:
            store = self._subject_store(current)
            items.extend(WrongQuestion(**item) for item in store.load())
        keyword_lower = keyword.strip().lower()
        if keyword_lower:
            items = [item for item in items if keyword_lower in item.question.lower() or keyword_lower in item.bank_name.lower()]
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return items[start:end], len(items)

    def get_question(self, subject: str, question_id: str) -> WrongQuestion | None:
        store = self._subject_store(subject)
        for item in store.load():
            wrong = WrongQuestion(**item)
            if wrong.question_id == question_id:
                return wrong
        return None

    def refresh_index(self) -> dict[str, int]:
        result = {}
        for subject in SUBJECTS:
            data = [WrongQuestion(**item) for item in self._subject_store(subject).load()]
            self._rebuild_subject_index(subject, data)
            result[subject] = len(data)
        return result

    def _rebuild_subject_index(self, subject: str, data: list[WrongQuestion]) -> None:
        index = self.load_index()
        index[subject] = [
            WrongIndexItem(
                question_id=item.question_id,
                subject=item.subject,
                question_content=item.question[:40],
                error_count=item.error_count,
            )
            for item in data
        ]
        self.index_store.save({name: [asdict(entry) for entry in entries] for name, entries in index.items()})
