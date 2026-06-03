"""Isolated state for the coach subgraph.

The subgraph owns its own input/output keys; it shares no mutable key with the
hub. The hub crosses this boundary only through an adapter node.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage


class CoachState(TypedDict):
    user_message: str
    messages: list[BaseMessage]
    answer: str
