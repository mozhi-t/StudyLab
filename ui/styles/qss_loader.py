from __future__ import annotations

from pathlib import Path


def load_qss(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
