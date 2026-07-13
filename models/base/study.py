from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    earned: float
    possible: float
    answered_count: int = 1


@dataclass
class DailyStudyStats:
    study_date: str
    answered_count: int = 0
    study_seconds: int = 0
    session_count: int = 0
    score_earned: float = 0
    score_possible: float = 0


@dataclass
class StudySession:
    id: int
    subject: str
    source_type: str
    source_key: str | None
    source_name: str
    started_at: str
    ended_at: str | None
    duration_seconds: int
    answered_count: int
    score_earned: float
    score_possible: float


@dataclass
class SubjectAbility:
    subject: str
    ability_index: float
    sample_count: int
    score_earned: float
    score_possible: float
    updated_at: str
