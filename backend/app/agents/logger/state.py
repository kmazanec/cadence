"""Isolated state for the logger subgraph.

Carries its own retry budget (ceiling 2); resolved/unresolved entries leave via
the boundary adapter, never a shared mutable key.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage

from ...data.log_repository import LogEntry

RETRY_CEILING: int = 2


class LoggerState(TypedDict):
    user_message: str
    messages: list[BaseMessage]
    entries: list[LogEntry]
    retry_count: int
