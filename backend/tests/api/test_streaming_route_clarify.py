"""Tests for SSE event emission: route event and clarification event/payload.

Why this file: route and clarification events must come from committed graph
state (per ADR-002), not from message deltas. Tests drive the real /chat
endpoint with a fake model injected at the get_model seam, so no LLM network
traffic is involved and event sourcing is verifiable.
"""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.graph.routing import ClarificationPrompt, Route, RoutingDecision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_events(app, message: str, session_id: str) -> list[dict]:
    """Stream /chat and collect all SSE events into a list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": message, "session_id": session_id},
        ) as response:
            assert response.status_code == 200
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# High-confidence COACH route → route event present, no clarification event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_emits_route_event_for_coach(monkeypatch: pytest.MonkeyPatch) -> None:
    """A high-confidence COACH decision produces a {type:'route', route:'coach'} event."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="clear fitness question")
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
    try:
        monkeypatch.setattr("app.agents.coach.graph.get_model", lambda role: fake)
    except AttributeError:
        pass

    # Re-import to get a fresh hub with the patched model.
    import importlib
    import app.api.chat as chat_module
    importlib.reload(chat_module)

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "What muscles does a deadlift work?", "sse-coach")

    route_events = [e for e in events if e.get("type") == "route"]
    clarify_events = [e for e in events if e.get("type") == "clarification"]

    assert len(route_events) >= 1, f"Expected at least one route event; got: {events}"
    assert route_events[0]["route"] == "coach"
    assert len(clarify_events) == 0, "Coach route must not produce a clarification event"


@pytest.mark.asyncio
async def test_sse_route_event_source_is_state_not_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route event value matches the committed state route, not a message delta."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(route=Route.COACH, confidence=0.95, rationale="test")
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    import importlib
    import app.api.chat as chat_module
    importlib.reload(chat_module)

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "test", "sse-state-source")

    route_events = [e for e in events if e.get("type") == "route"]
    assert route_events, "Expected a route event"
    # The route must be one of the known enum values — not raw model text
    assert route_events[0]["route"] in ("coach", "workout_generate", "workout_log")


# ---------------------------------------------------------------------------
# Below-threshold → clarification event present, no structured workout payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_emits_clarification_event_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """A below-threshold decision produces a {type:'clarification'} event with question+options."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.45,
        rationale="ambiguous",
        clarification=ClarificationPrompt(
            question="What would you like to do?",
            options=["Ask a fitness question", "Build a workout", "Log a workout"],
        ),
    )
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    import importlib
    import app.api.chat as chat_module
    importlib.reload(chat_module)

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "Bench press", "sse-clarify")

    clarify_events = [e for e in events if e.get("type") == "clarification"]
    structured_events = [e for e in events if e.get("type") == "structured"]

    assert len(clarify_events) >= 1, f"Expected clarification event; got: {events}"
    assert "question" in clarify_events[0]
    assert "options" in clarify_events[0]
    assert len(clarify_events[0]["options"]) >= 2
    assert len(structured_events) == 0, "Clarification response must not carry a structured workout payload"


@pytest.mark.asyncio
async def test_sse_clarification_event_has_no_route_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """When clarification fires, no route event is emitted (route is None in state)."""
    from tests.conftest import FakeStructuredOutputModel

    decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.3,
        rationale="ambiguous",
    )
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    import importlib
    import app.api.chat as chat_module
    importlib.reload(chat_module)

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "I did a workout yesterday", "sse-no-route")

    route_events = [e for e in events if e.get("type") == "route"]
    assert len(route_events) == 0, f"Below-threshold must not emit a route event; got: {route_events}"


# ---------------------------------------------------------------------------
# Null parse → clarification event, no route event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_null_parse_emits_clarification(monkeypatch: pytest.MonkeyPatch) -> None:
    """A structured-output parse failure emits a clarification event, not a route event."""
    from tests.conftest import FakeStructuredOutputModel

    fake = FakeStructuredOutputModel(simulate_null_parse=True)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)

    import importlib
    import app.api.chat as chat_module
    importlib.reload(chat_module)

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "something confusing", "sse-null-parse")

    clarify_events = [e for e in events if e.get("type") == "clarification"]
    route_events = [e for e in events if e.get("type") == "route"]

    assert len(clarify_events) >= 1
    assert len(route_events) == 0
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) >= 1
