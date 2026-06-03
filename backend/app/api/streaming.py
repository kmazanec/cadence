"""The SSE event envelope: the six event variants the /chat stream can carry,
and the encoder that puts one on the wire.

Token events originate only from model-message deltas; route, structured, and
clarification events are read from committed graph state, never from message
deltas. Error events carry a human-meaningful message and never a traceback,
prompt, or secret. The variant set is closed.
"""

from __future__ import annotations

import json
from typing import Literal, assert_never

from pydantic import BaseModel

from ..agents.generator.schemas import WorkoutPayload
from ..graph.routing import Route
from .schemas import LogPayload


class RouteEvent(BaseModel):
    type: Literal["route"] = "route"
    route: Route


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class StructuredEvent(BaseModel):
    type: Literal["structured"] = "structured"
    payload: WorkoutPayload | LogPayload


class ClarificationEvent(BaseModel):
    type: Literal["clarification"] = "clarification"
    question: str
    options: list[str]


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


SSEEvent = (
    RouteEvent
    | TokenEvent
    | StructuredEvent
    | ClarificationEvent
    | DoneEvent
    | ErrorEvent
)


def encode_sse(event: SSEEvent) -> str:
    """Serialise one event into a Server-Sent-Events frame.

    The match is exhaustive over the closed variant set; an unhandled variant is
    a type error, not a silent fallthrough.
    """

    match event:
        case RouteEvent() | TokenEvent() | StructuredEvent() | ClarificationEvent() | DoneEvent() | ErrorEvent():
            payload = event.model_dump()
        case _:
            assert_never(event)
    return f"data: {json.dumps(payload)}\n\n"
