"""The hub's shared state: HubState, the tagged SubgraphResult union that each
subgraph produces, and the recovery record carried after a caught error.

Every field is present from the outset and nullable where it is not yet
produced, so populating a value never reshapes the state schema. The three-arm
SubgraphResult union is closed: a response-assembly switch over ``kind`` must
remain exhaustive.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from ..agents.generator.schemas import WorkoutPayload
from ..data.log_repository import LogEntry
from .explanation import Reason
from .routing import ClarificationPrompt, Route


class CoachResult(BaseModel):
    kind: Literal["coach"] = "coach"
    answer: str


class GeneratorResult(BaseModel):
    kind: Literal["workout"] = "workout"
    workout: WorkoutPayload
    selected_exercise_ids: list[str]


class WorkoutLogResult(BaseModel):
    kind: Literal["log"] = "log"
    entries: list[LogEntry]
    session_id: str


SubgraphResult = CoachResult | GeneratorResult | WorkoutLogResult


class RecoveryInfo(BaseModel):
    """What is known about a caught error and the recovery attempt."""

    message: str
    recovered: bool
    retry_count: int = 0


class HubState(TypedDict):
    session_id: str
    # Single-owner reducer: only the hub appends to the conversation, so parent
    # and child never both reduce this key.
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str
    route: Route | None
    routing_confidence: float | None
    routing_raw: dict | None
    subgraph_result: SubgraphResult | None
    explanation: list[Reason]
    clarification: ClarificationPrompt | None
    error: RecoveryInfo | None
