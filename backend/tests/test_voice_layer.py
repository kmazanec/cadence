"""Tests for the voice layer (app.voice).

The voice layer is the single source of truth for all user-facing copy that
isn't domain-specific prose from a model. These tests assert the objective
floor: copy is non-empty, sourced from the voice module (not inlined
elsewhere), carries partnership markers, and replaces the prior generic strings.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Voice module: exported constants are non-empty and partnership-oriented
# ---------------------------------------------------------------------------


def test_voice_preamble_nonempty() -> None:
    """VOICE_PREAMBLE must be a non-empty string."""
    from app.voice import VOICE_PREAMBLE

    assert isinstance(VOICE_PREAMBLE, str)
    assert len(VOICE_PREAMBLE.strip()) > 0


def test_voice_preamble_contains_partnership_marker() -> None:
    """VOICE_PREAMBLE must include at least one partnership-orienting word."""
    from app.voice import VOICE_PREAMBLE

    lower = VOICE_PREAMBLE.lower()
    markers = ["partner", "we ", "let's", "you've", "together"]
    assert any(m in lower for m in markers), (
        f"VOICE_PREAMBLE lacks a partnership marker. Got: {VOICE_PREAMBLE!r}"
    )


def test_voice_preamble_not_generic() -> None:
    """VOICE_PREAMBLE must not be a bare generic-assistant string."""
    from app.voice import VOICE_PREAMBLE

    generic_phrases = ["I am a helpful assistant", "I'm a helpful assistant"]
    lower = VOICE_PREAMBLE.lower()
    for phrase in generic_phrases:
        assert phrase.lower() not in lower, (
            f"VOICE_PREAMBLE reads as a generic assistant opener: {VOICE_PREAMBLE!r}"
        )


def test_generator_failure_message_nonempty() -> None:
    """GENERATOR_FAILURE_MESSAGE must be a non-empty on-voice string."""
    from app.voice import GENERATOR_FAILURE_MESSAGE

    assert isinstance(GENERATOR_FAILURE_MESSAGE, str)
    assert len(GENERATOR_FAILURE_MESSAGE.strip()) > 0


def test_generator_failure_message_not_old_generic() -> None:
    """GENERATOR_FAILURE_MESSAGE must differ from the old hardcoded fallback."""
    from app.voice import GENERATOR_FAILURE_MESSAGE

    old = "I wasn't able to build a workout for that request. Try widening the equipment or muscle group selection."
    assert GENERATOR_FAILURE_MESSAGE.strip() != old.strip(), (
        "GENERATOR_FAILURE_MESSAGE must be the on-voice replacement, not the old copy."
    )


def test_recovery_error_message_nonempty() -> None:
    """RECOVERY_ERROR_MESSAGE must be a non-empty on-voice string."""
    from app.voice import RECOVERY_ERROR_MESSAGE

    assert isinstance(RECOVERY_ERROR_MESSAGE, str)
    assert len(RECOVERY_ERROR_MESSAGE.strip()) > 0


def test_recovery_error_message_not_old_generic() -> None:
    """RECOVERY_ERROR_MESSAGE must differ from the old hardcoded chat.py string."""
    from app.voice import RECOVERY_ERROR_MESSAGE

    old = "Something went wrong — please try again."
    assert RECOVERY_ERROR_MESSAGE.strip() != old.strip(), (
        "RECOVERY_ERROR_MESSAGE must be the on-voice replacement, not the old generic copy."
    )


# ---------------------------------------------------------------------------
# clarification_fallback: valid shape, >= 2 options, on-voice question
# ---------------------------------------------------------------------------


def test_clarification_fallback_returns_clarification_prompt() -> None:
    """clarification_fallback() returns a ClarificationPrompt."""
    from app.graph.routing import ClarificationPrompt
    from app.voice import clarification_fallback

    result = clarification_fallback()
    assert isinstance(result, ClarificationPrompt)


def test_clarification_fallback_has_two_or_more_options() -> None:
    """clarification_fallback() must return at least two concrete options."""
    from app.voice import clarification_fallback

    result = clarification_fallback()
    assert len(result.options) >= 2, (
        f"clarification_fallback must have >=2 options, got {result.options!r}"
    )


def test_clarification_fallback_question_nonempty() -> None:
    """clarification_fallback() question must be a non-empty string."""
    from app.voice import clarification_fallback

    result = clarification_fallback()
    assert isinstance(result.question, str)
    assert len(result.question.strip()) > 0


def test_clarification_fallback_question_not_old_generic() -> None:
    """clarification_fallback must not use the old inline ClarificationPrompt copy."""
    from app.voice import clarification_fallback

    old_questions = [
        "Could you tell me a bit more about what you'd like to do?",
        "Could you tell me more about what you'd like to do?",
    ]
    result = clarification_fallback()
    assert result.question.strip() not in old_questions, (
        f"clarification_fallback still uses old generic copy: {result.question!r}"
    )


# ---------------------------------------------------------------------------
# Coach system prompt: composed from VOICE_PREAMBLE
# ---------------------------------------------------------------------------


def test_coach_system_prompt_contains_voice_preamble() -> None:
    """COACH_SYSTEM_PROMPT must start with or contain VOICE_PREAMBLE."""
    from app.agents.coach.graph import COACH_SYSTEM_PROMPT
    from app.voice import VOICE_PREAMBLE

    # The preamble's core content must appear verbatim in the coach prompt.
    # Use the first 40 characters as a stable anchor.
    preamble_anchor = VOICE_PREAMBLE[:40]
    assert preamble_anchor in COACH_SYSTEM_PROMPT, (
        f"COACH_SYSTEM_PROMPT does not contain the VOICE_PREAMBLE. "
        f"Expected to find: {preamble_anchor!r}"
    )


# ---------------------------------------------------------------------------
# decide_route fallback: sourced from voice layer
# ---------------------------------------------------------------------------


def test_decide_route_fallback_matches_voice_clarification_fallback() -> None:
    """decide_route(None) must return the same question/options as clarification_fallback()."""
    from app.graph.routing import decide_route
    from app.voice import clarification_fallback

    _route, clarification = decide_route(None)
    expected = clarification_fallback()

    assert clarification is not None
    assert clarification.question == expected.question
    assert clarification.options == expected.options


def test_decide_route_below_threshold_fallback_matches_voice() -> None:
    """decide_route with a below-threshold decision also uses the voice fallback."""
    from app.graph.routing import Route, RoutingDecision, decide_route
    from app.voice import clarification_fallback

    low_conf = RoutingDecision(
        route=Route.COACH,
        confidence=0.3,
        rationale="ambiguous",
    )
    _route, clarification = decide_route(low_conf)
    expected = clarification_fallback()

    assert clarification is not None
    assert clarification.question == expected.question


# ---------------------------------------------------------------------------
# _clarify_node: fallback uses voice layer copy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clarify_node_default_matches_voice_fallback() -> None:
    """_clarify_node with no prior clarification uses voice.clarification_fallback."""
    from app.graph.hub import _clarify_node
    from app.graph.state import HubState
    from app.voice import clarification_fallback

    state: HubState = {
        "session_id": "voice-test",
        "messages": [],
        "user_message": "test",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    result = await _clarify_node(state)
    expected = clarification_fallback()

    clarification = result.get("clarification")
    assert clarification is not None
    assert clarification.question == expected.question
    assert clarification.options == expected.options


# ---------------------------------------------------------------------------
# _generator_boundary_node failure copy: sourced from voice layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_failure_copy_from_voice_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the generator produces no workout, the failure message comes from app.voice."""
    from app.voice import GENERATOR_FAILURE_MESSAGE

    class _EmptyRepo:
        def search(self, **kw):
            return []

        def get_by_id(self, id):
            return None

        def contraindicated_ids(self, injuries):
            return []

        def bilateral_pair(self, id):
            return None

    class _FakeSubgraph:
        async def ainvoke(self, inputs, **kw):
            return {"workout": None, "selected_exercise_ids": []}

    monkeypatch.setattr(
        "app.agents.generator.graph.build_generator_subgraph",
        lambda **kw: _FakeSubgraph(),
    )
    monkeypatch.setattr(
        "app.graph.hub.JsonExerciseRepository", lambda: _EmptyRepo()
    )

    from app.graph.hub import _generator_boundary_node
    from app.graph.state import HubState

    state: HubState = {
        "session_id": "voice-gen-test",
        "messages": [],
        "user_message": "build me a workout",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }

    result = await _generator_boundary_node(state)

    messages = result.get("messages", [])
    assert messages, "Expected at least one message from the generator boundary"
    content = messages[0].content
    assert content == GENERATOR_FAILURE_MESSAGE, (
        f"Generator failure copy must match GENERATOR_FAILURE_MESSAGE. "
        f"Got: {content!r}"
    )


# ---------------------------------------------------------------------------
# RECOVERY_ERROR_MESSAGE: used in chat.py error frame
# ---------------------------------------------------------------------------


def test_chat_error_frame_uses_voice_recovery_message() -> None:
    """The /chat error frame must import and use RECOVERY_ERROR_MESSAGE from app.voice."""
    import inspect

    import app.api.chat as chat_mod

    source = inspect.getsource(chat_mod)
    # The module must import from the voice layer (not inline the old literal).
    assert "RECOVERY_ERROR_MESSAGE" in source, (
        "chat.py must import RECOVERY_ERROR_MESSAGE from app.voice"
    )
    assert "from ..voice import RECOVERY_ERROR_MESSAGE" in source or "RECOVERY_ERROR_MESSAGE" in source, (
        "chat.py error frame must reference the voice layer constant"
    )
    # The old hardcoded literal must not appear as an inline string.
    old_literal = "Something went wrong — please try again."
    assert old_literal not in source, (
        f"chat.py must not inline the old error copy: {old_literal!r}. "
        f"Use RECOVERY_ERROR_MESSAGE from app.voice instead."
    )
