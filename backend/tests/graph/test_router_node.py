"""Tests for the router node: structured-output classification + include_raw safe-net.

Why this file: the router node must populate state from a controlled
with_structured_output(include_raw=True) result and clarify on a null parse.
Tests inject a fake model via the get_model seam so no network is involved.
"""

from __future__ import annotations

import pytest

from app.graph.routing import (
    ClarificationPrompt,
    Route,
    RoutingDecision,
)
from app.graph.state import HubState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(user_message: str = "test message") -> HubState:
    return {
        "session_id": "test-session",
        "messages": [],
        "user_message": user_message,
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }


def _fake(parsed_result: RoutingDecision | None = None, *, null_parse: bool = False):
    """Return a FakeStructuredOutputModel from conftest for use in monkeypatching."""
    from tests.conftest import FakeStructuredOutputModel

    if null_parse:
        return FakeStructuredOutputModel(simulate_null_parse=True)
    return FakeStructuredOutputModel(parsed_result=parsed_result)


# ---------------------------------------------------------------------------
# Tests: high-confidence route populates state correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target_route",
    [Route.COACH, Route.WORKOUT_GENERATE, Route.WORKOUT_LOG],
)
async def test_router_node_populates_route_fields(
    monkeypatch: pytest.MonkeyPatch, target_route: Route
) -> None:
    """A high-confidence RoutingDecision is stored into route/routing_confidence/routing_raw."""
    decision = RoutingDecision(route=target_route, confidence=0.9, rationale="clear intent")
    model = _fake(decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: model)

    from app.graph.hub import _router_node

    result = await _router_node(_make_state())

    assert result["route"] == target_route
    assert result["routing_confidence"] == pytest.approx(0.9)
    assert result["routing_raw"] is not None
    assert result.get("clarification") is None


@pytest.mark.asyncio
async def test_router_node_stores_routing_raw_as_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """routing_raw is stored as a dict (the serialized raw structured-output capture)."""
    decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="test")
    model = _fake(decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: model)

    from app.graph.hub import _router_node

    result = await _router_node(_make_state())
    assert isinstance(result["routing_raw"], dict)


# ---------------------------------------------------------------------------
# Tests: null parse → clarify, not dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_node_null_parse_sets_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When parsed is None (structured-output failure), route is None and clarification is set."""
    model = _fake(null_parse=True)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: model)

    from app.graph.hub import _router_node

    result = await _router_node(_make_state())
    assert result["route"] is None
    assert result["clarification"] is not None
    assert isinstance(result["clarification"], ClarificationPrompt)


@pytest.mark.asyncio
async def test_router_node_null_parse_has_no_routing_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed parse leaves routing_confidence as None."""
    model = _fake(null_parse=True)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: model)

    from app.graph.hub import _router_node

    result = await _router_node(_make_state())
    assert result.get("routing_confidence") is None


# ---------------------------------------------------------------------------
# Tests: below-threshold → clarify, not dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_node_low_confidence_sets_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A below-threshold decision results in clarification, not a route."""
    decision = RoutingDecision(route=Route.COACH, confidence=0.5, rationale="ambiguous")
    model = _fake(decision)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: model)

    from app.graph.hub import _router_node

    result = await _router_node(_make_state())
    assert result["route"] is None
    assert result["clarification"] is not None
    assert result["routing_confidence"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Tests: no keyword/regex imports
# ---------------------------------------------------------------------------


def test_router_node_uses_no_keyword_logic() -> None:
    """The router node module must not import 're' (structured-output only, no regex)."""
    import ast
    import inspect

    import app.graph.hub as hub_module

    source = inspect.getsource(hub_module)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert name != "re", "hub.py must not import 're' — routing must use structured output only"
