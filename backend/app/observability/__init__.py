"""Observability: structured per-request logging and an optional vendor tracer.

Every request is reconstructable from structured JSON log events keyed by a
``session_id`` correlation id. Secrets never appear in the output (see
:func:`redact`). A vendor tracer (LangSmith) is an optional, env-gated layer over
the same instrumentation points; it is never required to run.
"""

from __future__ import annotations

from .logging import (
    llm_call,
    log_route,
    redact,
    request_latency,
    retry,
    session_id,
    tool_call,
)
from .tracer import enable_vendor_tracer

__all__ = [
    "session_id",
    "log_route",
    "llm_call",
    "tool_call",
    "retry",
    "request_latency",
    "redact",
    "enable_vendor_tracer",
]
