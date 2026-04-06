from __future__ import annotations

from pathlib import Path


EXAM_SERVER_DIR = Path(__file__).resolve().parent.parent
EXAM_BANK_DIR = EXAM_SERVER_DIR / "exam_bank"
CONFIG_FILE = EXAM_SERVER_DIR / "config.json"
ACCOUNTS_FILE = EXAM_SERVER_DIR / "accounts.json"
CONNECTION_FILE = EXAM_SERVER_DIR / "connection.json"
LOG_DIR = EXAM_SERVER_DIR / "logs"
