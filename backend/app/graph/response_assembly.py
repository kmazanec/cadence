"""Maps committed hub state into the outbound chat envelope.

The switch over ``subgraph_result.kind`` is the single exhaustive point that
turns each producer arm into the response: coach contributes reply text only,
the generator contributes the workout payload, the logger contributes the log
payload. A new arm must be handled here or assembly fails loudly.
"""

from __future__ import annotations

from typing import assert_never

from ..agents.generator.schemas import WorkoutPayload
from ..api.schemas import ChatResponse, LogPayload
from .state import (
    CoachResult,
    GeneratorResult,
    HubState,
    SubgraphResult,
    WorkoutLogResult,
)


def assemble_response(state: HubState) -> ChatResponse:
    """Build the wide :class:`ChatResponse` from committed hub state."""

    reply_text = ""
    structured: WorkoutPayload | LogPayload | None = None

    result: SubgraphResult | None = state.get("subgraph_result")
    if isinstance(result, CoachResult):
        reply_text = result.answer
    elif isinstance(result, GeneratorResult):
        structured = result.workout
    elif isinstance(result, WorkoutLogResult):
        structured = LogPayload(entries=result.entries)
    elif result is None:
        # No subgraph ran this turn (e.g. a clarifying question was asked).
        reply_text = ""
    else:
        assert_never(result)

    return ChatResponse(
        route=state.get("route"),
        reply_text=reply_text,
        structured=structured,
        explanation=list(state.get("explanation") or []),
        clarification=state.get("clarification"),
    )
