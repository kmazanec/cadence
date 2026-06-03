"""The HTTP chat envelope: the request the client sends and the wide response
it receives.

The response is intentionally wide — every field is present on every turn and
null where the turn did not produce it — so the same shape serves coach replies,
workouts, logs, and clarifying questions. ``structured`` is the serialised
producer arm of the turn's subgraph result.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..agents.generator.schemas import WorkoutPayload
from ..data.log_repository import LogEntry
from ..graph.explanation import Reason
from ..graph.routing import ClarificationPrompt, Route


class LogPayload(BaseModel):
    """The structured form of a logging turn: the entries that were recorded."""

    entries: list[LogEntry]


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    route: Route | None = None
    reply_text: str
    structured: WorkoutPayload | LogPayload | None = None
    explanation: list[Reason] = Field(default_factory=list)
    clarification: ClarificationPrompt | None = None
