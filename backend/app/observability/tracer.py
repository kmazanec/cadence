"""Optional vendor tracer (LangSmith), gated on an environment key.

When a LangSmith/LangChain key is present, tracing is enabled over the same
instrumentation points the structured logger uses; when it is absent, this is a
no-op so the default path carries no vendor dependency. The ``langsmith`` import
is lazy and tolerant of being uninstalled — its absence simply means no tracing.
"""

from __future__ import annotations

import os

# Either key enables LangSmith's auto-tracing integration.
_TRACER_KEY_ENVS = ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY")


def enable_vendor_tracer() -> bool:
    """Enable the vendor tracer if its key is set; return whether it is on.

    No-ops and returns ``False`` when no key is present or the optional
    ``langsmith`` package is not installed.
    """
    if not any(os.environ.get(key) for key in _TRACER_KEY_ENVS):
        return False

    try:
        import langsmith  # noqa: F401
    except ImportError:
        return False

    # Presence of the key plus the package is sufficient: LangChain reads
    # LANGSMITH_TRACING / the key from the environment and traces automatically.
    return True
