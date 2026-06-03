"""SQLite-backed log repository — the default when no DATABASE_URL is set."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine

from ._sqlalchemy_log_repository import SqlAlchemyLogRepository

# Default on-disk location for a clean checkout that needs no external service.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "cadence_log.db"


class SqliteLogRepository(SqlAlchemyLogRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        super().__init__(create_engine(f"sqlite:///{path}"))
