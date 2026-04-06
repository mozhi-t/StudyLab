from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import LOG_DIR


def get_exam_logger() -> logging.Logger:
    logger = logging.getLogger("exam_server")
    if logger.handlers:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"exam_server_{datetime.now().strftime('%Y%m%d')}.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def _normalize_value(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\n", "\\n").replace("\r", "\\r")
    if not text:
        return '""'
    if any(char.isspace() for char in text):
        return f'"{text}"'
    return text


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    parts = [f"事件={event}"]
    for key in sorted(fields):
        parts.append(f"{key}={_normalize_value(fields[key])}")
    logger.log(level, " ".join(parts))
