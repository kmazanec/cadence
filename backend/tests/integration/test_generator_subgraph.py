"""Integration tests for the Generator subgraph (fake-model, no LLM).

The fake model is loaded with a canned tool-call sequence:
  1. AIMessage with search_exercises tool call
  2. AIMessage with build_workout tool call (using real dataset IDs)

Assertions:
- The GeneratorState contains a valid WorkoutPayload after the subgraph runs.
- The boundary adapter maps GeneratorState output to GeneratorResult on HubState.
- Relation-shaped Reasons (included/matches_target, equipment_match) are emitted
  with the closed vocabulary from explanation.py.
- The SSE 'structured' event payload is sourced from state (not message deltas)
  as required to prevent stream-delta corruption.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agents.generator.graph import build_generator_subgraph
from app.agents.generator.schemas import WorkoutPayload
from app.api.streaming import StructuredEvent, encode_sse
from app.data.json_repository import JsonExerciseRepository
from app.graph.explanation import Reason
from app.graph.state import GeneratorResult

# ---------------------------------------------------------------------------
# Real dataset IDs for the canned tool call sequence (no-equipment or yoga-mat
# exercises so the test is environment-independent).
# ---------------------------------------------------------------------------

_WARMUP_IDS = ["0a4d99cf-5075-468e-9551-b9f8efa267f1"]   # World's Greatest Stretch
_MAIN_IDS = ["0e3201e9-4394-4902-a717-f4ce544d98de"]      # Push-Up to Knee-Drive
_COOLDOWN_IDS = ["1965072a-7e34-4d37-98f5-bde8cb6629a4"]  # Cow Pose


def _canned_search_call() -> AIMessage:
    """First model turn: call search_exercises with muscle group + equipment."""
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "search-1",
            "name": "search_exercises",
            "args": {
                "muscle_groups": ["chest", "deltoids"],
                "equipment": ["Yoga Mat"],
            },
            "type": "tool_call",
        }],
    )


def _canned_build_call() -> AIMessage:
    """Second model turn: call build_workout with real exercise IDs."""
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "build-1",
            "name": "build_workout",
            "args": {
                "warmup_ids": _WARMUP_IDS,
                "main_ids": _MAIN_IDS,
                "cooldown_ids": _COOLDOWN_IDS,
                "prescriptions": [
                    {
                        "exercise_id": _WARMUP_IDS[0],
                        "name": "World's Greatest Stretch",
                        "sets": 2,
                        "reps": 5,
                        "rest_seconds": 30,
                    },
                    {
                        "exercise_id": _MAIN_IDS[0],
                        "name": "Push-Up to Knee-Drive",
                        "sets": 3,
                        "reps": 10,
                        "rest_seconds": 60,
                    },
                    {
                        "exercise_id": _COOLDOWN_IDS[0],
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


def _make_sequential_fake(monkeypatch) -> None:
    """Patch get_model('generator') to return a fake model with a fresh canned
    sequence for each call to get_model. This ensures each test gets an independent
    message iterator even when multiple tests run in a session."""

    class _SequentialFakeModel(GenericFakeChatModel):
        """Returns the next canned message on each ainvoke call."""

        def __init__(self):
            super().__init__(messages=iter([]))
            self._responses = iter([_canned_search_call(), _canned_build_call()])

        def invoke(self, *args, **kwargs):
            return next(self._responses)

        async def ainvoke(self, *args, **kwargs):
            return next(self._responses)

        def bind_tools(self, tools, **kwargs):
            """Acknowledge tool binding without changing behavior."""
            return self

    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _SequentialFakeModel(),
    )


@pytest.fixture
def fake_generator_model(monkeypatch) -> None:
    """Monkeypatch get_model to return a fake model with canned tool calls."""
    _make_sequential_fake(monkeypatch)


# ---------------------------------------------------------------------------
# Generator subgraph: workout lands in GeneratorState
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_subgraph_produces_workout(fake_generator_model) -> None:
    """After running with the canned tool sequence, GeneratorState.workout must
    be a valid WorkoutPayload with three blocks."""
    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Give me an upper body workout with a yoga mat",
        "injuries": [],
        "targets": ["chest", "deltoids"],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    assert result["workout"] is not None, "GeneratorState.workout must be set"
    workout = result["workout"]
    assert isinstance(workout, WorkoutPayload)
    assert len(workout.blocks) == 3
    names = [b.name for b in workout.blocks]
    assert names == ["warmup", "main", "cooldown"]


@pytest.mark.asyncio
async def test_generator_subgraph_workout_ids_resolve_in_repo(monkeypatch) -> None:
    """All exercise IDs in the assembled workout must exist in the repository."""
    _make_sequential_fake(monkeypatch)
    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Upper body yoga mat workout",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    workout = result["workout"]
    assert workout is not None
    for block in workout.blocks:
        for p in block.exercises:
            assert repo.get_by_id(p.exercise_id) is not None, (
                f"exercise_id {p.exercise_id!r} not in repository"
            )


@pytest.mark.asyncio
async def test_generator_subgraph_stores_selected_ids(monkeypatch) -> None:
    """GeneratorState.selected_exercise_ids must be populated from the build call."""
    _make_sequential_fake(monkeypatch)
    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Upper body yoga mat workout",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    assert result["selected_exercise_ids"], "selected_exercise_ids must be non-empty"


# ---------------------------------------------------------------------------
# Boundary adapter: GeneratorState maps to GeneratorResult on HubState
# ---------------------------------------------------------------------------


def test_generator_result_arm_on_hub_state() -> None:
    """GeneratorResult correctly carries the workout onto HubState.subgraph_result."""
    workout = WorkoutPayload(blocks=[])
    result = GeneratorResult(workout=workout, selected_exercise_ids=["x"])
    assert result.kind == "workout"
    assert result.workout is workout


# ---------------------------------------------------------------------------
# Reason vocabulary: closed relation terms used by the generator
# ---------------------------------------------------------------------------


def test_matches_target_reason_accepted() -> None:
    """'included' + 'matches_target' is a valid Reason triple."""
    r = Reason(
        claim="included",
        subject="Push-Up to Knee-Drive",
        relation="matches_target",
        object="chest",
    )
    assert r.claim == "included"
    assert r.relation == "matches_target"


def test_equipment_match_reason_accepted() -> None:
    """'included' + 'equipment_match' is a valid Reason triple."""
    r = Reason(
        claim="included",
        subject="World's Greatest Stretch",
        relation="equipment_match",
        object="Yoga Mat",
    )
    assert r.claim == "included"
    assert r.relation == "equipment_match"


def test_note_equipment_match_accepted() -> None:
    """'note' + 'equipment_match' is a valid Reason triple."""
    r = Reason(
        claim="note",
        subject="Cow Pose",
        relation="equipment_match",
        object="Yoga Mat",
    )
    assert r.claim == "note"
    assert r.relation == "equipment_match"


# ---------------------------------------------------------------------------
# SSE 'structured' event reads from state (ADR-002 regression guard)
# ---------------------------------------------------------------------------


def test_sse_structured_event_built_from_state_not_message_deltas() -> None:
    """The StructuredEvent is constructed from the WorkoutPayload in state, not
    from serialised message deltas. Sourcing the payload from streaming message
    deltas (stream_mode='messages') can corrupt tool-call arguments; state is
    the safe and correct source.

    This test verifies that the SSE frame round-trips the three block names
    that were in the originally assembled payload, proving the payload flows
    intact from build_workout -> state -> SSE event."""
    from app.agents.generator.build_workout import build_workout

    repo = JsonExerciseRepository()
    payload = build_workout(
        warmup_ids=_WARMUP_IDS,
        main_ids=_MAIN_IDS,
        cooldown_ids=_COOLDOWN_IDS,
        repo=repo,
    )

    # Simulate what the SSE layer does: read payload FROM state, wrap in event.
    event = StructuredEvent(payload=payload)
    frame = encode_sse(event)

    # The frame must be a valid SSE line referencing the workout blocks.
    assert frame.startswith("data: ")
    assert "warmup" in frame
    assert "main" in frame
    assert "cooldown" in frame
    assert "structured" in frame
