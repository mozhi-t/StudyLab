from __future__ import annotations

from pathlib import Path

APP_NAME = "Study Lab"
APP_AUTHOR = "MoZhi"
APP_VERSION = "Beta"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
USER_FILE = DATA_DIR / "user.json"
QUESTION_BANK_DIR = BASE_DIR / "question_bank"
QUESTION_BANK_INDEX_FILE = QUESTION_BANK_DIR / "index.json"
WRONG_DIR = BASE_DIR / "wrong"
WRONG_INDEX_FILE = WRONG_DIR / "index.json"
FAVORITE_DIR = BASE_DIR / "favorite"
FAVORITE_INDEX_FILE = FAVORITE_DIR / "index.json"

SETTINGS_DIR = BASE_DIR / "config"
APP_SETTINGS_FILE = SETTINGS_DIR / "app_settings.json"

SUBJECTS = {
    "chinese": "语文",
    "math": "数学",
    "english": "英语",
    "computer_basic": "机基",
    "python": "Python",
    "mysql": "MySQL",
}

PAGE_SIZE = 50
DEFAULT_THEME = "Auto"
DEFAULT_THEME_COLOR = "#009faa"
DEFAULT_LANGUAGE = "zh_CN"

USER_TEMPLATE = {
    "nickname": "",
    "total_questions": 0,
    "total_study_days": 0,
    "continuous_days": 0,
    "max_continuous_days": 0,
    "last_study_date": None,
}

APP_SETTINGS_TEMPLATE = {
    "theme": DEFAULT_THEME,
    "theme_color": DEFAULT_THEME_COLOR,
    "language": DEFAULT_LANGUAGE,
    "ui_scale": "跟随系统设置",
}


def empty_subject_map(default_factory):
    return {subject: default_factory() for subject in SUBJECTS}


QUESTION_INDEX_TEMPLATE = empty_subject_map(list)
WRONG_INDEX_TEMPLATE = empty_subject_map(list)
FAVORITE_INDEX_TEMPLATE = empty_subject_map(list)
