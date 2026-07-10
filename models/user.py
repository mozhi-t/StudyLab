from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    nickname: str = ""
    total_questions: int = 0
    total_study_seconds: int = 0
    total_study_days: int = 0
    continuous_days: int = 0
    max_continuous_days: int = 0
    last_study_date: str | None = None
    created_at: str = ""
    updated_at: str = ""
