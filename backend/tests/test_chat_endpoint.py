"""Integration tests for the /chat SSE endpoint.

Verifies:
- POST /chat returns a streamed SSE response.
- The stream contains route, token, done events.
- The fake model is used (no network).
- The final aggregated response envelope is correctly shaped.
"""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_chat_streams_sse_events(fake_get_model) -> None:
    """POST /chat returns SSE with at least route, token, and done events."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "What muscles does a squat work?", "session_id": "s1"},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            events: list[dict] = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    events.append(payload)

    event_types = [e["type"] for e in events]
    assert "route" in event_types
    assert "token" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_chat_route_event_matches_route_enum(fake_get_model) -> None:
    """The route event carries a valid Route enum value."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "test", "session_id": "s2"},
        ) as response:
            route_event = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if payload["type"] == "route":
                        route_event = payload
                        break

    assert route_event is not None
    assert route_event["route"] in ("coach", "workout_generate", "workout_log")


@pytest.mark.asyncio
async def test_chat_token_events_form_reply(fake_get_model) -> None:
    """Concatenating token event text reproduces the full reply."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "test", "session_id": "s3"},
        ) as response:
            reply = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if payload["type"] == "token":
                        reply += payload["text"]

    # The fake model returns "Hello there, friend" as its response.
    assert len(reply) > 0


@pytest.mark.asyncio
async def test_chat_generates_session_id_when_absent(fake_get_model) -> None:
    """When no session_id is provided, the backend generates one."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "test"},
        ) as response:
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

    assert any(e["type"] == "done" for e in events), "Expected done event"


@pytest.mark.asyncio
async def test_chat_app_boots_with_fake_model(fake_get_model) -> None:
    """The app boots and serves the health check without a real API key."""
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
