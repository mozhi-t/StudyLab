from __future__ import annotations

import json
from dataclasses import asdict

from config.settings import QUESTION_BANK_DIR, QUESTION_BANK_INDEX_NAME, SUBJECTS, question_bank_index_file
from core.base.datetime_utils import parse_datetime
from core.base.json_store import JsonStore
from models.base import BankMeta
from models.choice import QuestionBank
from models.python.question import PythonQuestionBank


class GlobalIndexChecker:
    def check_and_repair(self) -> dict:
        issue_count = 0
        invalid_times: list[dict[str, str]] = []
        issue_count += self._repair_question_indexes(self._build_question_index())
        issue_count += self._sync_question_bank_times(invalid_times)
        return {"issue_count": issue_count, "invalid_times": invalid_times}

    def collect_invalid_question_bank_times(self) -> list[dict[str, str]]:
        invalid_times: list[dict[str, str]] = []
        for subject in SUBJECTS:
            subject_dir = QUESTION_BANK_DIR / subject
            for file_path in sorted(subject_dir.glob("*.json")):
                if file_path.name == QUESTION_BANK_INDEX_NAME:
                    continue
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
                if file_path.name == QUESTION_BANK_INDEX_NAME:
                    continue
                raw = JsonStore(file_path, {}, "E006", "E007", "E009").load()
                bank = PythonQuestionBank(**raw) if raw.get("question_type") == "python_programming" else QuestionBank(**raw)
                create_time = self._raw_bank_time(raw.get("create_time"))
                if create_time is None:
                    create_time = str(bank.create_time)
                result[subject].append(asdict(BankMeta(name=bank.name, subject=bank.subject, create_time=create_time)))
        return result

    def _repair_question_indexes(self, expected: dict[str, list[dict]]) -> int:
        issues = 0
        for subject in SUBJECTS:
            path = question_bank_index_file(subject)
            raw, format_broken = self._load_raw_index(path)
            subject_issues = 1 if format_broken else 0
            expected_items = expected[subject]

            if not isinstance(raw, list):
                raw = []
                subject_issues += 1
            else:
                subject_issues += self._count_subject_issues(raw, expected_items, "name", ("name", "subject", "create_time"))

            if raw != expected_items:
                JsonStore(path, expected_items).save(expected_items)

            issues += subject_issues
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

    def _sync_question_bank_times(self, invalid_times: list[dict[str, str]]) -> int:
        issue_count = 0
        for subject in SUBJECTS:
            path = question_bank_index_file(subject)
            items, _format_broken = self._load_raw_index(path)
            if not isinstance(items, list):
                continue
            changed = False
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

            if changed:
                JsonStore(path, normalized_items).save(normalized_items)
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
