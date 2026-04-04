from __future__ import annotations

from config.settings import (
    APP_SETTINGS_FILE,
    APP_SETTINGS_TEMPLATE,
    DATA_DIR,
    FAVORITE_DIR,
    FAVORITE_INDEX_FILE,
    FAVORITE_INDEX_TEMPLATE,
    QUESTION_BANK_DIR,
    QUESTION_BANK_INDEX_FILE,
    QUESTION_INDEX_TEMPLATE,
    SUBJECTS,
    USER_FILE,
    USER_TEMPLATE,
    WRONG_DIR,
    WRONG_INDEX_FILE,
    WRONG_INDEX_TEMPLATE,
)
from core.json_store import JsonStore


def bootstrap_app() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QUESTION_BANK_DIR.mkdir(parents=True, exist_ok=True)
    WRONG_DIR.mkdir(parents=True, exist_ok=True)
    FAVORITE_DIR.mkdir(parents=True, exist_ok=True)

    for subject in SUBJECTS:
        (QUESTION_BANK_DIR / subject).mkdir(parents=True, exist_ok=True)
        JsonStore(WRONG_DIR / f"{subject}.json", [], "E010", "E011", "E012").ensure()
        JsonStore(FAVORITE_DIR / f"{subject}.json", [], "E013", "E014", "E015").ensure()

    JsonStore(USER_FILE, USER_TEMPLATE, "E001", "E002", "E001").ensure()
    JsonStore(QUESTION_BANK_INDEX_FILE, QUESTION_INDEX_TEMPLATE, "E003", "E004", "E009").ensure()
    JsonStore(WRONG_INDEX_FILE, WRONG_INDEX_TEMPLATE, "E010", "E011", "E012").ensure()
    JsonStore(FAVORITE_INDEX_FILE, FAVORITE_INDEX_TEMPLATE, "E013", "E014", "E015").ensure()
    JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, "E025", "E025", "E025").ensure()
