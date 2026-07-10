from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config.settings import DATABASE_FILE
from core.errors import raise_app_error


class DatabaseManager:
    """Manage StudyLab's SQLite connections, schema, and legacy migrations."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        path: Path | str = DATABASE_FILE,
    ):
        self.path = path
        self._local = threading.local()

    def initialize(self) -> None:
        try:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            connection = self.connection()
        except (OSError, sqlite3.Error) as exc:
            self.close()
            raise_app_error("E026", str(exc))
        try:
            self._run_migrations(connection)
        except sqlite3.Error as exc:
            self.close()
            raise_app_error("E026", str(exc))

    def connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 3000")
            if self.path != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = NORMAL")
            self._local.connection = connection
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connection()
        try:
            with connection:
                yield connection
        except Exception:
            connection.rollback()
            raise

    def close(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            del self._local.connection

    def _run_migrations(self, connection: sqlite3.Connection) -> None:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > self.SCHEMA_VERSION:
            raise sqlite3.DatabaseError(
                f"数据库版本 {version} 高于程序支持的版本 {self.SCHEMA_VERSION}"
            )
        if version < 1:
            self._migrate_to_version_1(connection)

    def _migrate_to_version_1(self, connection: sqlite3.Connection) -> None:
        try:
            connection.executescript(
                """
                BEGIN IMMEDIATE;

                CREATE TABLE wrong_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT NOT NULL,
                    question_num INTEGER NOT NULL,
                    bank_name TEXT NOT NULL,
                    bank_question_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    error_count INTEGER NOT NULL DEFAULT 1 CHECK (error_count >= 1),
                    UNIQUE (subject, question_id)
                );

                CREATE INDEX idx_wrong_subject
                    ON wrong_questions(subject);
                CREATE INDEX idx_wrong_bank_name
                    ON wrong_questions(bank_name);

                CREATE TABLE favorite_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT NOT NULL,
                    bank_name TEXT NOT NULL,
                    bank_question_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (subject, question_id)
                );

                CREATE INDEX idx_favorite_subject
                    ON favorite_questions(subject);
                CREATE INDEX idx_favorite_bank_name
                    ON favorite_questions(bank_name);
                """
            )
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
