"""The single source of voice copy.

Every user-facing string the backend authors — the persona preamble prepended to
agent prompts, the fallback clarification, and the failure/recovery messages —
lives here so the product speaks with one voice. Components consume these
constants rather than inlining their own wording. The voice itself (a
knowledgeable training partner: conversational, confident, partnership-oriented)
is documented in ``frontend/BRAND.md``.
"""

from __future__ import annotations

from .graph.routing import ClarificationPrompt

VOICE_PREAMBLE: str = (
    "You are Cadence, a knowledgeable training partner. Speak conversationally "
    "and directly to the person, not at them. Be confident: give a clear "
    "recommendation, then the reasoning. Be partnership-oriented and "
    "results-focused. Don't sound clinical, hedged, or robotic, and don't bury "
    "the answer under disclaimers."
)

GENERATOR_FAILURE_MESSAGE: str = (
    "I couldn't put a workout together for that one. Let's try again with a bit "
    "more to go on — tell me the muscle groups or equipment you've got."
)

RECOVERY_ERROR_MESSAGE: str = (
    "Something tripped up on my end. Give it another go and we'll pick up right "
    "where we left off."
)


def clarification_fallback() -> ClarificationPrompt:
    """The clarifying question to ask when intent can't be determined."""

    return ClarificationPrompt(
        question="Tell me a bit more about what you'd like to do.",
        options=[
            "Ask a fitness question",
            "Build me a workout",
            "Log a workout I did",
        ],
    )
