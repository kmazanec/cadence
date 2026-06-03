"""Workout-log persistence: the LogEntry schema, the repository seam, the
shared SQLAlchemy table, and the env-driven factory.

A single table with portable column types backs both the SQLite (default) and
Postgres implementations, so the same schema travels across deployments.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Column,
)

metadata = MetaData()

# Portable column types only — no backend-specific features — so SQLite and
# Postgres share one definition.
log_entries_table = Table(
    "log_entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String, nullable=False, index=True),
    Column("exercise_id", String, nullable=True),
    Column("raw_name", String, nullable=False),
    Column("sets", Integer, nullable=True),
    Column("reps", Integer, nullable=True),
    Column("weight", Float, nullable=True),
    Column("unmatched", Boolean, nullable=False),
    Column("logged_at", DateTime, nullable=False),
)


class LogEntry(BaseModel):
    """One logged exercise performance for a session.

    ``exercise_id`` is None and ``unmatched`` is True when the raw text could
    not be resolved to a catalogue exercise.
    """

    session_id: str
    exercise_id: str | None
    raw_name: str
    sets: int | None = None
    reps: int | None = None
    weight: float | None = None
    unmatched: bool
    logged_at: datetime


@runtime_checkable
class LogRepository(Protocol):
    """Append-and-read persistence for workout-log entries."""

    def append(self, entries: list[LogEntry], session_id: str) -> None:
        """Persist the entries for the session."""
        ...

    def for_session(self, session_id: str) -> list[LogEntry]:
        """Return every entry recorded for the session, oldest first."""
        ...


def get_log_repository() -> LogRepository:
    """Return the configured log repository.

    Uses Postgres when ``DATABASE_URL`` is set, otherwise a local SQLite file
    so a clean checkout needs no external service.
    """

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        from .postgres_log_repository import PostgresLogRepository

        return PostgresLogRepository(database_url)

    from .sqlite_log_repository import SqliteLogRepository

    return SqliteLogRepository()
