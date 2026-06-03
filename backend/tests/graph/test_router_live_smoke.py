"""Live smoke tests: the three canonical PRD messages route to expected subgraphs.

Why this file: deterministic tests verify the routing logic is wired correctly,
but cannot validate that CONFIDENCE_THRESHOLD=0.7 lets the three canonical
messages dispatch above threshold. This minimal live test (skipped without an
API key) provides that honest LLM-system check while keeping CI unaffected.
"""

from __future__ import annotations

import os

import pytest

from app.graph.routing import CONFIDENCE_THRESHOLD, Route, RoutingDecision

# Skip the entire module when no API key is present.
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set — live smoke skipped",
)


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expected_route",
    [
        ("What muscles does a deadlift work?", Route.COACH),
        ("Build me a 30 min upper body session with dumbbells", Route.WORKOUT_GENERATE),
        ("I just did 3x10 bench press at 185 lbs", Route.WORKOUT_LOG),
    ],
)
async def test_canonical_messages_route_correctly(
    message: str, expected_route: Route
) -> None:
    """Each canonical PRD message routes to its expected subgraph above threshold."""
    from app.graph.routing import RoutingDecision
    from app.models.factory import get_model

    model = get_model("router")
    structured = model.with_structured_output(RoutingDecision, include_raw=True)

    raw_result: dict = await structured.ainvoke(message)
    parsed: RoutingDecision | None = raw_result.get("parsed")

    assert parsed is not None, (
        f"Structured output parse failed for: {message!r}\n"
        f"Raw result: {raw_result}"
    )
    assert parsed.confidence >= CONFIDENCE_THRESHOLD, (
        f"Confidence {parsed.confidence:.2f} is below threshold {CONFIDENCE_THRESHOLD} "
        f"for: {message!r}\n"
        f"Rationale: {parsed.rationale}"
    )
    assert parsed.route == expected_route, (
        f"Expected route {expected_route.value!r} but got {parsed.route.value!r} "
        f"for: {message!r}\n"
        f"Confidence: {parsed.confidence:.2f}, Rationale: {parsed.rationale}"
    )
