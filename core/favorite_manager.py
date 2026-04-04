from __future__ import annotations

from dataclasses import asdict

from config.settings import FAVORITE_DIR, FAVORITE_INDEX_FILE, FAVORITE_INDEX_TEMPLATE, PAGE_SIZE, SUBJECTS
from core.errors import raise_app_error
from core.json_store import JsonStore
from models.favorite_question import FavoriteIndexItem, FavoriteQuestion


class FavoriteManager:
    def __init__(self):
        self.index_store = JsonStore(FAVORITE_INDEX_FILE, FAVORITE_INDEX_TEMPLATE, "E013", "E014", "E015")

    def _subject_store(self, subject: str) -> JsonStore:
        return JsonStore(FAVORITE_DIR / f"{subject}.json", [], "E013", "E014", "E015")

    def load_index(self) -> dict[str, list[FavoriteIndexItem]]:
        raw = self.index_store.load()
        return {
            subject: [FavoriteIndexItem(**item) for item in raw.get(subject, [])]
            for subject in SUBJECTS
        }

    def toggle_favorite(self, payload: FavoriteQuestion) -> bool:
        store = self._subject_store(payload.subject)
        data = [FavoriteQuestion(**item) for item in store.load()]
        existing = next((item for item in data if item.question_id == payload.question_id), None)
        if existing:
            try:
                data = [item for item in data if item.question_id != payload.question_id]
            except OSError as exc:
                raise_app_error("E016", str(exc))
            is_favorite = False
        else:
            data.append(payload)
            is_favorite = True
        store.save([asdict(item) for item in data])
        self._rebuild_subject_index(payload.subject, data)
        return is_favorite

    def list_favorites(self, subject: str | None = None, keyword: str = "", page: int = 1, page_size: int = PAGE_SIZE) -> tuple[list[FavoriteQuestion], int]:
        items: list[FavoriteQuestion] = []
        subjects = [subject] if subject else list(SUBJECTS)
        for current in subjects:
            items.extend(FavoriteQuestion(**item) for item in self._subject_store(current).load())
        keyword_lower = keyword.strip().lower()
        if keyword_lower:
            items = [item for item in items if keyword_lower in item.question.lower() or keyword_lower in item.bank_name.lower()]
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return items[start:end], len(items)

    def get_question(self, subject: str, question_id: str) -> FavoriteQuestion | None:
        for item in self._subject_store(subject).load():
            question = FavoriteQuestion(**item)
            if question.question_id == question_id:
                return question
        return None

    def _rebuild_subject_index(self, subject: str, data: list[FavoriteQuestion]) -> None:
        index = self.load_index()
        index[subject] = [
            FavoriteIndexItem(
                question_id=item.question_id,
                subject=item.subject,
                question_content=item.question[:40],
            )
            for item in data
        ]
        self.index_store.save({name: [asdict(entry) for entry in entries] for name, entries in index.items()})
