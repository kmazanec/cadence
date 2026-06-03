"""Integration tests for multi-turn session memory.

Verifies that:
- Prior conversation context reaches the router, coach, and generator subgraphs.
- The coach model sees the current user_message exactly once per turn (regression
  for the double-append bug: the router appends HumanMessage before the coach
  boundary, and _answer_node re-appends it, so the boundary must forward only
  prior history).
- Two distinct sessions remain isolated from each other.
- Re-invoking a thread with fresh initial state does not duplicate messages.
- The generator receives prior context so 'make it shorter' can adjust the workout.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.graph.hub import build_hub
from app.graph.routing import ClarificationPrompt, Route, RoutingDecision
from app.graph.state import HubState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _initial(session_id: str, user_message: str) -> HubState:
    """Return a fresh initial state dict for one hub turn."""
    return {
        "session_id": session_id,
        "messages": [],
        "user_message": user_message,
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }


def _install_fake(monkeypatch, decision: RoutingDecision | None = None, text: str = "Great question!") -> None:
    """Install the schema-aware fake across all seams."""
    from tests.conftest import FakeStructuredOutputModel

    fake = FakeStructuredOutputModel(parsed_result=decision, chat_text=text)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: fake)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: fake)
    try:
        monkeypatch.setattr("app.agents.coach.graph._factory.get_model", lambda role: fake)
    except AttributeError:
        pass
    try:
        monkeypatch.setattr("app.agents.generator.graph._factory.get_model", lambda role: fake)
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Chunk 1: No-turn duplication on re-invocation (criterion 3 regression lock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_turn_duplication_on_reinvocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-invoking the same thread_id twice with fresh initial dicts (messages:[])
    yields exactly four messages in order [Human, AI, Human, AI] with the two
    distinct user_message strings — no accumulator doubling.

    This locks current correct behavior of the MemorySaver + add_messages reducer.
    Passing messages:[] on the second invocation is a no-op; the checkpointer
    already holds the prior turn.
    """
    coach_decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="coach")
    _install_fake(monkeypatch, decision=coach_decision, text="That is a great technique.")

    hub = build_hub()
    session = "no-doubling-session"

    # Turn 1
    result1 = await hub.ainvoke(
        _initial(session, "How do I squat properly?"),
        {"configurable": {"thread_id": session}},
    )
    assert result1 is not None

    # Turn 2 — re-pass the full initial dict with messages:[]
    result2 = await hub.ainvoke(
        _initial(session, "What about deadlifts?"),
        {"configurable": {"thread_id": session}},
    )
    msgs_after_2 = result2["messages"]

    # Exactly 4 messages: [Human1, AI1, Human2, AI2]
    assert len(msgs_after_2) == 4, (
        f"Expected 4 messages after 2 turns, got {len(msgs_after_2)}: "
        + str([
            type(m).__name__ + ": " + (m.content[:40] if hasattr(m, "content") else "?")
            for m in msgs_after_2
        ])
    )

    human_msgs = [m for m in msgs_after_2 if isinstance(m, HumanMessage)]
    ai_msgs = [m for m in msgs_after_2 if isinstance(m, AIMessage)]
    assert len(human_msgs) == 2, f"Expected 2 HumanMessages, got {len(human_msgs)}"
    assert len(ai_msgs) == 2, f"Expected 2 AIMessages, got {len(ai_msgs)}"

    # The two user_message strings must appear in order.
    assert human_msgs[0].content == "How do I squat properly?"
    assert human_msgs[1].content == "What about deadlifts?"


# ---------------------------------------------------------------------------
# Chunk 2: Coach double-append fix + prior-context (criteria 2 + bug regression)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coach_sees_current_turn_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """On any coach turn the current user_message must appear exactly once in the
    coach model's ainvoke input (not twice).

    Live bug: the router appends HumanMessage(user_message) to HubState.messages
    BEFORE the coach boundary node runs. If the boundary forwards the full messages
    list (including that just-appended turn) AND _answer_node re-appends
    HumanMessage(user_message), the coach model receives the current turn twice.
    The boundary must forward only PRIOR history.
    """
    coach_decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="coach")

    captured_inputs: list[list[BaseMessage]] = []

    class _SpyModel:
        """Minimal model that records the messages it receives."""

        def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs):
            from langchain_core.runnables import RunnableLambda

            if schema is not RoutingDecision:
                try:
                    instance = schema()
                except Exception:
                    instance = None
                if include_raw:
                    return RunnableLambda(
                        lambda _: {"raw": AIMessage(content=""), "parsed": instance, "parsing_error": None}
                    )
                return RunnableLambda(lambda _: instance)

            result = {"raw": AIMessage(content=""), "parsed": coach_decision, "parsing_error": None}
            return RunnableLambda(lambda _: result)

        async def ainvoke(self, messages, **kwargs):
            captured_inputs.append(list(messages))
            return AIMessage(content="Here is your answer.")

        async def _astream(self, messages, **kwargs):
            from langchain_core.messages import AIMessageChunk

            yield AIMessageChunk(content="Here is your answer.")

        def bind_tools(self, tools, **kwargs):
            return self

    spy = _SpyModel()
    monkeypatch.setattr("app.models.factory.get_model", lambda role: spy)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: spy)
    try:
        monkeypatch.setattr("app.agents.coach.graph._factory.get_model", lambda role: spy)
    except AttributeError:
        pass

    hub = build_hub()
    session = "coach-once-session"

    captured_inputs.clear()
    await hub.ainvoke(
        _initial(session, "How do I improve my squat?"),
        {"configurable": {"thread_id": session}},
    )

    # The coach call is the one where the current user message is present.
    coach_calls = [
        msgs
        for msgs in captured_inputs
        if any(
            isinstance(m, HumanMessage) and m.content == "How do I improve my squat?"
            for m in msgs
        )
    ]
    assert coach_calls, "No coach model call captured"

    for call_msgs in coach_calls:
        occurrences = sum(
            1
            for m in call_msgs
            if isinstance(m, HumanMessage) and m.content == "How do I improve my squat?"
        )
        assert occurrences == 1, (
            f"Current user_message appeared {occurrences} times in coach model input (expected 1). "
            f"Messages: {[type(m).__name__ + ': ' + (m.content[:60] if hasattr(m, 'content') else '?') for m in call_msgs]}"
        )


@pytest.mark.asyncio
async def test_coach_sees_prior_turn_on_second_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """On turn 2 of a coach session, the coach model's input contains the prior
    turn's messages AND the current turn appears exactly once.
    """
    coach_decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="coach")

    captured_inputs: list[list[BaseMessage]] = []

    class _SpyModel:
        def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs):
            from langchain_core.runnables import RunnableLambda

            if schema is not RoutingDecision:
                try:
                    instance = schema()
                except Exception:
                    instance = None
                if include_raw:
                    return RunnableLambda(
                        lambda _: {"raw": AIMessage(content=""), "parsed": instance, "parsing_error": None}
                    )
                return RunnableLambda(lambda _: instance)

            result = {"raw": AIMessage(content=""), "parsed": coach_decision, "parsing_error": None}
            return RunnableLambda(lambda _: result)

        async def ainvoke(self, messages, **kwargs):
            captured_inputs.append(list(messages))
            return AIMessage(content="Here is your answer.")

        async def _astream(self, messages, **kwargs):
            from langchain_core.messages import AIMessageChunk

            yield AIMessageChunk(content="Here is your answer.")

        def bind_tools(self, tools, **kwargs):
            return self

    spy = _SpyModel()
    monkeypatch.setattr("app.models.factory.get_model", lambda role: spy)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: spy)
    try:
        monkeypatch.setattr("app.agents.coach.graph._factory.get_model", lambda role: spy)
    except AttributeError:
        pass

    hub = build_hub()
    session = "coach-prior-session"

    # Turn 1
    await hub.ainvoke(_initial(session, "How do I squat?"), {"configurable": {"thread_id": session}})

    captured_inputs.clear()

    # Turn 2
    await hub.ainvoke(
        _initial(session, "Now tell me about deadlifts."),
        {"configurable": {"thread_id": session}},
    )

    coach_calls = [
        msgs
        for msgs in captured_inputs
        if any(
            isinstance(m, HumanMessage) and m.content == "Now tell me about deadlifts."
            for m in msgs
        )
    ]
    assert coach_calls, "No turn-2 coach model call captured"

    for call_msgs in coach_calls:
        current_count = sum(
            1
            for m in call_msgs
            if isinstance(m, HumanMessage) and m.content == "Now tell me about deadlifts."
        )
        assert current_count == 1, f"Current turn appeared {current_count} times (expected 1)"

        prior_count = sum(
            1
            for m in call_msgs
            if isinstance(m, HumanMessage) and m.content == "How do I squat?"
        )
        assert prior_count >= 1, "Prior turn-1 HumanMessage not found in turn-2 coach input"


# ---------------------------------------------------------------------------
# Chunk 4: Router sees prior messages on clarify-answer (criterion 2 part B)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_sees_prior_messages_on_clarify_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn 1 produces a clarification (low-confidence router). Turn 2 is the user's
    answer. Assert that the router's structured-model is invoked with the prior
    turn messages present in its input on turn 2.
    """
    clarify_decision = RoutingDecision(
        route=Route.COACH,
        confidence=0.5,
        rationale="ambiguous",
        clarification=ClarificationPrompt(
            question="Are you asking a fitness question or want a workout?",
            options=["Ask a question", "Build a workout"],
        ),
    )
    coach_decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="coach")

    call_count = 0
    router_inputs: list[Any] = []

    class _TurnAwareModel:
        def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs):
            from langchain_core.runnables import RunnableLambda

            nonlocal call_count

            if schema is not RoutingDecision:
                try:
                    instance = schema()
                except Exception:
                    instance = None
                if include_raw:
                    return RunnableLambda(
                        lambda _: {"raw": AIMessage(content=""), "parsed": instance, "parsing_error": None}
                    )
                return RunnableLambda(lambda _: instance)

            call_count += 1
            decision = clarify_decision if call_count <= 1 else coach_decision

            def _invoke(input_val):
                router_inputs.append(input_val)
                return {"raw": AIMessage(content=""), "parsed": decision, "parsing_error": None}

            return RunnableLambda(_invoke)

        async def ainvoke(self, messages, **kwargs):
            return AIMessage(content="Good answer!")

        async def _astream(self, messages, **kwargs):
            from langchain_core.messages import AIMessageChunk

            yield AIMessageChunk(content="Good answer!")

        def bind_tools(self, tools, **kwargs):
            return self

    spy = _TurnAwareModel()
    monkeypatch.setattr("app.models.factory.get_model", lambda role: spy)
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: spy)
    try:
        monkeypatch.setattr("app.agents.coach.graph._factory.get_model", lambda role: spy)
    except AttributeError:
        pass

    hub = build_hub()
    session = "router-prior-session"

    # Turn 1 — clarification branch
    await hub.ainvoke(_initial(session, "fitness stuff"), {"configurable": {"thread_id": session}})

    router_inputs.clear()

    # Turn 2 — user answers the clarification
    await hub.ainvoke(
        _initial(session, "I meant a fitness question"),
        {"configurable": {"thread_id": session}},
    )

    assert router_inputs, "Router was not invoked on turn 2"

    turn2_input = router_inputs[-1]
    assert isinstance(turn2_input, list), (
        f"Router invoked with bare string instead of message list: {type(turn2_input)}"
    )
    prior_content = [
        m.content
        for m in turn2_input
        if isinstance(m, HumanMessage) and m.content == "fitness stuff"
    ]
    assert prior_content, (
        "Router turn-2 input does not contain the prior-turn user message ('fitness stuff'). "
        f"Got: {[type(m).__name__ + ': ' + (getattr(m, 'content', '?')[:40]) for m in turn2_input]}"
    )


# ---------------------------------------------------------------------------
# Chunk 6: Generator sees prior workout context ('make it shorter', criterion 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_make_it_shorter_generator_sees_prior_workout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn 1 routes to WORKOUT_GENERATE and produces a canned workout. Turn 2 is
    'make it shorter'. A recording fake patched into the generator model seam
    captures the messages it is invoked with. The test asserts that turn-2's
    generator input contains:
    - The turn-1 HumanMessage content ('build me a leg workout')
    - An AIMessage carrying a workout summary (the boundary must append it on the
      success path so the transcript carries the prior workout)
    """
    from langchain_core.messages import AIMessageChunk

    generate_decision = RoutingDecision(
        route=Route.WORKOUT_GENERATE, confidence=0.95, rationale="workout"
    )

    _WARMUP_ID = "0a4d99cf-5075-468e-9551-b9f8efa267f1"
    _MAIN_ID = "0e3201e9-4394-4902-a717-f4ce544d98de"
    _COOLDOWN_ID = "1965072a-7e34-4d37-98f5-bde8cb6629a4"

    def _search_msg():
        return AIMessage(
            content="",
            tool_calls=[{
                "id": "s1",
                "name": "search_exercises",
                "args": {"muscle_groups": ["quadriceps"], "equipment": []},
                "type": "tool_call",
            }],
        )

    def _build_msg():
        return AIMessage(
            content="",
            tool_calls=[{
                "id": "b1",
                "name": "build_workout",
                "args": {
                    "warmup_ids": [_WARMUP_ID],
                    "main_ids": [_MAIN_ID],
                    "cooldown_ids": [_COOLDOWN_ID],
                    "prescriptions": [
                        {
                            "exercise_id": _WARMUP_ID,
                            "name": "World's Greatest Stretch",
                            "sets": 1,
                            "reps": 5,
                            "rest_seconds": 30,
                        },
                        {
                            "exercise_id": _MAIN_ID,
                            "name": "Push-Up to Knee-Drive",
                            "sets": 3,
                            "reps": 10,
                            "rest_seconds": 60,
                        },
                        {
                            "exercise_id": _COOLDOWN_ID,
                            "name": "Cow Pose",
                            "sets": 1,
                            "duration_seconds": 30,
                            "rest_seconds": 30,
                        },
                    ],
                },
                "type": "tool_call",
            }],
        )

    generator_model_inputs: list[list[BaseMessage]] = []

    class _RouterModel:
        """Always routes to WORKOUT_GENERATE."""

        def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs):
            from langchain_core.runnables import RunnableLambda

            if schema is not RoutingDecision:
                try:
                    instance = schema()
                except Exception:
                    instance = None
                if include_raw:
                    return RunnableLambda(
                        lambda _: {"raw": AIMessage(content=""), "parsed": instance, "parsing_error": None}
                    )
                return RunnableLambda(lambda _: instance)

            return RunnableLambda(
                lambda _: {"raw": AIMessage(content=""), "parsed": generate_decision, "parsing_error": None}
            )

        async def ainvoke(self, messages, **kwargs):
            return AIMessage(content="Router answer")

        async def _astream(self, messages, **kwargs):
            yield AIMessageChunk(content="Router answer")

        def bind_tools(self, tools, **kwargs):
            return self

    class _GeneratorRecordingModel:
        """Records the messages it receives and returns canned tool calls."""

        def __init__(self):
            self._responses = [_search_msg(), _build_msg()]
            self._idx = 0

        async def ainvoke(self, messages, **kwargs):
            generator_model_inputs.append(list(messages))
            if self._idx < len(self._responses):
                resp = self._responses[self._idx]
                self._idx += 1
                return resp
            return AIMessage(content="done")

        def bind_tools(self, tools, **kwargs):
            return self

        async def _astream(self, messages, **kwargs):
            yield AIMessageChunk(content="")

    router_model = _RouterModel()
    monkeypatch.setattr("app.graph.hub.get_model", lambda role: router_model)
    monkeypatch.setattr("app.models.factory.get_model", lambda role: router_model)

    # Each call to get_model in the generator gets a fresh recording model.
    gen_models = [_GeneratorRecordingModel(), _GeneratorRecordingModel()]
    gen_iter = iter(gen_models)
    monkeypatch.setattr(
        "app.agents.generator.graph._factory.get_model",
        lambda role: next(gen_iter),
    )

    hub = build_hub()
    session = "make-shorter-session"

    # Turn 1: generate a workout
    result1 = await hub.ainvoke(
        _initial(session, "build me a leg workout"),
        {"configurable": {"thread_id": session}},
    )

    # The boundary must append a workout-summary AIMessage so the transcript
    # carries the prior workout for 'make it shorter'.
    msgs_after_t1 = result1["messages"]
    ai_msgs_t1 = [m for m in msgs_after_t1 if isinstance(m, AIMessage)]
    assert ai_msgs_t1, (
        "Expected an AIMessage summarizing the workout in messages after turn 1. "
        "The generator boundary must append a compact workout summary on the success path."
    )

    # Turn 2: 'make it shorter'
    generator_model_inputs.clear()
    await hub.ainvoke(
        _initial(session, "make it shorter"),
        {"configurable": {"thread_id": session}},
    )

    assert generator_model_inputs, "Generator model was not invoked on turn 2"

    all_turn2_messages = [m for msgs in generator_model_inputs for m in msgs]

    prior_human = [
        m
        for m in all_turn2_messages
        if isinstance(m, HumanMessage) and m.content == "build me a leg workout"
    ]
    assert prior_human, (
        "Turn-2 generator input does not contain the turn-1 HumanMessage ('build me a leg workout'). "
        "The generator boundary must forward prior history so 'make it shorter' can adjust."
    )

    prior_ai_summary = [m for m in all_turn2_messages if isinstance(m, AIMessage)]
    assert prior_ai_summary, (
        "Turn-2 generator input contains no AIMessage carrying the prior workout summary. "
        "The boundary success path must append a compact workout-summary AIMessage."
    )


# ---------------------------------------------------------------------------
# Session isolation (two threads do not leak into each other)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_remain_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two distinct thread_ids do not share messages after the context-threading changes."""
    coach_decision = RoutingDecision(route=Route.COACH, confidence=0.9, rationale="coach")
    _install_fake(monkeypatch, decision=coach_decision, text="Session answer")

    hub = build_hub()

    result_a = await hub.ainvoke(
        _initial("iso-a", "Hello from session A"),
        {"configurable": {"thread_id": "iso-a"}},
    )
    result_b = await hub.ainvoke(
        _initial("iso-b", "Hello from session B"),
        {"configurable": {"thread_id": "iso-b"}},
    )

    msgs_a = result_a["messages"]
    msgs_b = result_b["messages"]

    assert not any(
        isinstance(m, HumanMessage) and m.content == "Hello from session A"
        for m in msgs_b
    ), "Session B contains session A's message — sessions are not isolated"

    assert not any(
        isinstance(m, HumanMessage) and m.content == "Hello from session B"
        for m in msgs_a
    ), "Session A contains session B's message — sessions are not isolated"


# ---------------------------------------------------------------------------
# Generator ignores empty prior messages (single-turn path unchanged)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_subgraph_ignores_empty_prior_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """The generator subgraph invoked with messages absent behaves identically to
    the prior single-turn path — seeds [System, Human(user_message)] only, with
    no prior context injected.
    """
    from langchain_core.messages import SystemMessage

    from app.agents.generator.graph import build_generator_subgraph

    _WARMUP_ID = "0a4d99cf-5075-468e-9551-b9f8efa267f1"
    _MAIN_ID = "0e3201e9-4394-4902-a717-f4ce544d98de"
    _COOLDOWN_ID = "1965072a-7e34-4d37-98f5-bde8cb6629a4"

    def _search_msg():
        return AIMessage(
            content="",
            tool_calls=[{
                "id": "s1",
                "name": "search_exercises",
                "args": {"muscle_groups": ["chest"], "equipment": []},
                "type": "tool_call",
            }],
        )

    def _build_msg():
        return AIMessage(
            content="",
            tool_calls=[{
                "id": "b1",
                "name": "build_workout",
                "args": {
                    "warmup_ids": [_WARMUP_ID],
                    "main_ids": [_MAIN_ID],
                    "cooldown_ids": [_COOLDOWN_ID],
                    "prescriptions": [
                        {
                            "exercise_id": _WARMUP_ID,
                            "name": "World's Greatest Stretch",
                            "sets": 1,
                            "reps": 5,
                            "rest_seconds": 30,
                        },
                        {
                            "exercise_id": _MAIN_ID,
                            "name": "Push-Up to Knee-Drive",
                            "sets": 3,
                            "reps": 10,
                            "rest_seconds": 60,
                        },
                        {
                            "exercise_id": _COOLDOWN_ID,
                            "name": "Cow Pose",
                            "sets": 1,
                            "duration_seconds": 30,
                            "rest_seconds": 30,
                        },
                    ],
                },
                "type": "tool_call",
            }],
        )

    captured: list[list[BaseMessage]] = []
    responses = [_search_msg(), _build_msg()]
    idx = 0

    class _RecordingModel:
        async def ainvoke(self, messages, **kwargs):
            nonlocal idx
            captured.append(list(messages))
            resp = responses[idx] if idx < len(responses) else AIMessage(content="done")
            idx += 1
            return resp

        def bind_tools(self, tools, **kwargs):
            return self

    monkeypatch.setattr(
        "app.agents.generator.graph._factory.get_model",
        lambda role: _RecordingModel(),
    )

    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    # Call with messages absent (single-turn path, no prior context key)
    await generator.ainvoke({
        "user_message": "Give me a chest workout",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    assert captured, "Generator model was not invoked"
    first_call = captured[0]
    assert isinstance(first_call[0], SystemMessage), (
        f"First message must be SystemMessage, got {type(first_call[0])}"
    )
    assert isinstance(first_call[-1], HumanMessage), (
        f"Last message must be HumanMessage, got {type(first_call[-1])}"
    )
    assert first_call[-1].content == "Give me a chest workout"
    # With no prior context the generate node seeds exactly [System, Human]
    assert len(first_call) == 2, (
        f"With empty prior context, generator should get [System, Human] (2 messages), "
        f"got {len(first_call)}"
    )
