"""Unit tests for the optional vendor tracer module.

Verifies that enable_vendor_tracer() is a no-op when no key is set and
does not raise regardless of whether langsmith is installed.
"""

from __future__ import annotations

import pytest

from app.observability.tracer import enable_vendor_tracer


def test_vendor_tracer_noop_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """enable_vendor_tracer() returns False and does not raise when no key is set."""
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    result = enable_vendor_tracer()
    assert result is False


def test_vendor_tracer_does_not_raise_on_import() -> None:
    """enable_vendor_tracer() is safe to call at app startup regardless of key state."""
    # This verifies no ImportError or other exception propagates out.
    try:
        enable_vendor_tracer()
    except Exception as exc:
        pytest.fail(f"enable_vendor_tracer() raised unexpectedly: {exc}")


def test_vendor_tracer_returns_false_when_both_keys_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both LANGSMITH_API_KEY and LANGCHAIN_API_KEY absent -> returns False."""
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert enable_vendor_tracer() is False
