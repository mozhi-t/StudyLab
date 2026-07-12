from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RunResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    timed_out: bool = False


@dataclass(frozen=True)
class JudgeDetail:
    point_id: str
    name: str
    earned: float
    possible: float
    passed: bool
    message: str


@dataclass(frozen=True)
class PythonJudgeResult:
    earned: float
    possible: float
    details: list[JudgeDetail] = field(default_factory=list)
    runnable: bool = False
    message: str = ""
