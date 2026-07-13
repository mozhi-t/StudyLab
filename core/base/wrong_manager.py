from __future__ import annotations

import json
import sqlite3

from config.settings import PAGE_SIZE, SUBJECTS
from core.base.database import DatabaseManager
from core.base.errors import raise_app_error
from models.base import WrongQuestion


class WrongManager:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def add_wrong(self, payload: WrongQuestion) -> None:
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO wrong_questions (
                        question_id, question_num, bank_name, bank_question_id,
                        subject, question, options_json, answer, explanation,
                        error_count, question_type, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subject, question_id) DO UPDATE SET
                        error_count = wrong_questions.error_count + 1,
                        question = excluded.question,
                        answer = excluded.answer,
                        explanation = excluded.explanation,
                        question_type = excluded.question_type,
                        payload_json = excluded.payload_json
                    """,
                    (
                        payload.question_id,
                        payload.question_num,
                        payload.bank_name,
                        payload.bank_question_id,
                        payload.subject,
                        payload.question,
                        self._encode_options(payload.options),
                        payload.answer,
                        payload.explanation,
                        payload.error_count,
                        payload.question_type,
                        self._encode_payload(payload.payload),
                    ),
                )
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise_app_error("E012", str(exc))

    def list_wrongs(
        self,
        subject: str | None = None,
        keyword: str = "",
        page: int = 1,
        page_size: int = PAGE_SIZE,
    ) -> tuple[list[WrongQuestion], int]:
        where_sql, parameters = self._filters(subject, keyword)
        offset = max(page - 1, 0) * page_size
        try:
            connection = self.database.connection()
            total = connection.execute(
                f"SELECT COUNT(*) FROM wrong_questions{where_sql}",
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM wrong_questions{where_sql}
                ORDER BY {self._subject_order_sql()}, id
                LIMIT ? OFFSET ?
                """,
                (*parameters, page_size, offset),
            ).fetchall()
            return [self._row_to_question(row) for row in rows], total
        except sqlite3.Error as exc:
            raise_app_error("E010", str(exc))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise_app_error("E011", str(exc))

    def get_question(self, subject: str, question_id: str) -> WrongQuestion | None:
        try:
            row = self.database.connection().execute(
                """
                SELECT * FROM wrong_questions
                WHERE subject = ? AND question_id = ?
                """,
                (subject, question_id),
            ).fetchone()
            return self._row_to_question(row) if row else None
        except sqlite3.Error as exc:
            raise_app_error("E010", str(exc))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise_app_error("E011", str(exc))

    def remove_wrong(self, subject: str, question_id: str) -> None:
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM wrong_questions WHERE subject = ? AND question_id = ?",
                    (subject, question_id),
                )
        except sqlite3.Error as exc:
            raise_app_error("E012", str(exc))

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
    def _row_to_question(row: sqlite3.Row) -> WrongQuestion:
        options = json.loads(row["options_json"])
        payload = json.loads(row["payload_json"])
        if not isinstance(options, dict):
            raise TypeError("题目选项不是字典")
        if not isinstance(payload, dict):
            raise TypeError("题目扩展数据不是字典")
        return WrongQuestion(
            question_id=row["question_id"],
            question_num=row["question_num"],
            bank_name=row["bank_name"],
            bank_question_id=row["bank_question_id"],
            subject=row["subject"],
            question=row["question"],
            options=options,
            answer=row["answer"],
            explanation=row["explanation"],
            error_count=row["error_count"],
            question_type=row["question_type"],
            payload=payload,
        )
