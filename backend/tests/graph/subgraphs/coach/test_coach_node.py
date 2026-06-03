"""Tests for the coach subgraph node wiring, adapter, and voice-prompt application.

Why: Prove deterministically (no network) that the coach subgraph's wiring
correctly invokes the model, the boundary adapter maps answers onto HubState,
the BRAND.md voice directive is present in the system prompt, and the hub
composes the coach via its unique node name without a MULTIPLE_SUBGRAPHS error.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, SystemMessage

from app.agents.coach.graph import COACH_SYSTEM_PROMPT, build_coach_subgraph
from app.agents.coach.state import CoachState
from app.graph.hub import build_hub
from app.graph.routing import Route
from app.graph.state import CoachResult, HubState


# ---------------------------------------------------------------------------
# Test 1: invoking the compiled subgraph with a fake model returns an answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coach_subgraph_returns_canned_answer(fake_get_model) -> None:
    """The compiled coach subgraph with a fake model yields a non-empty answer."""
    canned = "Deadlifts primarily work the hamstrings, glutes, and lower back."
    fake_get_model(canned)

    coach = build_coach_subgraph()
    initial: CoachState = {
        "user_message": "What muscles does a deadlift work?",
        "messages": [],
        "answer": "",
    }
    result = await coach.ainvoke(initial)
    assert result["answer"] == canned


# ---------------------------------------------------------------------------
# Test 2: the system prompt contains the BRAND.md voice directives
# ---------------------------------------------------------------------------


def test_coach_system_prompt_contains_brand_voice_directives() -> None:
    """The coach system prompt applies BRAND.md voice: conversational, direct,
    confident, partnership-oriented, and never clinical/robotic."""
    prompt_lower = COACH_SYSTEM_PROMPT.lower()

    # Voice must be conversational and direct — not clinical or robotic.
    assert any(kw in prompt_lower for kw in ("conversational", "direct", "training partner")), (
        "System prompt lacks a conversational/direct/training-partner directive"
    )
    # Partnership voice: 'let's', 'we', or partnership-oriented phrasing.
    assert any(kw in prompt_lower for kw in ("partner", "we", "let's", "together")), (
        "System prompt lacks a partnership-voice directive"
    )
    # Must not encourage clinical, hedged, or robotic output.
    assert any(kw in prompt_lower for kw in ("clinical", "robotic", "hedged", "disclaimers")), (
        "System prompt does not caution against clinical/robotic tone"
    )


# ---------------------------------------------------------------------------
# Test 3: hub composition reaches the coach via its unique node name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_composes_coach_via_unique_node_name(fake_get_model) -> None:
    """The hub wires the coach under a unique node name; no MULTIPLE_SUBGRAPHS."""
    graph = build_hub()
    node_names = list(graph.nodes.keys())
    assert any("coach" in name for name in node_names), (
        f"Expected a coach-related node in the hub; found: {node_names}"
    )

    # End-to-end invocation must succeed without any graph-composition error.
    config = {"configurable": {"thread_id": "coach-node-test-1"}}
    initial: HubState = {
        "session_id": "coach-node-test-1",
        "messages": [],
        "user_message": "What muscles does a deadlift work?",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    final = await graph.ainvoke(initial, config)
    assert final["route"] == Route.COACH
    assert isinstance(final["subgraph_result"], CoachResult)
    assert len(final["subgraph_result"].answer) > 0
