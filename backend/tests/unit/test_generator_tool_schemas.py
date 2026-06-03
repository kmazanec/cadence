"""Unit tests for the generator tool input schemas.

Both SearchExercisesInput and BuildWorkoutInput must be Pydantic models and
every field must carry a non-empty description string. Field descriptions are
what the model reads to understand how to call the tools; a missing or empty
description silently degrades generation quality.

The StructuredTool wrappers (search_exercises_tool, build_workout_tool) must
carry names that match the dispatch keys used in graph.py; otherwise a real
model's tool calls will always hit the "Unknown tool" branch.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agents.generator.tools import (
    BuildWorkoutInput,
    SearchExercisesInput,
    build_workout_tool,
    search_exercises_tool,
)


def test_search_exercises_input_is_pydantic_model() -> None:
    assert issubclass(SearchExercisesInput, BaseModel)


def test_build_workout_input_is_pydantic_model() -> None:
    assert issubclass(BuildWorkoutInput, BaseModel)


def test_all_search_exercises_fields_have_non_empty_description() -> None:
    """Every field on SearchExercisesInput must carry a non-empty description."""
    for name, field_info in SearchExercisesInput.model_fields.items():
        assert field_info.description, (
            f"SearchExercisesInput.{name} has no description"
        )
        assert field_info.description.strip(), (
            f"SearchExercisesInput.{name} description is blank"
        )


def test_all_build_workout_fields_have_non_empty_description() -> None:
    """Every field on BuildWorkoutInput must carry a non-empty description."""
    for name, field_info in BuildWorkoutInput.model_fields.items():
        assert field_info.description, (
            f"BuildWorkoutInput.{name} has no description"
        )
        assert field_info.description.strip(), (
            f"BuildWorkoutInput.{name} description is blank"
        )


def test_search_exercises_input_field_names() -> None:
    """Schema field names match the frozen contract surface."""
    assert set(SearchExercisesInput.model_fields) == {
        "muscle_groups",
        "equipment",
        "movement_patterns",
    }


def test_build_workout_input_field_names() -> None:
    """Schema field names match the frozen contract surface."""
    assert set(BuildWorkoutInput.model_fields) == {
        "warmup_ids",
        "main_ids",
        "cooldown_ids",
        "prescriptions",
    }


def test_search_exercises_all_fields_optional() -> None:
    """All SearchExercisesInput fields may be omitted (all default to None)."""
    instance = SearchExercisesInput()
    assert instance.muscle_groups is None
    assert instance.equipment is None
    assert instance.movement_patterns is None


def test_build_workout_prescriptions_field_accepts_prescription_list() -> None:
    """prescriptions field accepts a list of Prescription objects."""
    from app.agents.generator.schemas import Prescription

    p = Prescription(exercise_id="x", name="Test", sets=3, reps=10, rest_seconds=60)
    instance = BuildWorkoutInput(
        warmup_ids=["a"],
        main_ids=["b"],
        cooldown_ids=["c"],
        prescriptions=[p],
    )
    assert len(instance.prescriptions) == 1
    assert instance.prescriptions[0].exercise_id == "x"


# ---------------------------------------------------------------------------
# StructuredTool name assertions — these names must match the dispatch keys
# in graph.py; a mismatch silently sends every real model tool call to the
# "Unknown tool" branch and the workout path never executes.
# ---------------------------------------------------------------------------


def test_search_exercises_tool_name_matches_dispatch_key() -> None:
    """search_exercises_tool.name must equal the dispatch key used in graph.py."""
    assert search_exercises_tool.name == "search_exercises"


def test_build_workout_tool_name_matches_dispatch_key() -> None:
    """build_workout_tool.name must equal the dispatch key used in graph.py."""
    assert build_workout_tool.name == "build_workout"
