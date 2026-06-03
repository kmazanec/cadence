"""Integration test: graceful recovery when injuries exclude most/all candidates.

Acceptance criteria #3: over-exclusion (injuries that block most or all valid
exercises) must yield honest recovery — never padding with contraindicated or
irrelevant exercises, and never crashing.

This test exercises the path where the output gate rejects the assembled workout
(because the fake model includes a contraindicated ID), retries are exhausted,
and the subgraph returns workout=None for graceful recovery.

Ownership: AC #3 is tested here. The output-gate invariant for unknown IDs is
covered in tests/critical/test_output_gate.py (ADR-018 #3).
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agents.generator.graph import build_generator_subgraph
from app.data.json_repository import JsonExerciseRepository

# ---------------------------------------------------------------------------
# Fake model: always tries to build with a contraindicated ID
# ---------------------------------------------------------------------------

# Exercises that load the knee — all will be contraindicated.
_KNEE_ID = "00036a08-7c22-42e4-8fe5-323b53e31667"  # Kettlebell Goblet Cyclist Squat
_KNEE_ID2 = "00cc383b-f156-4b23-952a-15340100c261"  # RNT Split Squat
_KNEE_ID3 = "01ff62bc-e887-49e4-9cc8-bcd367b34cfd"  # Static Jump

# Broader over-exclusion: block hip+knee so very few exercises remain
_OVER_EXCLUDE_INJURIES = ["knee", "hip", "ankle", "shoulder"]


class _AlwaysBuildContraindicated(GenericFakeChatModel):
    """Always calls build_workout with a contraindicated exercise ID."""

    def __init__(self) -> None:
        super().__init__(messages=iter([]))
        self._turn = 0

    def _search_call(self) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[{
                "id": f"s{self._turn}",
                "name": "search_exercises",
                "args": {"muscle_groups": ["quads"]},
                "type": "tool_call",
            }],
        )

    def _build_call(self) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[{
                "id": f"b{self._turn}",
                "name": "build_workout",
                "args": {
                    "warmup_ids": [_KNEE_ID],
                    "main_ids": [_KNEE_ID2],
                    "cooldown_ids": [_KNEE_ID3],
                    "prescriptions": [
                        {"exercise_id": _KNEE_ID, "name": "Ex1", "sets": 2, "reps": 8, "rest_seconds": 30},
                        {"exercise_id": _KNEE_ID2, "name": "Ex2", "sets": 3, "reps": 10, "rest_seconds": 60},
                        {"exercise_id": _KNEE_ID3, "name": "Ex3", "sets": 1, "duration_seconds": 30, "rest_seconds": 30},
                    ],
                },
                "type": "tool_call",
            }],
        )

    def invoke(self, *args, **kwargs):
        msg = self._search_call() if self._turn % 2 == 0 else self._build_call()
        self._turn += 1
        return msg

    async def ainvoke(self, *args, **kwargs):
        return self.invoke()

    def bind_tools(self, tools, **kwargs):
        return self


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_over_exclusion_yields_graceful_recovery(monkeypatch) -> None:
    """With an over-broad injury set, the generator exhausts retries and returns
    workout=None rather than padding with contraindicated exercises.

    This confirms:
    - No contraindicated exercise appears in the final result.
    - The workout is None (graceful honest-gap response), not a fabricated one.
    - The subgraph does not crash or raise.
    """
    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _AlwaysBuildContraindicated(),
    )

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Workout but I have knee, hip, ankle and shoulder injuries",
        "injuries": _OVER_EXCLUDE_INJURIES,
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    workout = result.get("workout")

    # When every attempt is rejected by the gate, workout must be None.
    assert workout is None, (
        f"Expected workout=None after over-exclusion recovery, got: {workout}"
    )


@pytest.mark.asyncio
async def test_over_exclusion_no_contraindicated_exercise_in_result(monkeypatch) -> None:
    """Even if somehow the gate did not fully clear the workout, no contraindicated
    exercise must appear in the final result."""
    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _AlwaysBuildContraindicated(),
    )

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "Workout but I have knee injuries",
        "injuries": ["knee"],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    workout = result.get("workout")
    if workout is not None:
        knee_ids = repo.contraindicated_ids(["knee"])
        for block in workout.blocks:
            for p in block.exercises:
                assert p.exercise_id not in knee_ids, (
                    f"Contraindicated exercise {p.exercise_id!r} appeared in result "
                    f"despite injuries=['knee']"
                )
