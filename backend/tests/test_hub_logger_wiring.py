"""Tests that verify the hub dispatches WORKOUT_LOG to the logger boundary.

These tests confirm the hub's route edge correctly sends WORKOUT_LOG turns to
the logger boundary node, and that the assembled response contains a LogPayload.
"""

from __future__ import annotations

import pytest

from app.graph.hub import build_hub
from app.graph.routing import Route
from app.api.schemas import LogPayload


@pytest.mark.asyncio
async def test_workout_log_route_dispatches_to_logger(
    tmp_path, fake_get_model, monkeypatch
) -> None:
    """When route=WORKOUT_LOG, the hub produces a WorkoutLogResult in state."""
    from app.agents.logger import graph as logger_graph
    from app.agents.logger.graph import ParsedEntry
    from app.data.sqlite_log_repository import SqliteLogRepository
    from app.graph import hub as hub_module

    # Stub both LLM-driven steps.
    async def _fake_extract(user_message: str, model) -> list[ParsedEntry]:
        return [ParsedEntry(raw_name="bench press", sets=3, reps=10, weight=185.0)]

    monkeypatch.setattr(logger_graph, "_extract_entries", _fake_extract)

    # Inject an in-memory SQLite repo for the hub logger boundary.
    sqlite = SqliteLogRepository(tmp_path / "hub_test.db")
    monkeypatch.setattr(hub_module, "_get_log_repository_for_hub", lambda: sqlite)

    # Force the router to commit WORKOUT_LOG.
    from app.graph.routing import RoutingDecision, CONFIDENCE_THRESHOLD

    async def _fake_router(state) -> dict:
        decision = RoutingDecision(
            route=Route.WORKOUT_LOG,
            confidence=CONFIDENCE_THRESHOLD + 0.1,
            rationale="test stub",
        )
        from langchain_core.messages import HumanMessage
        return {
            "route": decision.route,
            "routing_confidence": decision.confidence,
            "routing_raw": decision.model_dump(),
            "messages": [HumanMessage(content=state["user_message"])],
        }

    monkeypatch.setattr(hub_module, "_router_node", _fake_router)

    hub = build_hub()
    session_id = "hub-test-session"
    initial_state = {
        "session_id": session_id,
        "user_message": "I just did 3x10 bench press at 185 lbs",
        "messages": [],
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    config = {"configurable": {"thread_id": session_id}}
    final_state = await hub.ainvoke(initial_state, config=config)

    from app.graph.state import WorkoutLogResult
    result = final_state.get("subgraph_result")
    assert isinstance(result, WorkoutLogResult), (
        f"Expected WorkoutLogResult, got {type(result)}"
    )
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.unmatched is False
    assert entry.exercise_id is not None


@pytest.mark.asyncio
async def test_assemble_response_log_route(tmp_path, fake_get_model, monkeypatch) -> None:
    """assemble_response produces a LogPayload when subgraph_result is WorkoutLogResult."""
    from datetime import datetime, timezone
    from app.data.log_repository import LogEntry
    from app.graph.state import WorkoutLogResult
    from app.graph.response_assembly import assemble_response

    entry = LogEntry(
        session_id="s1",
        exercise_id="some-id",
        raw_name="bench press",
        sets=3,
        reps=10,
        weight=185.0,
        unmatched=False,
        logged_at=datetime.now(timezone.utc),
    )
    state = {
        "session_id": "s1",
        "messages": [],
        "user_message": "I did bench press",
        "route": Route.WORKOUT_LOG,
        "routing_confidence": 0.9,
        "routing_raw": None,
        "subgraph_result": WorkoutLogResult(entries=[entry], session_id="s1"),
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    response = assemble_response(state)
    assert isinstance(response.structured, LogPayload)
    assert response.structured.entries[0].raw_name == "bench press"
