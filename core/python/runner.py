from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from models.python.grading import RunResult


class PythonRunner:
    def __init__(self, max_output_chars: int = 65536):
        self.max_output_chars = max_output_chars

    def run(self, file_path: Path, stdin: str = "", timeout_seconds: float = 3.0) -> RunResult:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-X", "utf8", file_path.name],
                cwd=file_path.parent,
                input=stdin,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return RunResult(
                success=completed.returncode == 0,
                stdout=completed.stdout[: self.max_output_chars],
                stderr=completed.stderr[: self.max_output_chars],
                exit_code=completed.returncode,
                duration_seconds=time.perf_counter() - started,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return RunResult(False, stdout[: self.max_output_chars], stderr[: self.max_output_chars], None, time.perf_counter() - started, True)
        except OSError as exc:
            return RunResult(False, "", str(exc), None, time.perf_counter() - started)
