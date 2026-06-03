"""SQLite-backed log repository — the default when no DATABASE_URL is set."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine

from ._sqlalchemy_log_repository import SqlAlchemyLogRepository

# Default on-disk location for a clean checkout that needs no external service.
# Override via CADENCE_DB_PATH env var (e.g. to write into a named-volume dir).
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "cadence_log.db"


def _resolve_db_path(db_path: Path | str | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    env_path = os.environ.get("CADENCE_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


class SqliteLogRepository(SqlAlchemyLogRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        path = _resolve_db_path(db_path)
        super().__init__(create_engine(f"sqlite:///{path}"))
