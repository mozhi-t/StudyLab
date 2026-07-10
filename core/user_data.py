from __future__ import annotations

import sqlite3
from datetime import date, datetime

from config.settings import SUBJECTS
from core.database import DatabaseManager
from core.datetime_utils import format_date, now_text, parse_date, parse_datetime
from core.errors import raise_app_error
from models.study import DailyStudyStats, ScoreResult, StudySession, SubjectAbility
from models.user import User


class UserDataManager:
    DEFAULT_USER_ID = 1
    ABILITY_PRIOR_EARNED = 5.0
    ABILITY_PRIOR_POSSIBLE = 10.0

    def __init__(self, database: DatabaseManager):
        self.database = database

    def load_user(self, user_id: int = DEFAULT_USER_ID) -> User:
        try:
            return self._load_user(self.database.connection(), user_id)
        except sqlite3.Error as exc:
            raise_app_error("E001", str(exc))

    def save_user(self, user: User, user_id: int = DEFAULT_USER_ID) -> None:
        timestamp = now_text()
        try:
            with self.database.transaction() as connection:
                user_updated = connection.execute(
                    """
                    UPDATE users
                    SET nickname = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (user.nickname, timestamp, user_id),
                ).rowcount
                stats_updated = connection.execute(
                    """
                    UPDATE user_statistics
                    SET total_questions = ?, total_study_seconds = ?,
                        total_study_days = ?, continuous_days = ?,
                        max_continuous_days = ?, last_study_date = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        user.total_questions,
                        user.total_study_seconds,
                        user.total_study_days,
                        user.continuous_days,
                        user.max_continuous_days,
                        user.last_study_date,
                        timestamp,
                        user_id,
                    ),
                ).rowcount
                if not user_updated or not stats_updated:
                    raise ValueError(f"用户不存在: {user_id}")
        except (sqlite3.Error, ValueError) as exc:
            raise_app_error("E002", str(exc))

    def record_answer(
        self,
        result: ScoreResult,
        *,
        subject: str | None = None,
        session_id: int | None = None,
        study_date: date | None = None,
        user_id: int = DEFAULT_USER_ID,
    ) -> User:
        self._validate_score(result)
        if subject is not None and subject not in SUBJECTS:
            raise_app_error("E002", f"未知科目: {subject}")

        today = study_date or date.today()
        today_text = format_date(today)
        timestamp = now_text()
        try:
            with self.database.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM user_statistics WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"用户统计不存在: {user_id}")

                total_study_days = row["total_study_days"]
                continuous_days = row["continuous_days"]
                max_continuous_days = row["max_continuous_days"]
                last_study_date = parse_date(row["last_study_date"])
                if last_study_date != today:
                    total_study_days += 1
                    continuous_days = (
                        continuous_days + 1
                        if last_study_date and (today - last_study_date).days == 1
                        else 1
                    )
                    max_continuous_days = max(max_continuous_days, continuous_days)

                connection.execute(
                    """
                    UPDATE user_statistics
                    SET total_questions = total_questions + ?,
                        total_study_days = ?, continuous_days = ?,
                        max_continuous_days = ?, last_study_date = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        result.answered_count,
                        total_study_days,
                        continuous_days,
                        max_continuous_days,
                        today_text,
                        timestamp,
                        user_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO daily_study_stats (
                        user_id, study_date, answered_count, study_seconds,
                        session_count, score_earned, score_possible, updated_at
                    ) VALUES (?, ?, ?, 0, 0, ?, ?, ?)
                    ON CONFLICT(user_id, study_date) DO UPDATE SET
                        answered_count = answered_count + excluded.answered_count,
                        score_earned = score_earned + excluded.score_earned,
                        score_possible = score_possible + excluded.score_possible,
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        today_text,
                        result.answered_count,
                        result.earned,
                        result.possible,
                        timestamp,
                    ),
                )

                if subject is not None and result.possible > 0:
                    self._update_ability(connection, user_id, subject, result, timestamp)
                if session_id is not None:
                    updated = connection.execute(
                        """
                        UPDATE study_sessions
                        SET answered_count = answered_count + ?,
                            score_earned = score_earned + ?,
                            score_possible = score_possible + ?
                        WHERE id = ? AND user_id = ? AND ended_at IS NULL
                        """,
                        (
                            result.answered_count,
                            result.earned,
                            result.possible,
                            session_id,
                            user_id,
                        ),
                    ).rowcount
                    if not updated:
                        raise ValueError(f"学习会话不存在或已结束: {session_id}")

                connection.execute(
                    "UPDATE users SET updated_at = ? WHERE id = ?",
                    (timestamp, user_id),
                )
                return self._load_user(connection, user_id)
        except (sqlite3.Error, ValueError) as exc:
            raise_app_error("E002", str(exc))

    def start_study_session(
        self,
        *,
        subject: str,
        source_type: str,
        source_name: str,
        source_key: str | None = None,
        user_id: int = DEFAULT_USER_ID,
    ) -> int:
        if subject not in SUBJECTS:
            raise_app_error("E002", f"未知科目: {subject}")
        timestamp = now_text()
        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO study_sessions (
                        user_id, subject, source_type, source_key,
                        source_name, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, subject, source_type, source_key, source_name, timestamp),
                )
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise_app_error("E002", str(exc))

    def finish_study_session(
        self,
        session_id: int,
        *,
        user_id: int = DEFAULT_USER_ID,
        ended_at: datetime | None = None,
    ) -> int:
        end_time = ended_at or datetime.now().replace(microsecond=0)
        end_text = end_time.strftime("%Y-%m-%d %H:%M:%S")
        timestamp = now_text()
        try:
            with self.database.transaction() as connection:
                row = connection.execute(
                    """
                    SELECT * FROM study_sessions
                    WHERE id = ? AND user_id = ?
                    """,
                    (session_id, user_id),
                ).fetchone()
                if row is None:
                    raise ValueError(f"学习会话不存在: {session_id}")
                if row["ended_at"] is not None:
                    return row["duration_seconds"]

                started_at = parse_datetime(row["started_at"])
                if started_at is None:
                    raise ValueError(f"学习会话开始时间无效: {session_id}")
                duration_seconds = max(int((end_time - started_at).total_seconds()), 0)
                connection.execute(
                    """
                    UPDATE study_sessions
                    SET ended_at = ?, duration_seconds = ?
                    WHERE id = ?
                    """,
                    (end_text, duration_seconds, session_id),
                )

                is_valid_session = row["answered_count"] > 0 or duration_seconds >= 60
                if is_valid_session:
                    study_date = format_date(end_time.date())
                    connection.execute(
                        """
                        UPDATE user_statistics
                        SET total_study_seconds = total_study_seconds + ?,
                            updated_at = ?
                        WHERE user_id = ?
                        """,
                        (duration_seconds, timestamp, user_id),
                    )
                    connection.execute(
                        """
                        INSERT INTO daily_study_stats (
                            user_id, study_date, answered_count, study_seconds,
                            session_count, score_earned, score_possible, updated_at
                        ) VALUES (?, ?, 0, ?, 1, 0, 0, ?)
                        ON CONFLICT(user_id, study_date) DO UPDATE SET
                            study_seconds = study_seconds + excluded.study_seconds,
                            session_count = session_count + 1,
                            updated_at = excluded.updated_at
                        """,
                        (user_id, study_date, duration_seconds, timestamp),
                    )
                    connection.execute(
                        "UPDATE users SET updated_at = ? WHERE id = ?",
                        (timestamp, user_id),
                    )
                return duration_seconds
        except (sqlite3.Error, ValueError) as exc:
            raise_app_error("E002", str(exc))

    def get_daily_stats(
        self,
        study_date: date | None = None,
        user_id: int = DEFAULT_USER_ID,
    ) -> DailyStudyStats:
        day_text = format_date(study_date or date.today())
        try:
            row = self.database.connection().execute(
                """
                SELECT * FROM daily_study_stats
                WHERE user_id = ? AND study_date = ?
                """,
                (user_id, day_text),
            ).fetchone()
            return self._row_to_daily_stats(row) if row else DailyStudyStats(day_text)
        except sqlite3.Error as exc:
            raise_app_error("E001", str(exc))

    def list_daily_stats(
        self,
        start_date: date,
        end_date: date,
        user_id: int = DEFAULT_USER_ID,
    ) -> list[DailyStudyStats]:
        try:
            rows = self.database.connection().execute(
                """
                SELECT * FROM daily_study_stats
                WHERE user_id = ? AND study_date BETWEEN ? AND ?
                ORDER BY study_date
                """,
                (user_id, format_date(start_date), format_date(end_date)),
            ).fetchall()
            return [self._row_to_daily_stats(row) for row in rows]
        except sqlite3.Error as exc:
            raise_app_error("E001", str(exc))

    def get_subject_abilities(
        self,
        user_id: int = DEFAULT_USER_ID,
    ) -> list[SubjectAbility]:
        try:
            rows = self.database.connection().execute(
                """
                SELECT * FROM user_subject_abilities
                WHERE user_id = ?
                ORDER BY CASE subject
                    WHEN 'chinese' THEN 0 WHEN 'math' THEN 1
                    WHEN 'english' THEN 2 WHEN 'computer_basic' THEN 3
                    WHEN 'python' THEN 4 WHEN 'mysql' THEN 5 ELSE 6 END
                """,
                (user_id,),
            ).fetchall()
            return [
                SubjectAbility(
                    subject=row["subject"],
                    ability_index=row["ability_index"],
                    sample_count=row["sample_count"],
                    score_earned=row["score_earned"],
                    score_possible=row["score_possible"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
        except sqlite3.Error as exc:
            raise_app_error("E001", str(exc))

    def get_recent_activity(
        self,
        user_id: int = DEFAULT_USER_ID,
    ) -> StudySession | None:
        try:
            row = self.database.connection().execute(
                """
                SELECT * FROM study_sessions
                WHERE user_id = ? AND ended_at IS NOT NULL
                  AND (answered_count > 0 OR duration_seconds >= 60)
                ORDER BY ended_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return self._row_to_session(row) if row else None
        except sqlite3.Error as exc:
            raise_app_error("E001", str(exc))

    def _update_ability(
        self,
        connection: sqlite3.Connection,
        user_id: int,
        subject: str,
        result: ScoreResult,
        timestamp: str,
    ) -> None:
        row = connection.execute(
            """
            SELECT * FROM user_subject_abilities
            WHERE user_id = ? AND subject = ?
            """,
            (user_id, subject),
        ).fetchone()
        if row is None:
            raise ValueError(f"科目能力数据不存在: {subject}")
        earned = row["score_earned"] + result.earned
        possible = row["score_possible"] + result.possible
        ability_index = 100 * (
            earned + self.ABILITY_PRIOR_EARNED
        ) / (possible + self.ABILITY_PRIOR_POSSIBLE)
        connection.execute(
            """
            UPDATE user_subject_abilities
            SET ability_index = ?, sample_count = sample_count + ?,
                score_earned = ?, score_possible = ?, updated_at = ?
            WHERE user_id = ? AND subject = ?
            """,
            (
                ability_index,
                result.answered_count,
                earned,
                possible,
                timestamp,
                user_id,
                subject,
            ),
        )

    @staticmethod
    def _validate_score(result: ScoreResult) -> None:
        if result.answered_count < 0:
            raise_app_error("E002", "答题数量不能为负数")
        if result.earned < 0 or result.possible < 0:
            raise_app_error("E002", "得分不能为负数")
        if result.earned > result.possible:
            raise_app_error("E002", "实际得分不能大于满分")

    @staticmethod
    def _load_user(connection: sqlite3.Connection, user_id: int) -> User:
        row = connection.execute(
            """
            SELECT u.nickname, u.created_at, u.updated_at,
                   s.total_questions, s.total_study_seconds,
                   s.total_study_days, s.continuous_days,
                   s.max_continuous_days, s.last_study_date
            FROM users AS u
            JOIN user_statistics AS s ON s.user_id = u.id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f"用户不存在: {user_id}")
        return User(
            nickname=row["nickname"],
            total_questions=row["total_questions"],
            total_study_seconds=row["total_study_seconds"],
            total_study_days=row["total_study_days"],
            continuous_days=row["continuous_days"],
            max_continuous_days=row["max_continuous_days"],
            last_study_date=row["last_study_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_daily_stats(row: sqlite3.Row) -> DailyStudyStats:
        return DailyStudyStats(
            study_date=row["study_date"],
            answered_count=row["answered_count"],
            study_seconds=row["study_seconds"],
            session_count=row["session_count"],
            score_earned=row["score_earned"],
            score_possible=row["score_possible"],
        )

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> StudySession:
        return StudySession(
            id=row["id"],
            subject=row["subject"],
            source_type=row["source_type"],
            source_key=row["source_key"],
            source_name=row["source_name"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_seconds=row["duration_seconds"],
            answered_count=row["answered_count"],
            score_earned=row["score_earned"],
            score_possible=row["score_possible"],
        )
