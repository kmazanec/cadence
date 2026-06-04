"""The SSE event envelope: the event variants the /chat stream can carry, and
the encoder that puts one on the wire.

Token events originate only from the reply-producing node's model deltas;
thinking events carry every OTHER node's model deltas (the router deciding, a
subagent working) as deemphasized progress, never as the reply. Route,
structured, explanation, and clarification events are read from committed graph
state, never reconstructed from message deltas. Error events carry a
human-meaningful message and never a traceback, prompt, or secret. The variant
set is closed.
"""

from __future__ import annotations

import json
from typing import Literal, assert_never

from pydantic import BaseModel

from ..agents.generator.schemas import WorkoutPayload
from ..graph.explanation import Reason
from ..graph.routing import Route
from .schemas import LogPayload


class RouteEvent(BaseModel):
    type: Literal["route"] = "route"
    route: Route


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class ThinkingEvent(BaseModel):
    """Deemphasized progress text — the router deciding, a subagent working.

    Distinct from ``TokenEvent`` so the client can render it as faded 'thinking'
    chatter rather than part of the reply. This is where internal model output
    (the router's structured-decision tokens, the generator's tool reasoning)
    surfaces honestly without leaking into the conversation as if it were the
    answer.

    ``source`` names the node that produced the fragment so the client can parse
    it correctly: ``router`` fragments are partial JSON of the routing decision
    (the client extracts the human ``rationale``), while other sources stream
    plain prose. The client must never display the raw JSON.
    """

    type: Literal["thinking"] = "thinking"
    source: str
    text: str


class StructuredEvent(BaseModel):
    type: Literal["structured"] = "structured"
    payload: WorkoutPayload | LogPayload


class ExplanationEvent(BaseModel):
    """The turn's reasoning, read from committed graph state.

    Carries the controlled-vocabulary :class:`Reason` triples the agent produced
    this turn so the client can render why a decision was made — never the
    reply text itself.
    """

    type: Literal["explanation"] = "explanation"
    reasons: list[Reason]


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
    | ThinkingEvent
    | StructuredEvent
    | ExplanationEvent
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
        case (
            RouteEvent()
            | TokenEvent()
            | ThinkingEvent()
            | StructuredEvent()
            | ExplanationEvent()
            | ClarificationEvent()
            | DoneEvent()
            | ErrorEvent()
        ):
            # mode="json" coerces nested datetimes/enums to JSON-native values
            # (e.g. LogEntry.logged_at) so json.dumps never trips on them.
            payload = event.model_dump(mode="json")
        case _:
            assert_never(event)
    return f"data: {json.dumps(payload)}\n\n"
