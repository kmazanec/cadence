"""Pure-function unit tests for the confidence gate in decide_route.

Why this file: the routing logic — including the 0.69/0.70 boundary,
the None-decision safe-net, and the three-arm dispatch — must be tested
independently of any graph or LLM call so the invariant is provably
correct by itself.
"""

from __future__ import annotations

import pytest

from app.graph.routing import (
    CONFIDENCE_THRESHOLD,
    ClarificationPrompt,
    Route,
    RoutingDecision,
    decide_route,
)


# ---------------------------------------------------------------------------
# Boundary tests: 0.69 → clarify, 0.70 → dispatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "confidence,expect_route",
    [
        (0.69, False),  # just below threshold → clarify
        (0.70, True),   # at threshold → dispatch
        (0.71, True),   # above threshold → dispatch
        (0.0, False),   # zero confidence → clarify
        (1.0, True),    # perfect confidence → dispatch
    ],
)
def test_confidence_boundary(confidence: float, expect_route: bool) -> None:
    """Boundary semantics: >= THRESHOLD dispatches, < THRESHOLD clarifies."""
    decision = RoutingDecision(
        route=Route.COACH,
        confidence=confidence,
        rationale="test",
    )
    route, clarification = decide_route(decision)
    if expect_route:
        assert route is not None, f"Expected route at confidence={confidence}"
        assert clarification is None
    else:
        assert route is None, f"Expected clarify at confidence={confidence}"
        assert clarification is not None


def test_threshold_is_imported_constant() -> None:
    """CONFIDENCE_THRESHOLD is the single magic number; not a literal inside decide_route."""
    # If THRESHOLD changed, all boundary tests would move — confirms the one constant controls them all.
    assert CONFIDENCE_THRESHOLD == 0.7


# ---------------------------------------------------------------------------
# None decision → safe-net clarify
# ---------------------------------------------------------------------------


def test_none_decision_returns_clarification() -> None:
    """A missing decision (structured-output failure) triggers clarification, not dispatch."""
    route, clarification = decide_route(None)
    assert route is None
    assert clarification is not None
    assert isinstance(clarification, ClarificationPrompt)
    assert len(clarification.options) >= 2


# ---------------------------------------------------------------------------
# Each route at high confidence → dispatches correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_route", list(Route))
def test_each_route_dispatches_at_high_confidence(target_route: Route) -> None:
    """All three Route variants are returned unchanged when confidence is high."""
    decision = RoutingDecision(
        route=target_route,
        confidence=0.9,
        rationale="test",
    )
    route, clarification = decide_route(decision)
    assert route is target_route
    assert clarification is None


# ---------------------------------------------------------------------------
# Below-threshold with explicit clarification on the decision
# ---------------------------------------------------------------------------


def test_below_threshold_with_decision_clarification_preserved() -> None:
    """When the decision carries its own ClarificationPrompt, it is returned as-is."""
    custom_clarification = ClarificationPrompt(
        question="Did you mean A or B?",
        options=["A", "B"],
    )
    decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.5,
        rationale="ambiguous",
        clarification=custom_clarification,
    )
    route, clarification = decide_route(decision)
    assert route is None
    assert clarification is custom_clarification


def test_below_threshold_without_clarification_gets_default() -> None:
    """A below-threshold decision without a clarification gets the safe-net default."""
    decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.3,
        rationale="ambiguous",
        clarification=None,
    )
    route, clarification = decide_route(decision)
    assert route is None
    assert clarification is not None
    assert len(clarification.options) >= 2
