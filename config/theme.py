from __future__ import annotations

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
