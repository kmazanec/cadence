"""Critical-path test: injury-driven hard exclusion.

Rationale (ADR-018 #2 — injury safety):
A workout assembled with injuries must NEVER contain an exercise that loads an
injured joint. This is a hard invariant, not a preference: presenting a
knee-loading exercise to a user with a knee injury could cause physical harm.

The test runs the full generator subgraph with a deterministic fake model that
deliberately tries to include a knee-loading exercise. Both the search pre-filter
(dropping contraindicated candidates before the model sees them) and the output
gate (defense-in-depth: rejecting a contraindicated ID even if it somehow reached
build_workout) are exercised end-to-end.

The fake follows the schema-aware _SequentialFakeModel pattern from
test_generator_subgraph.py — reusing the shared get_model seam rather than
introducing a per-feature fake, per ADR-018 lesson.

This test is designated critical path because its failure represents a safety
regression, not merely a behavior regression.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agents.generator.graph import build_generator_subgraph
from app.agents.generator.schemas import WorkoutPayload
from app.data.json_repository import JsonExerciseRepository

# ---------------------------------------------------------------------------
# Fixture exercises
# ---------------------------------------------------------------------------

# One knee-loading exercise the fake model will attempt to include.
_KNEE_LOADING_ID = "00036a08-7c22-42e4-8fe5-323b53e31667"  # Kettlebell Goblet Cyclist Squat

# Safe (non-knee) exercises used to pad the canned build call so it looks like
# a real workout. These load shoulder/elbow/wrist only.
_SAFE_WARMUP = "0e3201e9-4394-4902-a717-f4ce544d98de"   # Push-Up to Knee-Drive
_SAFE_COOLDOWN = "0a2dc786-fb42-4571-9b26-f58cdeb2c70e"  # Bodyweight Pike


def _canned_search_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "search-knee-test",
            "name": "search_exercises",
            "args": {"muscle_groups": ["quads"]},
            "type": "tool_call",
        }],
    )


def _canned_build_with_knee_id() -> AIMessage:
    """Fake model attempts to include a knee-loading exercise in the workout.

    The gate must reject this and prevent it from reaching the user.
    """
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "build-knee-test",
            "name": "build_workout",
            "args": {
                "warmup_ids": [_SAFE_WARMUP],
                "main_ids": [_KNEE_LOADING_ID],
                "cooldown_ids": [_SAFE_COOLDOWN],
                "prescriptions": [
                    {
                        "exercise_id": _SAFE_WARMUP,
                        "name": "Push-Up to Knee-Drive",
                        "sets": 2,
                        "reps": 10,
                        "rest_seconds": 30,
                    },
                    {
                        "exercise_id": _KNEE_LOADING_ID,
                        "name": "Kettlebell Goblet Cyclist Squat",
                        "sets": 3,
                        "reps": 10,
                        "rest_seconds": 60,
                    },
                    {
                        "exercise_id": _SAFE_COOLDOWN,
                        "name": "Bodyweight Pike",
                        "sets": 1,
                        "duration_seconds": 30,
                        "rest_seconds": 30,
                    },
                ],
            },
            "type": "tool_call",
        }],
    )


class _SequentialFakeModel(GenericFakeChatModel):
    """Returns canned messages in sequence; schema-aware bind_tools no-op."""

    def __init__(self, responses: list[AIMessage]) -> None:
        super().__init__(messages=iter([]))
        self._responses = iter(responses)

    def invoke(self, *args, **kwargs):
        return next(self._responses)

    async def ainvoke(self, *args, **kwargs):
        return next(self._responses)

    def bind_tools(self, tools, **kwargs):
        return self


# ---------------------------------------------------------------------------
# Critical-path safety test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_knee_injury_yields_zero_knee_loading_exercises(monkeypatch) -> None:
    """End-to-end safety invariant: injuries=['knee'] produces a workout with
    zero exercises whose joints_loaded includes 'knee'.

    The fake model deliberately tries to place a knee-loading exercise in the
    main block. Both the search pre-filter (dropping contraindicated IDs from
    results before the model ever sees them) and the output gate
    (defense-in-depth) must prevent it from appearing in the final workout.

    If this test goes red, it means a knee-loading exercise can reach the user
    despite a stated knee injury — a safety regression.
    """
    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _SequentialFakeModel([
            _canned_search_call(),
            _canned_build_with_knee_id(),
        ]),
    )

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Give me a lower body workout, I have a knee injury",
        "injuries": ["knee"],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    # The workout may be None (gate rejected + retries exhausted) or a valid
    # payload. In either case, zero knee-loading exercises must be present.
    workout: WorkoutPayload | None = result.get("workout")
    if workout is not None:
        repo_check = JsonExerciseRepository()
        for block in workout.blocks:
            for p in block.exercises:
                ex = repo_check.get_by_id(p.exercise_id)
                assert ex is not None, f"Unknown exercise_id {p.exercise_id!r} in result"
                knee_loaded = any(j.casefold() == "knee" for j in ex.joints_loaded)
                assert not knee_loaded, (
                    f"Knee-loading exercise {ex.name!r} ({ex.id}) reached the "
                    f"workout despite injuries=['knee']. joints_loaded={ex.joints_loaded}"
                )
