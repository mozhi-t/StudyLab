from __future__ import annotations

from PyQt6.QtGui import QColor
from qfluentwidgets import Theme, setTheme, setThemeColor

from .json_store import JsonStore
from .paths import EXAM_SERVER_DIR


APP_SETTINGS_FILE = EXAM_SERVER_DIR / "app_settings.json"
DEFAULT_THEME = "Auto"
DEFAULT_THEME_COLOR = "#0f52aa"
DEFAULT_LANGUAGE = "zh_CN"
APP_SETTINGS_TEMPLATE = {
    "theme": DEFAULT_THEME,
    "theme_color": DEFAULT_THEME_COLOR,
    "language": DEFAULT_LANGUAGE,
    "ui_scale": "跟随系统设置",
}


def apply_theme() -> None:
    settings = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE).load()
    theme_name = settings.get("theme", "Auto")
    theme_map = {
        "Light": Theme.LIGHT,
        "Dark": Theme.DARK,
        "Auto": Theme.AUTO,
    }
    setTheme(theme_map.get(theme_name, Theme.AUTO))
    setThemeColor(QColor(settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"])))
