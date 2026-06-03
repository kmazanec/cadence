"""Routing contract: the closed Route enum, the router's structured-output
decision shape, and the confidence gate that turns a decision into either a
route or a clarifying question.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

# Below this routing confidence the hub asks a clarifying question rather than
# committing to a route.
CONFIDENCE_THRESHOLD: float = 0.7


class Route(str, Enum):
    """The closed set of destinations the hub can dispatch a turn to."""

    COACH = "coach"
    WORKOUT_GENERATE = "workout_generate"
    WORKOUT_LOG = "workout_log"


class ClarificationPrompt(BaseModel):
    """A question (with suggested options) offered when intent is ambiguous."""

    question: str
    options: list[str]


class RoutingDecision(BaseModel):
    """The router's structured output for a single turn."""

    route: Route
    confidence: float
    rationale: str
    clarification: ClarificationPrompt | None = None


def decide_route(
    decision: RoutingDecision | None,
) -> tuple[Route | None, ClarificationPrompt | None]:
    """Apply the confidence gate to a routing decision.

    Returns ``(route, None)`` when a decision is present and confident enough;
    otherwise ``(None, clarification)`` — covering both a below-threshold
    decision and a missing decision (e.g. structured output failed).
    """

    if decision is not None and decision.confidence >= CONFIDENCE_THRESHOLD:
        return decision.route, None

    clarification = decision.clarification if decision is not None else None
    if clarification is None:
        clarification = ClarificationPrompt(
            question="Could you tell me a bit more about what you'd like to do?",
            options=[
                "Ask a fitness question",
                "Build me a workout",
                "Log a workout I did",
            ],
        )
    return None, clarification
