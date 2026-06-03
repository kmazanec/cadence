"""Shared SQLAlchemy-engine log repository.

Both the SQLite and Postgres repositories are this same implementation over a
different engine URL, guaranteeing they stay schema-identical.
"""

from __future__ import annotations

from sqlalchemy import create_engine, insert, select
from sqlalchemy.engine import Engine

from .log_repository import LogEntry, log_entries_table, metadata


class SqlAlchemyLogRepository:
    """Engine-backed :class:`LogRepository` implementation."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        metadata.create_all(self._engine)

    @classmethod
    def from_url(cls, url: str) -> "SqlAlchemyLogRepository":
        return cls(create_engine(url))

    def append(self, entries: list[LogEntry], session_id: str) -> None:
        if not entries:
            return
        rows = [
            {
                "session_id": session_id,
                "exercise_id": e.exercise_id,
                "raw_name": e.raw_name,
                "sets": e.sets,
                "reps": e.reps,
                "weight": e.weight,
                "unmatched": e.unmatched,
                "logged_at": e.logged_at,
            }
            for e in entries
        ]
        with self._engine.begin() as conn:
            conn.execute(insert(log_entries_table), rows)

    def for_session(self, session_id: str) -> list[LogEntry]:
        stmt = (
            select(log_entries_table)
            .where(log_entries_table.c.session_id == session_id)
            .order_by(log_entries_table.c.id)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            LogEntry(
                session_id=row["session_id"],
                exercise_id=row["exercise_id"],
                raw_name=row["raw_name"],
                sets=row["sets"],
                reps=row["reps"],
                weight=row["weight"],
                unmatched=row["unmatched"],
                logged_at=row["logged_at"],
            )
            for row in rows
        ]
