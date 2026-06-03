"""Structured JSON logging for request reconstruction.

Each instrumentation point emits one JSON object on the ``cadence.events``
logger. Every event carries at least ``event`` (its type) and ``session_id``
(the request correlation id, read from a context variable so call sites need not
thread it through). Secrets are scrubbed via :func:`redact` before anything is
written.

The timing helpers (:func:`llm_call`, :func:`request_latency`) are context
managers so a caller wraps the work it measures; the event is emitted on exit
with the elapsed duration. Token usage and richer fields are layered on at the
call sites without reshaping this contract.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from ..models.config import API_KEY_ENV

# Request correlation id. Set once per request (thread_id == session_id) so every
# event emitted while handling that request is attributable to it.
session_id: ContextVar[str] = ContextVar("session_id", default="")

_logger = logging.getLogger("cadence.events")


def redact(text: str) -> str:
    """Return ``text`` with the live API key replaced by a fixed marker.

    Scrubs the value currently in ``os.environ[API_KEY_ENV]`` so a key that
    leaks into a model echo or error string never reaches the logs (ADR-015).
    A blank/absent key is a no-op.
    """
    secret = os.environ.get(API_KEY_ENV)
    if not secret:
        return text
    return text.replace(secret, "***REDACTED***")


def _emit(event: str, **fields: object) -> None:
    """Serialise one structured event as a single redacted JSON line."""
    payload: dict[str, object] = {"event": event, "session_id": session_id.get()}
    payload.update(fields)
    _logger.info(redact(json.dumps(payload, default=str)))


def log_route(route: object, confidence: float | None) -> None:
    """Record the route a request was classified into and the confidence."""
    _emit("route", route=str(route), confidence=confidence)


@contextmanager
def llm_call(role: str, model: str) -> Iterator[None]:
    """Measure and record one model call by role and model id."""
    start = time.perf_counter()
    try:
        yield
    finally:
        _emit("llm_call", role=role, model=model, latency_ms=_elapsed_ms(start))


def tool_call(name: str, outcome: str) -> None:
    """Record a tool invocation by name and its outcome (e.g. ok/error)."""
    _emit("tool_call", name=name, outcome=outcome)


def retry() -> None:
    """Record a single retry attempt within a request."""
    _emit("retry")


@contextmanager
def request_latency() -> Iterator[None]:
    """Measure and record the total wall-clock latency of a request."""
    start = time.perf_counter()
    try:
        yield
    finally:
        _emit("request_latency", latency_ms=_elapsed_ms(start))


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
