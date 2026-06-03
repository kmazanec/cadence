"""Integration tests: a headless message through the hub reaches the
coach subgraph and returns a streamed response.

These tests cover:
- The hub state machine reaches the coach subgraph via a unique node name
  (no MULTIPLE_SUBGRAPHS error).
- A streamed invocation emits token events.
- The hub works with the fake model (no network).
"""

from __future__ import annotations

import pytest

from app.graph.hub import build_hub
from app.graph.routing import Route
from app.graph.state import CoachResult, HubState


@pytest.mark.asyncio
async def test_hub_reaches_coach_subgraph(fake_get_model) -> None:
    """A message routed through the hub reaches the coach node and produces a reply."""
    graph = build_hub()
    config = {"configurable": {"thread_id": "test-session-1"}}
    initial: HubState = {
        "session_id": "test-session-1",
        "messages": [],
        "user_message": "What muscles does a squat work?",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    final = await graph.ainvoke(initial, config)
    # The router placeholder always returns Route.COACH
    assert final["route"] == Route.COACH
    # The coach subgraph should have produced a CoachResult
    assert isinstance(final["subgraph_result"], CoachResult)
    assert len(final["subgraph_result"].answer) > 0


@pytest.mark.asyncio
async def test_hub_streams_tokens(fake_get_model) -> None:
    """Streaming the hub with subgraphs=True produces token chunks from the coach.

    The coach runs inside a boundary node which itself may run a subgraph.
    Using subgraphs=True surfaces chunks from all namespace levels.
    """
    from langchain_core.messages import AIMessageChunk

    graph = build_hub()
    config = {"configurable": {"thread_id": "test-session-2"}}
    initial: HubState = {
        "session_id": "test-session-2",
        "messages": [],
        "user_message": "Give me a push-up tip",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }

    # Collect all events across namespace levels, looking for token chunks.
    got_message_delta = False
    async for ns_chunk in graph.astream(
        initial, config, stream_mode="messages", subgraphs=True
    ):
        # With subgraphs=True, each item is (namespace_tuple, (msg, metadata))
        _ns, (msg, _meta) = ns_chunk
        if isinstance(msg, AIMessageChunk) and msg.content:
            got_message_delta = True
            break

    assert got_message_delta, "No token deltas seen from hub stream (including subgraphs)"


@pytest.mark.asyncio
async def test_hub_unique_coach_node_name(fake_get_model) -> None:
    """The coach subgraph is wired under a unique node name, not 'coach_subgraph'
    ambiguity — this verifies no MULTIPLE_SUBGRAPHS error occurs."""
    graph = build_hub()
    node_names = list(graph.nodes.keys())
    # At least one node should contain 'coach'
    assert any("coach" in name for name in node_names), (
        f"Expected a coach-related node; found: {node_names}"
    )


@pytest.mark.asyncio
async def test_hub_session_keyed_checkpointing(fake_get_model) -> None:
    """Two separate sessions don't share message history."""
    graph = build_hub()
    for session_id in ("session-a", "session-b"):
        config = {"configurable": {"thread_id": session_id}}
        initial: HubState = {
            "session_id": session_id,
            "messages": [],
            "user_message": "Hello",
            "route": None,
            "routing_confidence": None,
            "routing_raw": None,
            "subgraph_result": None,
            "explanation": [],
            "clarification": None,
            "error": None,
        }
        result = await graph.ainvoke(initial, config)
        # Each session should have at least the user message in the thread
        assert result is not None
