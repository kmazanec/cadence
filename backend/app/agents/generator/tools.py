"""Field-described input schemas for the generator's tools.

The field descriptions are part of the contract: they are what the model reads
to call the tools correctly. ``WorkoutPayload`` and its parts are re-exported
here so the generator's structured shapes live behind one import.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .schemas import Block, BlockName, Prescription, WorkoutPayload

__all__ = [
    "SearchExercisesInput",
    "BuildWorkoutInput",
    "WorkoutPayload",
    "Block",
    "BlockName",
    "Prescription",
]


class SearchExercisesInput(BaseModel):
    """Arguments for searching the exercise catalogue."""

    muscle_groups: list[str] | None = Field(
        None,
        description="Muscle groups to target, e.g. ['chest', 'triceps']. Omit to not filter by muscle.",
    )
    equipment: list[str] | None = Field(
        None,
        description="Equipment the user has available, e.g. ['Dumbbell']. Omit to not filter by equipment.",
    )
    movement_patterns: list[str] | None = Field(
        None,
        description="Movement patterns to include, e.g. ['upper push - horizontal']. Omit to not filter by pattern.",
    )


class BuildWorkoutInput(BaseModel):
    """Arguments for assembling the final workout from chosen exercises."""

    warmup_ids: list[str] = Field(
        description="Exercise ids to place in the warmup block, in order.",
    )
    main_ids: list[str] = Field(
        description="Exercise ids to place in the main block, in order.",
    )
    cooldown_ids: list[str] = Field(
        description="Exercise ids to place in the cooldown block, in order.",
    )
    prescriptions: list[Prescription] = Field(
        description="Per-exercise prescription (sets, reps or duration, rest, optional weight) for every id used.",
    )
