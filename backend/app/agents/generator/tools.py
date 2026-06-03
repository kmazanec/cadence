"""Field-described input schemas for the generator's tools.

The field descriptions are part of the contract: they are what the model reads
to call the tools correctly. ``WorkoutPayload`` and its parts are re-exported
here so the generator's structured shapes live behind one import.

``search_exercises_tool`` and ``build_workout_tool`` are the ``StructuredTool``
wrappers that must be bound to the model. Binding the bare Pydantic classes
would produce tool names derived from the class name (e.g. ``SearchExercisesInput``),
which would not match the dispatch keys ``"search_exercises"`` / ``"build_workout"``
used in graph.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from .schemas import Block, BlockName, Prescription, WorkoutPayload

__all__ = [
    "SearchExercisesInput",
    "BuildWorkoutInput",
    "search_exercises_tool",
    "build_workout_tool",
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


# ---------------------------------------------------------------------------
# StructuredTool wrappers — bind these to the model, not the bare schemas.
# LangChain derives a tool's name from the callable/class passed to bind_tools;
# using StructuredTool with an explicit name guarantees the model emits tool
# calls named "search_exercises" / "build_workout", matching the dispatch keys.
# ---------------------------------------------------------------------------

def _noop_search(**kwargs) -> str:  # pragma: no cover
    """Placeholder; the real execution lives in graph._execute_search."""
    return ""


def _noop_build(**kwargs) -> str:  # pragma: no cover
    """Placeholder; the real execution lives in graph._execute_build_workout."""
    return ""


search_exercises_tool: StructuredTool = StructuredTool.from_function(
    func=_noop_search,
    name="search_exercises",
    description="Search the exercise catalogue by muscle groups, equipment, or movement pattern.",
    args_schema=SearchExercisesInput,
)

build_workout_tool: StructuredTool = StructuredTool.from_function(
    func=_noop_build,
    name="build_workout",
    description="Assemble a warmup/main/cooldown workout from the exercise IDs returned by search_exercises.",
    args_schema=BuildWorkoutInput,
)
