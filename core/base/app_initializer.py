from __future__ import annotations

from config.settings import (
    APP_SETTINGS_FILE,
    APP_SETTINGS_TEMPLATE,
    DATABASE_FILE,
    DATA_DIR,
    LAN_EXAM_DIR,
    QUESTION_BANK_DIR,
    QUESTION_INDEX_TEMPLATE,
    SUBJECTS,
    question_bank_index_file,
)
from core.base.database import DatabaseManager
from core.base.json_store import JsonStore


def initialize_app() -> DatabaseManager:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QUESTION_BANK_DIR.mkdir(parents=True, exist_ok=True)
    LAN_EXAM_DIR.mkdir(parents=True, exist_ok=True)

    for subject in SUBJECTS:
        (QUESTION_BANK_DIR / subject).mkdir(parents=True, exist_ok=True)
        JsonStore(question_bank_index_file(subject), QUESTION_INDEX_TEMPLATE, "E003", "E004", "E009").ensure()

    JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, "E025", "E025", "E025").ensure()

    database = DatabaseManager(DATABASE_FILE)
    database.initialize()
    return database
