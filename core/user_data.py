from __future__ import annotations

from dataclasses import asdict
from datetime import date

from config.settings import USER_FILE, USER_TEMPLATE
from core.datetime_utils import format_date, parse_date
from core.json_store import JsonStore
from models.user import User


class UserDataManager:
    def __init__(self):
        self.store = JsonStore(USER_FILE, USER_TEMPLATE, "E001", "E002", "E001")

    def load_user(self) -> User:
        data = self.store.load()
        return User(**data)

    def save_user(self, user: User) -> None:
        self.store.save(asdict(user))

    def record_study_session(self, answered_count: int, study_date: date | None = None) -> User:
        user = self.load_user()
        today = study_date or date.today()
        last = parse_date(user.last_study_date)

        user.total_questions += answered_count
        if last != today:
            user.total_study_days += 1
            if last and (today - last).days == 1:
                user.continuous_days += 1
            else:
                user.continuous_days = 1
            user.max_continuous_days = max(user.max_continuous_days, user.continuous_days)
            user.last_study_date = format_date(today)

        self.save_user(user)
        return user
