from __future__ import annotations

from datetime import datetime


DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)


def parse_datetime(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def format_datetime(value: str | datetime | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value.strftime(DISPLAY_DATETIME_FORMAT)

    parsed = parse_datetime(value)
    if parsed:
        return parsed.strftime(DISPLAY_DATETIME_FORMAT)
    return str(value) if value else fallback


def now_text() -> str:
    return datetime.now().replace(microsecond=0).strftime(DISPLAY_DATETIME_FORMAT)
