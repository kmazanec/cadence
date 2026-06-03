"""Integration test: the /chat API error boundary.

Proves that any exception escaping the hub graph is caught at the SSE boundary,
emitted as a structured ``{type:'error', message:...}`` event, and never surfaces
as a 500 HTTP response or a raw traceback visible to the client.

This test forces a node to throw inside the graph (via an injected fake model
that raises), drives a /chat POST, and asserts:
1. The HTTP response is 200 (streaming starts before the error occurs).
2. The SSE stream terminates with a ``type:error`` event.
3. The error message contains no traceback text ('Traceback', 'File "',
   exception class repr).
4. The error message is human-meaningful (non-empty, not a Python repr).

Contract: SSE event envelope error variant (frozen in backend/app/api/streaming.py).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of event dicts."""
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            payload = line[len("data: "):]
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_error_boundary_emits_error_event_not_traceback(monkeypatch):
    """Force the hub graph to raise and verify a clean error event is emitted.

    The model seam is replaced with a model that raises RuntimeError when
    invoked; this propagates through the router node and the error boundary
    must catch it before any traceback crosses the HTTP trust boundary.
    """

    class _BoomModel(BaseChatModel):
        """A model that always raises when invoked."""

        @property
        def _llm_type(self) -> str:
            return "boom"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("Injected failure for test")

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("Injected failure for test")

        def with_structured_output(self, schema, **kwargs):
            """Override to raise on invoke too."""
            parent = self

            class _StructuredBoom:
                async def ainvoke(self, *args, **kwargs):
                    raise RuntimeError("Injected failure for test")

                def invoke(self, *args, **kwargs):
                    raise RuntimeError("Injected failure for test")

            return _StructuredBoom()

    def _fake_get_model(role):
        return _BoomModel()

    monkeypatch.setattr("app.models.factory.get_model", _fake_get_model)

    # Re-import and rebuild after patching so the hub picks up the fake model.
    import importlib
    import app.api.chat as chat_module

    # Patch the hub instance inside the chat module to force a rebuild.
    from app.graph.hub import build_hub

    new_hub = build_hub()
    monkeypatch.setattr(chat_module, "_hub", new_hub)

    from app.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/chat",
        json={"message": "what exercises help with back pain?"},
    )

    # HTTP must not be 500 — streaming already started.
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    events = _parse_sse_events(response.text)
    types = [e.get("type") for e in events]

    # The stream must contain an error event.
    assert "error" in types, f"Expected 'error' event in {types}"

    # Find the error event and inspect it.
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) >= 1

    error_msg = error_events[0].get("message", "")

    # The message must be human-readable and non-empty.
    assert error_msg, "Error event message must not be empty"

    # The message must NOT contain traceback text.
    forbidden = ["Traceback", 'File "', "RuntimeError", "Exception", "Error:"]
    for forbidden_text in forbidden:
        assert forbidden_text not in error_msg, (
            f"Error event message leaks internal detail: {error_msg!r} "
            f"contains {forbidden_text!r}"
        )


def test_error_event_message_is_human_readable(monkeypatch):
    """Verify the error message is a proper human-facing string, not a Python repr."""

    class _BoomModel(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "boom"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise ValueError("boom")

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            raise ValueError("boom")

        def with_structured_output(self, schema, **kwargs):
            class _Boom:
                async def ainvoke(self, *args, **kwargs):
                    raise ValueError("boom")

            return _Boom()

    monkeypatch.setattr("app.models.factory.get_model", lambda _role: _BoomModel())

    import app.api.chat as chat_module
    from app.graph.hub import build_hub

    monkeypatch.setattr(chat_module, "_hub", build_hub())

    from app.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/chat", json={"message": "build me a workout"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    error_events = [e for e in events if e.get("type") == "error"]
    assert error_events, "Expected at least one error event"

    msg = error_events[0]["message"]
    # Message should look like normal English prose, not a Python exception repr.
    assert len(msg) > 10, "Error message is suspiciously short"
    assert "<" not in msg, "Error message looks like a Python repr"
    assert "Traceback" not in msg
