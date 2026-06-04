"""Tests for the ExplanationEvent SSE frame.

Verifies that:
- A workout turn with non-empty explanation emits an
  {type:'explanation', reasons:[...]} frame carrying at least one
  excluded/loads_joint reason (the injury case).
- A coach turn emits NO explanation frame (the gate prevents it).

Strategy: the explanation is built by the generator boundary node from
committed state. Rather than driving a full generator run, we patch
``assemble_response`` to return a deterministic ChatResponse with the
explanation field pre-populated, so the test remains fast and network-free
while still exercising the emit path in ``chat.py``.
"""

from __future__ import annotations

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.schemas import ChatResponse
from app.graph.explanation import Reason
from app.graph.routing import Route


_EXCLUDED_REASON = Reason(
    claim="excluded",
    relation="loads_joint",
    subject="Barbell Squat",
    object="knee",
)

_INCLUDED_REASON = Reason(
    claim="included",
    relation="matches_target",
    subject="Push-Up",
    object="chest",
)


async def _collect_events(app, message: str, session_id: str) -> list[dict]:
    """Stream /chat and return all SSE event dicts."""
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


@pytest.mark.asyncio
async def test_explanation_event_emitted_on_workout_turn(fake_get_model, monkeypatch) -> None:
    """Workout turn with non-empty explanation emits {type:'explanation'} frame.

    The assertion focuses on the transport path: the event appears in the
    stream with the correct shape when assemble_response returns reasons.
    """
    from app.agents.generator.schemas import WorkoutPayload
    from app.api.schemas import ChatResponse

    workout_response = ChatResponse(
        route=Route.WORKOUT_GENERATE,
        reply_text="",
        structured=WorkoutPayload(blocks=[]),
        explanation=[_EXCLUDED_REASON, _INCLUDED_REASON],
        clarification=None,
    )

    # Patch assemble_response to inject our deterministic ChatResponse.
    monkeypatch.setattr(
        "app.api.chat.assemble_response",
        lambda state: workout_response,
    )

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "chest workout, bad knee", "expl-workout")

    explanation_events = [e for e in events if e.get("type") == "explanation"]
    assert explanation_events, (
        f"Expected an explanation event; got types: {[e.get('type') for e in events]}"
    )

    evt = explanation_events[0]
    assert "reasons" in evt, f"explanation event missing 'reasons' key: {evt}"
    assert isinstance(evt["reasons"], list), "reasons must be a list"
    assert len(evt["reasons"]) == 2, f"Expected 2 reasons; got {len(evt['reasons'])}"

    # Verify the excluded/loads_joint reason is transported faithfully.
    excluded = [r for r in evt["reasons"] if r["claim"] == "excluded" and r["relation"] == "loads_joint"]
    assert excluded, (
        f"Expected excluded/loads_joint reason in stream; got: {evt['reasons']}"
    )
    assert excluded[0]["object"] == "knee"


@pytest.mark.asyncio
async def test_no_explanation_event_on_coach_turn(fake_get_model, monkeypatch) -> None:
    """Coach turn (no reasons) must NOT emit an explanation frame.

    The emit is gated on response.explanation being truthy; empty list → no event.
    """
    from app.api.schemas import ChatResponse

    coach_response = ChatResponse(
        route=Route.COACH,
        reply_text="Great question!",
        structured=None,
        explanation=[],
        clarification=None,
    )

    monkeypatch.setattr(
        "app.api.chat.assemble_response",
        lambda state: coach_response,
    )

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "What muscles does a squat work?", "expl-coach")

    explanation_events = [e for e in events if e.get("type") == "explanation"]
    assert not explanation_events, (
        f"Coach turn must not emit explanation event; got: {explanation_events}"
    )


@pytest.mark.asyncio
async def test_explanation_event_before_done(fake_get_model, monkeypatch) -> None:
    """The explanation event must appear before the done event in stream order."""
    from app.agents.generator.schemas import WorkoutPayload
    from app.api.schemas import ChatResponse

    workout_response = ChatResponse(
        route=Route.WORKOUT_GENERATE,
        reply_text="",
        structured=WorkoutPayload(blocks=[]),
        explanation=[_EXCLUDED_REASON],
        clarification=None,
    )

    monkeypatch.setattr(
        "app.api.chat.assemble_response",
        lambda state: workout_response,
    )

    from app.main import create_app
    app = create_app()

    events = await _collect_events(app, "build workout", "expl-order")

    types = [e.get("type") for e in events]
    assert "explanation" in types, f"explanation event missing; got: {types}"
    assert "done" in types, "done event must be present"

    expl_idx = types.index("explanation")
    done_idx = types.index("done")
    assert expl_idx < done_idx, (
        f"explanation ({expl_idx}) must precede done ({done_idx}) in {types}"
    )
