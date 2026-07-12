from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config.settings import DATABASE_FILE, SUBJECTS
from core.datetime_utils import now_text
from core.errors import raise_app_error


class DatabaseManager:
    """Manage StudyLab's SQLite connections, schema, and version upgrades."""

    SCHEMA_VERSION = 4

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
            version = 1
        if version < 2:
            self._migrate_to_version_2(connection)
            version = 2
        if version < 3:
            self._migrate_to_version_3(connection)
            version = 3
        if version < 4:
            self._migrate_to_version_4(connection)

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

    def _migrate_to_version_2(self, connection: sqlite3.Connection) -> None:
        try:
            connection.executescript(
                """
                BEGIN IMMEDIATE;

                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    nickname TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE user_statistics (
                    user_id INTEGER PRIMARY KEY,
                    total_questions INTEGER NOT NULL DEFAULT 0 CHECK (total_questions >= 0),
                    total_study_seconds INTEGER NOT NULL DEFAULT 0 CHECK (total_study_seconds >= 0),
                    total_study_days INTEGER NOT NULL DEFAULT 0 CHECK (total_study_days >= 0),
                    continuous_days INTEGER NOT NULL DEFAULT 0 CHECK (continuous_days >= 0),
                    max_continuous_days INTEGER NOT NULL DEFAULT 0 CHECK (max_continuous_days >= 0),
                    last_study_date TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE daily_study_stats (
                    user_id INTEGER NOT NULL,
                    study_date TEXT NOT NULL,
                    answered_count INTEGER NOT NULL DEFAULT 0 CHECK (answered_count >= 0),
                    study_seconds INTEGER NOT NULL DEFAULT 0 CHECK (study_seconds >= 0),
                    session_count INTEGER NOT NULL DEFAULT 0 CHECK (session_count >= 0),
                    score_earned REAL NOT NULL DEFAULT 0 CHECK (score_earned >= 0),
                    score_possible REAL NOT NULL DEFAULT 0 CHECK (score_possible >= 0),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, study_date),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_key TEXT,
                    source_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds INTEGER NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
                    answered_count INTEGER NOT NULL DEFAULT 0 CHECK (answered_count >= 0),
                    score_earned REAL NOT NULL DEFAULT 0 CHECK (score_earned >= 0),
                    score_possible REAL NOT NULL DEFAULT 0 CHECK (score_possible >= 0),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX idx_study_sessions_user_time
                    ON study_sessions(user_id, started_at DESC);
                CREATE INDEX idx_study_sessions_subject
                    ON study_sessions(user_id, subject);

                CREATE TABLE user_subject_abilities (
                    user_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    ability_index REAL NOT NULL DEFAULT 50 CHECK (ability_index BETWEEN 0 AND 100),
                    sample_count INTEGER NOT NULL DEFAULT 0 CHECK (sample_count >= 0),
                    score_earned REAL NOT NULL DEFAULT 0 CHECK (score_earned >= 0),
                    score_possible REAL NOT NULL DEFAULT 0 CHECK (score_possible >= 0),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, subject),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

            timestamp = now_text()
            connection.execute(
                """
                INSERT INTO users (id, nickname, created_at, updated_at)
                VALUES (1, '', ?, ?)
                """,
                (timestamp, timestamp),
            )
            connection.execute(
                """
                INSERT INTO user_statistics (
                    user_id, total_questions, total_study_seconds,
                    total_study_days, continuous_days, max_continuous_days,
                    last_study_date, updated_at
                ) VALUES (1, 0, 0, 0, 0, 0, NULL, ?)
                """,
                (timestamp,),
            )
            connection.executemany(
                """
                INSERT INTO user_subject_abilities (
                    user_id, subject, ability_index, sample_count,
                    score_earned, score_possible, updated_at
                ) VALUES (1, ?, 50, 0, 0, 0, ?)
                """,
                [(subject, timestamp) for subject in SUBJECTS],
            )
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_to_version_3(connection: sqlite3.Connection) -> None:
        try:
            with connection:
                connection.execute("ALTER TABLE users ADD COLUMN avatar_image BLOB")
                connection.execute("PRAGMA user_version = 3")
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_to_version_4(connection: sqlite3.Connection) -> None:
        try:
            with connection:
                connection.execute("ALTER TABLE wrong_questions ADD COLUMN question_type TEXT NOT NULL DEFAULT 'choice'")
                connection.execute("ALTER TABLE wrong_questions ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'")
                connection.execute("ALTER TABLE favorite_questions ADD COLUMN question_type TEXT NOT NULL DEFAULT 'choice'")
                connection.execute("ALTER TABLE favorite_questions ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'")
                connection.execute("PRAGMA user_version = 4")
        except Exception:
            connection.rollback()
            raise
