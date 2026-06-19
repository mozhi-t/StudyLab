from __future__ import annotations

import os
import re

from PyQt6.QtGui import QColor
from qfluentwidgets import Theme, setTheme, setThemeColor

from core.json_store import JsonStore
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE


def _read_settings() -> dict:
    return JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE).load()


def apply_theme() -> None:
    settings = _read_settings()
    theme_name = settings.get("theme", "Auto")
    theme_map = {
        "Light": Theme.LIGHT,
        "Dark": Theme.DARK,
        "Auto": Theme.AUTO,
    }
    setTheme(theme_map.get(theme_name, Theme.AUTO))
    color = settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"])
    setThemeColor(QColor(color))


def parse_ui_scale(value: str) -> float | None:
    """Return a scale factor for an ui_scale option, or None to follow the system."""
    if not value or value == "跟随系统设置":
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*%?\s*$", value)
    if not match:
        return None
    factor = float(match.group(1)) / 100
    return factor if factor > 0 else None


def apply_ui_scale() -> None:
    """Apply the configured UI scale before QApplication is created.

    Qt reads QT_SCALE_FACTOR at startup, so this must run before constructing the
    application object to take effect.
    """
    factor = parse_ui_scale(_read_settings().get("ui_scale", "跟随系统设置"))
    if factor is None:
        os.environ.pop("QT_SCALE_FACTOR", None)
    else:
        os.environ["QT_SCALE_FACTOR"] = str(factor)
