"""Unit tests for the structured observability logging module.

Verifies: redaction correctness, JSON event shape, and context-variable
correlation id — all at the function level so no network or graph is needed.
"""

from __future__ import annotations

import json
import logging

import pytest

import app.observability.logging as obs


# ---------------------------------------------------------------------------
# redact()
# ---------------------------------------------------------------------------


def test_redact_scrubs_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """redact() replaces the live API key value with '***REDACTED***'."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-secret-key")
    result = obs.redact("Authorization: Bearer sk-test-secret-key")
    assert "sk-test-secret-key" not in result
    assert "***REDACTED***" in result


def test_redact_noop_when_key_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """redact() is a no-op when the API key environment variable is absent."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    original = "some text with no key"
    assert obs.redact(original) == original


def test_redact_noop_when_key_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """redact() is a no-op when the API key is set but blank."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    original = "some text"
    assert obs.redact(original) == original


def test_redact_replaces_all_occurrences(monkeypatch: pytest.MonkeyPatch) -> None:
    """redact() replaces every occurrence of the key in the text."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "SECRET")
    result = obs.redact("key=SECRET and also SECRET appears twice")
    assert result.count("***REDACTED***") == 2
    assert "SECRET" not in result


# ---------------------------------------------------------------------------
# Event shape — JSON validity and required keys
# ---------------------------------------------------------------------------


def test_event_is_valid_json(caplog: pytest.LogCaptureFixture) -> None:
    """Each emitted log record is valid JSON containing 'event' and 'session_id'."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        obs.log_route("coach", 0.9)

    assert len(caplog.records) >= 1
    record = caplog.records[-1]
    parsed = json.loads(record.message)
    assert "event" in parsed
    assert "session_id" in parsed


def test_session_id_default_is_empty_string(caplog: pytest.LogCaptureFixture) -> None:
    """session_id defaults to empty string when the ContextVar is not set."""
    token = obs.session_id.set("")
    try:
        with caplog.at_level(logging.INFO, logger="cadence.events"):
            obs.tool_call("search_exercises", "ok")
        record = caplog.records[-1]
        parsed = json.loads(record.message)
        assert parsed["session_id"] == ""
    finally:
        obs.session_id.reset(token)


def test_session_id_propagates_to_events(caplog: pytest.LogCaptureFixture) -> None:
    """Events carry the session_id set on the ContextVar."""
    token = obs.session_id.set("test-session-42")
    try:
        with caplog.at_level(logging.INFO, logger="cadence.events"):
            obs.tool_call("build_workout", "ok")
        record = caplog.records[-1]
        parsed = json.loads(record.message)
        assert parsed["session_id"] == "test-session-42"
    finally:
        obs.session_id.reset(token)


def test_log_route_event_shape(caplog: pytest.LogCaptureFixture) -> None:
    """log_route emits an event with 'route' and 'confidence' fields."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        obs.log_route("workout_generate", 0.85)
    parsed = json.loads(caplog.records[-1].message)
    assert parsed["event"] == "route"
    assert "route" in parsed
    assert "confidence" in parsed
    assert parsed["confidence"] == 0.85


def test_llm_call_event_shape(caplog: pytest.LogCaptureFixture) -> None:
    """llm_call emits an 'llm_call' event with role, model, and latency_ms >= 0."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        with obs.llm_call("router", "openai/gpt-4o-mini"):
            pass  # simulated model invocation
    parsed = json.loads(caplog.records[-1].message)
    assert parsed["event"] == "llm_call"
    assert parsed["role"] == "router"
    assert parsed["model"] == "openai/gpt-4o-mini"
    assert parsed["latency_ms"] >= 0


def test_tool_call_event_shape(caplog: pytest.LogCaptureFixture) -> None:
    """tool_call emits a 'tool_call' event with name and outcome."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        obs.tool_call("search_exercises", "ok")
    parsed = json.loads(caplog.records[-1].message)
    assert parsed["event"] == "tool_call"
    assert parsed["name"] == "search_exercises"
    assert parsed["outcome"] == "ok"


def test_retry_event_shape(caplog: pytest.LogCaptureFixture) -> None:
    """retry() emits a 'retry' event."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        obs.retry()
    parsed = json.loads(caplog.records[-1].message)
    assert parsed["event"] == "retry"


def test_request_latency_event_shape(caplog: pytest.LogCaptureFixture) -> None:
    """request_latency emits a 'request_latency' event with latency_ms >= 0."""
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        with obs.request_latency():
            pass
    parsed = json.loads(caplog.records[-1].message)
    assert parsed["event"] == "request_latency"
    assert parsed["latency_ms"] >= 0


def test_secret_never_appears_in_json_events(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Secret values are scrubbed before the event JSON hits the log."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-leak-test")
    with caplog.at_level(logging.INFO, logger="cadence.events"):
        obs.tool_call("build_workout", "error: sk-leak-test exposed")
    record_text = caplog.records[-1].message
    assert "sk-leak-test" not in record_text
    assert "***REDACTED***" in record_text
