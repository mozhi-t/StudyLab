from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from config.settings import FAVORITE_DIR, FAVORITE_INDEX_FILE, QUESTION_BANK_DIR, QUESTION_BANK_INDEX_FILE, SUBJECTS, WRONG_DIR, WRONG_INDEX_FILE
from core.datetime_utils import format_datetime, parse_datetime
from core.json_store import JsonStore
from models.favorite_question import FavoriteIndexItem, FavoriteQuestion
from models.question_bank import BankMeta, QuestionBank
from models.wrong_question import WrongIndexItem, WrongQuestion


class GlobalIndexChecker:
    def check_and_repair(self) -> dict:
        issue_count = 0
        invalid_times: list[dict[str, str]] = []
        issue_count += self._repair_index(QUESTION_BANK_INDEX_FILE, self._build_question_index(), key_field="name", required_fields=("name", "subject", "create_time"))
        issue_count += self._sync_question_bank_times(invalid_times)
        issue_count += self._repair_index(
            WRONG_INDEX_FILE,
            self._build_wrong_index(),
            key_field="question_id",
            required_fields=("question_id", "subject", "question_content", "error_count"),
        )
        issue_count += self._repair_index(FAVORITE_INDEX_FILE, self._build_favorite_index(), key_field="question_id", required_fields=("question_id", "subject", "question_content"))
        return {"issue_count": issue_count, "invalid_times": invalid_times}

    def collect_invalid_question_bank_times(self) -> list[dict[str, str]]:
        invalid_times: list[dict[str, str]] = []
        for subject in SUBJECTS:
            subject_dir = QUESTION_BANK_DIR / subject
            for file_path in sorted(subject_dir.glob("*.json")):
                raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
                name = raw.get("name") or file_path.stem
                create_time = raw.get("create_time")
                if not isinstance(create_time, str) or not parse_datetime(create_time):
                    invalid_times.append({"subject": subject, "name": str(name)})
        return invalid_times

    def _build_question_index(self) -> dict[str, list[dict]]:
        result = {subject: [] for subject in SUBJECTS}
        for subject in SUBJECTS:
            subject_dir = QUESTION_BANK_DIR / subject
            for file_path in sorted(subject_dir.glob("*.json")):
                raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
                bank = QuestionBank(**raw)
                create_time = self._raw_bank_time(raw.get("create_time"))
                if create_time is None:
                    create_time = str(bank.create_time)
                result[subject].append(asdict(BankMeta(name=bank.name, subject=bank.subject, create_time=create_time)))
        return result

    def _build_wrong_index(self) -> dict[str, list[dict]]:
        result = {subject: [] for subject in SUBJECTS}
        for subject in SUBJECTS:
            store = JsonStore(WRONG_DIR / f"{subject}.json", [], "E010", "E011", "E012")
            for item in store.load():
                wrong = WrongQuestion(**item)
                result[subject].append(
                    asdict(WrongIndexItem(question_id=wrong.question_id, subject=wrong.subject, question_content=wrong.question[:40], error_count=wrong.error_count))
                )
        return result

    def _build_favorite_index(self) -> dict[str, list[dict]]:
        result = {subject: [] for subject in SUBJECTS}
        for subject in SUBJECTS:
            store = JsonStore(FAVORITE_DIR / f"{subject}.json", [], "E013", "E014", "E015")
            for item in store.load():
                favorite = FavoriteQuestion(**item)
                result[subject].append(asdict(FavoriteIndexItem(question_id=favorite.question_id, subject=favorite.subject, question_content=favorite.question[:40])))
        return result

    def _repair_index(self, path: Path, expected: dict[str, list[dict]], *, key_field: str, required_fields: tuple[str, ...]) -> int:
        raw, format_broken = self._load_raw_index(path)
        issues = 1 if format_broken else 0

        if not isinstance(raw, dict):
            raw = {}
            issues += 1

        for subject in SUBJECTS:
            subject_items = raw.get(subject)
            expected_items = expected[subject]
            if not isinstance(subject_items, list):
                issues += 1
                continue
            issues += self._count_subject_issues(subject_items, expected_items, key_field, required_fields)

        extra_subjects = [key for key in raw.keys() if key not in SUBJECTS]
        issues += len(extra_subjects)

        if self._normalize_index(raw) != expected:
            JsonStore(path, expected).save(expected)

        return issues

    def _count_subject_issues(self, subject_items: list, expected_items: list[dict], key_field: str, required_fields: tuple[str, ...]) -> int:
        issues = 0
        normalized_items: dict[str, dict] = {}
        for item in subject_items:
            if not isinstance(item, dict):
                issues += 1
                continue
            if any(field not in item for field in required_fields):
                issues += 1
                continue
            key = item.get(key_field)
            if not isinstance(key, str) or not key:
                issues += 1
                continue
            if key in normalized_items:
                issues += 1
                continue
            normalized_items[key] = item

        expected_map = {item[key_field]: item for item in expected_items}
        missing_keys = [key for key in expected_map if key not in normalized_items]
        extra_keys = [key for key in normalized_items if key not in expected_map]
        changed_keys = [key for key in expected_map if key in normalized_items and normalized_items[key] != expected_map[key]]
        issues += len(missing_keys) + len(extra_keys) + len(changed_keys)
        return issues

    def _load_raw_index(self, path: Path) -> tuple[object, bool]:
        if not path.exists():
            return {}, True
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file), False
        except (OSError, json.JSONDecodeError):
            return {}, True

    def _normalize_index(self, raw) -> dict[str, list[dict]]:
        if not isinstance(raw, dict):
            return {subject: [] for subject in SUBJECTS}
        normalized: dict[str, list[dict]] = {}
        for subject in SUBJECTS:
            items = raw.get(subject)
            normalized[subject] = items if isinstance(items, list) else []
        return normalized

    def _sync_question_bank_times(self, invalid_times: list[dict[str, str]]) -> int:
        raw, _format_broken = self._load_raw_index(QUESTION_BANK_INDEX_FILE)
        if not isinstance(raw, dict):
            return 0

        issue_count = 0
        changed = False
        for subject in SUBJECTS:
            items = raw.get(subject)
            if not isinstance(items, list):
                continue
            normalized_items: list[dict] = []
            for item in items:
                if not isinstance(item, dict):
                    normalized_items.append(item)
                    continue
                name = item.get("name")
                if not isinstance(name, str) or not name:
                    normalized_items.append(item)
                    continue
                bank_time = self._load_bank_time(subject, name)
                if bank_time is None:
                    invalid_times.append({"subject": subject, "name": name})
                    normalized_items.append(item)
                    continue
                if item.get("create_time") != bank_time:
                    item = item | {"create_time": bank_time}
                    issue_count += 1
                    changed = True
                normalized_items.append(item)
            raw[subject] = normalized_items

        if changed:
            JsonStore(QUESTION_BANK_INDEX_FILE, raw).save(raw)
        return issue_count

    def _load_bank_time(self, subject: str, name: str) -> str | None:
        file_path = QUESTION_BANK_DIR / subject / f"{name}.json"
        if not file_path.exists():
            return None
        raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
        return self._raw_bank_time(raw.get("create_time"))

    def _raw_bank_time(self, create_time) -> str | None:
        if not isinstance(create_time, str) or not parse_datetime(create_time):
            return None
        return create_time
