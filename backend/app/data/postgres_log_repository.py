"""Postgres-backed log repository — selected when DATABASE_URL is set.

Shares the schema and behaviour of the SQLite repository; only the engine URL
differs.
"""

from __future__ import annotations

from sqlalchemy import create_engine

from ._sqlalchemy_log_repository import SqlAlchemyLogRepository


class PostgresLogRepository(SqlAlchemyLogRepository):
    def __init__(self, database_url: str) -> None:
        super().__init__(create_engine(database_url))
