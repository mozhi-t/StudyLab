from __future__ import annotations

import json
import sqlite3

from config.settings import PAGE_SIZE, SUBJECTS
from core.database import DatabaseManager
from core.errors import raise_app_error
from models.favorite_question import FavoriteQuestion


class FavoriteManager:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def toggle_favorite(self, payload: FavoriteQuestion) -> bool:
        try:
            with self.database.transaction() as connection:
                exists = connection.execute(
                    """
                    SELECT 1 FROM favorite_questions
                    WHERE subject = ? AND question_id = ?
                    """,
                    (payload.subject, payload.question_id),
                ).fetchone()
                if exists:
                    connection.execute(
                        """
                        DELETE FROM favorite_questions
                        WHERE subject = ? AND question_id = ?
                        """,
                        (payload.subject, payload.question_id),
                    )
                    return False
                connection.execute(
                    """
                    INSERT INTO favorite_questions (
                        question_id, bank_name, bank_question_id, subject,
                        question, options_json, answer, explanation,
                        question_type, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.question_id,
                        payload.bank_name,
                        payload.bank_question_id,
                        payload.subject,
                        payload.question,
                        self._encode_options(payload.options),
                        payload.answer,
                        payload.explanation,
                        payload.question_type,
                        self._encode_payload(payload.payload),
                    ),
                )
                return True
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise_app_error("E015", str(exc))

    def list_favorites(
        self,
        subject: str | None = None,
        keyword: str = "",
        page: int = 1,
        page_size: int = PAGE_SIZE,
    ) -> tuple[list[FavoriteQuestion], int]:
        where_sql, parameters = self._filters(subject, keyword)
        offset = max(page - 1, 0) * page_size
        try:
            connection = self.database.connection()
            total = connection.execute(
                f"SELECT COUNT(*) FROM favorite_questions{where_sql}",
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM favorite_questions{where_sql}
                ORDER BY {self._subject_order_sql()}, id
                LIMIT ? OFFSET ?
                """,
                (*parameters, page_size, offset),
            ).fetchall()
            return [self._row_to_question(row) for row in rows], total
        except sqlite3.Error as exc:
            raise_app_error("E013", str(exc))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise_app_error("E014", str(exc))

    def get_question(self, subject: str, question_id: str) -> FavoriteQuestion | None:
        try:
            row = self.database.connection().execute(
                """
                SELECT * FROM favorite_questions
                WHERE subject = ? AND question_id = ?
                """,
                (subject, question_id),
            ).fetchone()
            return self._row_to_question(row) if row else None
        except sqlite3.Error as exc:
            raise_app_error("E013", str(exc))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise_app_error("E014", str(exc))

    def remove_favorite(self, subject: str, question_id: str) -> None:
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM favorite_questions WHERE subject = ? AND question_id = ?",
                    (subject, question_id),
                )
        except sqlite3.Error as exc:
            raise_app_error("E015", str(exc))

    @staticmethod
    def _filters(subject: str | None, keyword: str) -> tuple[str, tuple]:
        clauses = []
        parameters: list[object] = []
        if subject:
            clauses.append("subject = ?")
            parameters.append(subject)
        keyword = keyword.strip()
        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            clauses.append(
                "(question LIKE ? ESCAPE '\\' COLLATE NOCASE "
                "OR bank_name LIKE ? ESCAPE '\\' COLLATE NOCASE)"
            )
            parameters.extend((pattern, pattern))
        where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_sql, tuple(parameters)

    @staticmethod
    def _subject_order_sql() -> str:
        cases = " ".join(
            f"WHEN '{subject}' THEN {position}"
            for position, subject in enumerate(SUBJECTS)
        )
        return f"CASE subject {cases} ELSE {len(SUBJECTS)} END"

    @staticmethod
    def _encode_options(options: dict[str, str]) -> str:
        if not isinstance(options, dict):
            raise TypeError("题目选项不是字典")
        return json.dumps(options, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _encode_payload(payload: dict) -> str:
        if not isinstance(payload, dict):
            raise TypeError("题目扩展数据不是字典")
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> FavoriteQuestion:
        options = json.loads(row["options_json"])
        payload = json.loads(row["payload_json"])
        if not isinstance(options, dict):
            raise TypeError("题目选项不是字典")
        if not isinstance(payload, dict):
            raise TypeError("题目扩展数据不是字典")
        return FavoriteQuestion(
            question_id=row["question_id"],
            bank_name=row["bank_name"],
            bank_question_id=row["bank_question_id"],
            subject=row["subject"],
            question=row["question"],
            options=options,
            answer=row["answer"],
            explanation=row["explanation"],
            question_type=row["question_type"],
            payload=payload,
        )
