"""Tests for general-conversation handling and the explanation note emitted by
the coach boundary.

Why: Prove that the coach gracefully handles any message (not just knowledge
questions), that the hub's coach boundary populates HubState.explanation with
exactly one {claim:'note'} Reason from the frozen vocab, and that the coach's
answer reaches the SSE token stream end-to-end through the hub. An opt-in live
smoke test verifies real-model relevance when an API key is available.
"""

from __future__ import annotations

import os

import pytest
from langchain_core.messages import AIMessageChunk

from app.api.streaming import DoneEvent, RouteEvent, TokenEvent, encode_sse
from app.graph.explanation import Reason
from app.graph.hub import build_hub
from app.graph.routing import Route
from app.graph.state import CoachResult, HubState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_state(message: str, session_id: str = "coach-conv-test") -> HubState:
    return {
        "session_id": session_id,
        "messages": [],
        "user_message": message,
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Test 1: general chat message returns a non-empty graceful answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coach_handles_general_conversation(fake_get_model) -> None:
    """A general-chat message (not a knowledge question, not generate/log)
    through the coach with a fake model returns a non-empty graceful answer."""
    fake_get_model("Hey there! That's a great question. Let's work on that together.")

    graph = build_hub()
    config = {"configurable": {"thread_id": "coach-general-1"}}
    final = await graph.ainvoke(_base_state("How's your day?"), config)

    assert isinstance(final["subgraph_result"], CoachResult)
    assert len(final["subgraph_result"].answer) > 0


# ---------------------------------------------------------------------------
# Test 2: HubState.explanation carries exactly one {claim:'note'} Reason
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coach_emits_exactly_one_note_reason(fake_get_model) -> None:
    """After the coach node, HubState.explanation contains exactly one Reason
    with claim=='note' drawn from the frozen relation vocabulary."""
    fake_get_model("Great question! Your glutes, hamstrings, and lower back will feel it.")

    graph = build_hub()
    config = {"configurable": {"thread_id": "coach-note-reason-1"}}
    final = await graph.ainvoke(
        _base_state("What muscles does a deadlift work?", "coach-note-reason-1"),
        config,
    )

    explanation: list[Reason] = final.get("explanation", [])
    note_reasons = [r for r in explanation if r.claim == "note"]
    assert len(note_reasons) == 1, (
        f"Expected exactly 1 note Reason; got {len(note_reasons)}: {explanation}"
    )
    # The relation must be from the frozen vocab.
    from app.graph.explanation import Relation
    import typing
    frozen_relations = set(typing.get_args(Relation))
    assert note_reasons[0].relation in frozen_relations, (
        f"note Reason carries an out-of-vocab relation: {note_reasons[0].relation!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: coach text reaches the SSE token stream end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coach_answer_reaches_sse_token_stream(fake_get_model) -> None:
    """Streaming the hub with the fake coach model emits at least one token
    event carrying coach text, proving AC-4 (readable text reaches the stream)."""
    fake_get_model("Deadlifts work your hamstrings, glutes, and lower back. Let's do it!")

    graph = build_hub()
    config = {"configurable": {"thread_id": "coach-sse-1"}}
    initial = _base_state("What muscles does a deadlift work?", "coach-sse-1")

    token_texts: list[str] = []
    async for ns_chunk in graph.astream(
        initial, config, stream_mode="messages", subgraphs=True
    ):
        _ns, (msg, _meta) = ns_chunk
        if isinstance(msg, AIMessageChunk) and msg.content:
            token_texts.append(str(msg.content))

    combined = "".join(token_texts)
    assert combined, "No token text streamed from the coach through the hub"

    # The SSE encode path must serialise a token event without error.
    sample_event = TokenEvent(text=token_texts[0] if token_texts else "hi")
    frame = encode_sse(sample_event)
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")


# ---------------------------------------------------------------------------
# Opt-in live smoke test: real model produces a relevant deadlift answer
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set — skipping live smoke test",
)
@pytest.mark.asyncio
async def test_live_deadlift_answer_mentions_relevant_muscle() -> None:
    """A real model should mention at least one primary deadlift muscle.

    Skipped in CI; run manually with OPENROUTER_API_KEY set to confirm AC-1
    real-model relevance.
    """
    from app.agents.coach.graph import build_coach_subgraph
    from app.agents.coach.state import CoachState

    coach = build_coach_subgraph()
    initial: CoachState = {
        "user_message": "What muscles does a deadlift work?",
        "messages": [],
        "answer": "",
    }
    result = await coach.ainvoke(initial)
    answer_lower = result["answer"].lower()
    primary_muscles = {"hamstring", "glute", "lower back", "erector", "trap", "lat"}
    assert any(m in answer_lower for m in primary_muscles), (
        f"Live answer did not mention a primary deadlift muscle: {result['answer']!r}"
    )
