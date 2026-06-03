"""Critical-path integration test: structured logs are reconstructable and redacted.

Drives a request through the hub graph (via the schema-aware fake-model seam)
while capturing structured log output, then asserts:
- The log stream contains a 'route' event naming the route taken.
- The log stream contains at least one 'llm_call' event with role and latency_ms.
- The log stream contains a 'request_latency' event with total_latency_ms.
- No captured log record contains the sentinel secret value (redaction holds).

The critical-path acceptance test for the observability feature.
"""

from __future__ import annotations

import json
import logging

import pytest

from app.graph.hub import build_hub
from app.graph.routing import Route, RoutingDecision
from app.graph.state import HubState


def _initial_state(session_id: str = "obs-test") -> HubState:
    return {
        "session_id": session_id,
        "messages": [],
        "user_message": "Give me a quick warm-up routine",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }


@pytest.mark.asyncio
async def test_request_log_reconstructable_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A hub request emits structured logs that reconstruct the full call path,
    and secrets never appear in any captured record.
    """
    from tests.conftest import FakeStructuredOutputModel
    import app.observability.logging as obs

    # Sentinel secret: set it in the environment so redaction has something to scrub.
    sentinel = "sk-test-sentinel-obs-integration"
    monkeypatch.setenv("OPENROUTER_API_KEY", sentinel)

    # Route to COACH so the whole path exercises the router + coach llm_call events.
    decision = RoutingDecision(route=Route.COACH, confidence=0.92, rationale="fitness question")
    fake = FakeStructuredOutputModel(parsed_result=decision, chat_text="Great question!")

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
    try:
        monkeypatch.setattr("app.agents.coach.graph.get_model", lambda role: fake)
    except AttributeError:
        pass

    # Set the correlation ContextVar as the request boundary would.
    session_id = "obs-integration-test"
    sid_token = obs.session_id.set(session_id)

    try:
        hub = build_hub()
        config = {"configurable": {"thread_id": session_id}}

        with caplog.at_level(logging.INFO, logger="cadence.events"):
            with obs.request_latency():
                await hub.ainvoke(_initial_state(session_id), config)
    finally:
        obs.session_id.reset(sid_token)

    # Parse all cadence.events log records as JSON.
    events = []
    for record in caplog.records:
        if record.name == "cadence.events":
            try:
                events.append(json.loads(record.message))
            except json.JSONDecodeError:
                pass  # non-JSON records (shouldn't happen) are ignored

    assert events, "No structured events were emitted — observability wiring is broken"

    # 1. A 'route' event must be present naming the committed route.
    route_events = [e for e in events if e.get("event") == "route"]
    assert route_events, f"No 'route' event found; events: {[e['event'] for e in events]}"
    assert any(
        "coach" in str(e.get("route", "")).lower() for e in route_events
    ), f"'route' event does not contain 'coach': {route_events}"

    # 2. At least one 'llm_call' event must be present with role and latency_ms.
    llm_events = [e for e in events if e.get("event") == "llm_call"]
    assert llm_events, f"No 'llm_call' event found; events: {[e['event'] for e in events]}"
    for ev in llm_events:
        assert "role" in ev, f"llm_call event missing 'role': {ev}"
        assert "latency_ms" in ev, f"llm_call event missing 'latency_ms': {ev}"
        assert ev["latency_ms"] >= 0, f"latency_ms must be non-negative: {ev}"

    # 3. A 'request_latency' event carries total wall-clock time.
    latency_events = [e for e in events if e.get("event") == "request_latency"]
    assert latency_events, f"No 'request_latency' event found; events: {[e['event'] for e in events]}"
    assert latency_events[0]["latency_ms"] >= 0

    # 4. The sentinel secret must never appear in any captured record.
    all_text = " ".join(r.message for r in caplog.records if r.name == "cadence.events")
    assert sentinel not in all_text, (
        f"Sentinel secret leaked into structured logs — redaction is broken.\n"
        f"Leaked text contains: {sentinel}"
    )


@pytest.mark.asyncio
async def test_router_llm_call_event_carries_role(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Router path emits an llm_call event with role='router'."""
    from tests.conftest import FakeStructuredOutputModel
    import app.observability.logging as obs

    decision = RoutingDecision(route=Route.COACH, confidence=0.88, rationale="test")
    fake = FakeStructuredOutputModel(parsed_result=decision)

    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
    try:
        monkeypatch.setattr("app.agents.coach.graph.get_model", lambda role: fake)
    except AttributeError:
        pass

    session_id = "router-role-test"
    sid_token = obs.session_id.set(session_id)
    try:
        hub = build_hub()
        config = {"configurable": {"thread_id": session_id}}
        with caplog.at_level(logging.INFO, logger="cadence.events"):
            await hub.ainvoke(_initial_state(session_id), config)
    finally:
        obs.session_id.reset(sid_token)

    llm_events = [
        json.loads(r.message)
        for r in caplog.records
        if r.name == "cadence.events"
        and json.loads(r.message).get("event") == "llm_call"
    ]
    roles = [e["role"] for e in llm_events]
    assert "router" in roles, f"No llm_call event with role='router'; roles seen: {roles}"
