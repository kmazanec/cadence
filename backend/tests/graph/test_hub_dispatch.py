"""Integration tests: the compiled hub dispatches to the correct subgraph node or
to the clarification node based on the router's structured-output decision.

Why this file: the conditional-edge map must be exhaustive over the closed Route
enum plus the clarify branch; driving the full compiled graph with controlled
decisions verifies the wiring end-to-end with zero LLM variance.
"""

from __future__ import annotations

import pytest

from app.graph.routing import ClarificationPrompt, Route, RoutingDecision
from app.graph.state import HubState


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _initial_state(session_id: str = "dispatch-test") -> HubState:
    return {
        "session_id": session_id,
        "messages": [],
        "user_message": "test",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }


# ---------------------------------------------------------------------------
# COACH route dispatches to coach_boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_dispatch_coach(monkeypatch: pytest.MonkeyPatch) -> None:
    """A COACH decision above threshold reaches the coach_boundary node."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="clear fitness question")
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
    try:
        monkeypatch.setattr("app.agents.coach.graph.get_model", lambda role: fake)
    except AttributeError:
        pass

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "dispatch-coach"}}
    result = await hub.ainvoke(_initial_state("dispatch-coach"), config)

    assert result["route"] == Route.COACH
    assert result["subgraph_result"] is not None
    assert result["subgraph_result"].kind == "coach"
    assert result["clarification"] is None


# ---------------------------------------------------------------------------
# WORKOUT_GENERATE route dispatches (currently falls to response_assembly stub)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_dispatch_workout_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A WORKOUT_GENERATE decision above threshold commits the route (generator stub present)."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(
        route=Route.WORKOUT_GENERATE, confidence=0.95, rationale="build workout request"
    )
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "dispatch-generate"}}
    result = await hub.ainvoke(_initial_state("dispatch-generate"), config)

    assert result["route"] == Route.WORKOUT_GENERATE
    assert result["clarification"] is None


# ---------------------------------------------------------------------------
# WORKOUT_LOG route dispatches (currently falls to response_assembly stub)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_dispatch_workout_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """A WORKOUT_LOG decision above threshold commits the route (logger stub present)."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(
        route=Route.WORKOUT_LOG, confidence=0.88, rationale="log workout"
    )
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "dispatch-log"}}
    result = await hub.ainvoke(_initial_state("dispatch-log"), config)

    assert result["route"] == Route.WORKOUT_LOG
    assert result["clarification"] is None


# ---------------------------------------------------------------------------
# Below-threshold → clarification node, no subgraph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_dispatch_below_threshold_clarifies(monkeypatch: pytest.MonkeyPatch) -> None:
    """A below-threshold decision reaches the clarify node and produces no subgraph result."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.5,
        rationale="ambiguous",
        clarification=ClarificationPrompt(
            question="What would you like to do?",
            options=["Ask a question", "Build a workout", "Log a workout"],
        ),
    )
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "dispatch-clarify"}}
    result = await hub.ainvoke(_initial_state("dispatch-clarify"), config)

    assert result["route"] is None
    assert result["clarification"] is not None
    assert len(result["clarification"].options) >= 2
    assert result["subgraph_result"] is None


# ---------------------------------------------------------------------------
# Null parse (structured-output failure) → clarification, no dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_dispatch_null_parse_clarifies(monkeypatch: pytest.MonkeyPatch) -> None:
    """A null parse from the router triggers safe-net clarification without dispatching."""
    from tests.conftest import FakeStructuredOutputModel

    # simulate_null_parse=True makes with_structured_output emit parsed=None
    fake = FakeStructuredOutputModel(simulate_null_parse=True)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    from app.graph.hub import build_hub

    hub = build_hub()
    config = {"configurable": {"thread_id": "dispatch-null-parse"}}
    result = await hub.ainvoke(_initial_state("dispatch-null-parse"), config)

    assert result["route"] is None
    assert result["clarification"] is not None
    assert result["subgraph_result"] is None


# ---------------------------------------------------------------------------
# Conditional edge map covers every Route value
# ---------------------------------------------------------------------------


def test_route_edge_exhaustive_over_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    """The _route_edge function handles every member of the Route enum."""
    from app.graph.hub import _route_edge
    from app.graph.routing import Route

    handled: set[str] = set()
    for member in Route:
        # Simulate a state where the route is committed above threshold
        state: HubState = {  # type: ignore[typeddict-item]
            "route": member,
            "clarification": None,
        }
        result = _route_edge(state)
        handled.add(result)

    # Clarify branch
    clarify_state: HubState = {  # type: ignore[typeddict-item]
        "route": None,
        "clarification": ClarificationPrompt(question="?", options=["A", "B"]),
    }
    clarify_result = _route_edge(clarify_state)
    assert clarify_result == "clarify"

    # All Route members were handled (none fell through to clarify implicitly)
    assert all(r != "clarify" for r in handled), "A route member fell through to clarify unexpectedly"
