from __future__ import annotations

from .defaults import ACCOUNTS_TEMPLATE, CONNECTION_TEMPLATE, SERVER_CONFIG_TEMPLATE
from .json_store import JsonStore
from .paths import ACCOUNTS_FILE, CONFIG_FILE, CONNECTION_FILE, EXAM_BANK_DIR, LOG_DIR


def ensure_server_files() -> None:
    EXAM_BANK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JsonStore(CONFIG_FILE, SERVER_CONFIG_TEMPLATE).ensure()
    JsonStore(ACCOUNTS_FILE, ACCOUNTS_TEMPLATE).ensure()
    JsonStore(CONNECTION_FILE, CONNECTION_TEMPLATE).ensure()
