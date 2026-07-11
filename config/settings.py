from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "StudyLab"
APP_AUTHOR = "MoZhi"
APP_VERSION = "Beta"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_FILE = DATA_DIR / "studylab.db"
QUESTION_BANK_DIR = BASE_DIR / "question_bank"
QUESTION_BANK_INDEX_NAME = "index.json"
EXAM_DIR = BASE_DIR / "exam"
LAN_EXAM_DIR = EXAM_DIR / "LAN"

SETTINGS_DIR = BASE_DIR / "config"
APP_SETTINGS_FILE = SETTINGS_DIR / "app_settings.json"

SUBJECTS = {
    "chinese": "语文",
    "math": "数学",
    "english": "英语",
    "computer_basic": "计算机基础",
    "python": "Python",
    "mysql": "MySQL",
}

PAGE_SIZE = 50
DEFAULT_THEME = "Auto"
DEFAULT_THEME_COLOR = "#0f52aa"
DEFAULT_LANGUAGE = "zh_CN"

APP_SETTINGS_TEMPLATE = {
    "theme": DEFAULT_THEME,
    "theme_color": DEFAULT_THEME_COLOR,
    "language": DEFAULT_LANGUAGE,
    "ui_scale": "跟随系统设置",
    "home_page_style": "样式一",
    "window_memory_mode": "default",
    "window_geometry": {},
    "daily_question_goal": 50,
    "answer_shortcuts": {
        "prev_question": "1",
        "next_question": "2",
        "mark_question": "3",
    },
    "eye_care": {
        "enabled": True,
        "interval_minutes": 20,
        "reminder_mode": "dialog",
        "first_shown": False,
    },
}


QUESTION_INDEX_TEMPLATE = []


def question_bank_index_file(subject: str) -> Path:
    return QUESTION_BANK_DIR / subject / QUESTION_BANK_INDEX_NAME
