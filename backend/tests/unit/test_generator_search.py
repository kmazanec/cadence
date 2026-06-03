"""Unit tests for equipment-satisfiable search and the prescription helper.

Search subset-semantics contract: an exercise is satisfiable iff every item in
its equipment_required is present in the caller's available-equipment set. No
exercise requiring equipment the user lacks can appear in results.

The prescription helper is covered in test_prescription.py.
"""

from __future__ import annotations

import pytest

from app.data.json_repository import JsonExerciseRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


# ---------------------------------------------------------------------------
# Subset-satisfiability: equipment filter
# ---------------------------------------------------------------------------


def test_search_dumbbell_only_excludes_exercises_needing_bench(repo) -> None:
    """All returned exercises must be satisfiable with only a Dumbbell."""
    results = repo.search(equipment=["Dumbbell"])
    for ex in results:
        req = {eq.casefold() for eq in ex.equipment_required}
        available = {"dumbbell"}
        assert req <= available, (
            f"{ex.name!r} requires {ex.equipment_required!r}, "
            "which is not a subset of {['Dumbbell']}"
        )


def test_search_dumbbell_only_returns_dataset_real_exercises(repo) -> None:
    """Every returned exercise id resolves via get_by_id (no ghost entries)."""
    results = repo.search(equipment=["Dumbbell"])
    assert results, "Expected at least one dumbbell-only exercise"
    for ex in results:
        assert repo.get_by_id(ex.id) is not None, (
            f"Exercise id {ex.id!r} does not resolve in the repository"
        )


def test_search_dumbbell_excludes_multi_equipment_exercises(repo) -> None:
    """Exercises requiring both a Dumbbell AND a bench must not appear when only
    a Dumbbell is available."""
    results = repo.search(equipment=["Dumbbell"])
    for ex in results:
        assert "Flat Bench" not in ex.equipment_required, (
            f"{ex.name!r} requires a Flat Bench but was returned for Dumbbell-only search"
        )
        assert "Adjustable Bench - Incline" not in ex.equipment_required, (
            f"{ex.name!r} requires an incline bench but was returned for Dumbbell-only search"
        )
        assert "Adjustable Bench - Decline" not in ex.equipment_required, (
            f"{ex.name!r} requires a decline bench but was returned for Dumbbell-only search"
        )


def test_search_bodyweight_always_satisfiable(repo) -> None:
    """Exercises with an empty equipment_required list are satisfiable by any
    equipment set, including an empty one."""
    results = repo.search(equipment=[])
    for ex in results:
        assert ex.equipment_required == [], (
            f"{ex.name!r} requires {ex.equipment_required!r} but appeared in no-equipment search"
        )


def test_search_yoga_mat_satisfiable_when_mat_available(repo) -> None:
    """Yoga-Mat-only exercises appear when the mat is in the available set."""
    results = repo.search(equipment=["Yoga Mat"])
    yoga_mat_exercises = [ex for ex in results if ex.equipment_required == ["Yoga Mat"]]
    assert yoga_mat_exercises, "Expected at least one Yoga Mat only exercise"


def test_search_no_equipment_filter_returns_all_exercises(repo) -> None:
    """Omitting the equipment filter returns all exercises (no-filter passthrough)."""
    all_count = len(repo.all())
    unfiltered = repo.search()
    assert len(unfiltered) == all_count


def test_search_muscle_groups_and_equipment_combined(repo) -> None:
    """When both filters are supplied, results must satisfy BOTH (AND semantics).
    Every result must target the requested muscle group AND be equipment-satisfiable.
    """
    results = repo.search(muscle_groups=["deltoids"], equipment=["Dumbbell"])
    for ex in results:
        req = {eq.casefold() for eq in ex.equipment_required}
        available = {"dumbbell"}
        assert req <= available, (
            f"{ex.name!r} fails equipment-satisfiability"
        )
        muscle_groups_lower = [mg.casefold() for mg in ex.muscle_groups]
        assert "deltoids" in muscle_groups_lower, (
            f"{ex.name!r} does not target deltoids"
        )


def test_search_with_dumbbell_and_yoga_mat_superset_includes_more_exercises(repo) -> None:
    """A larger available-equipment set should return >= exercises than a smaller one."""
    dumbbell_only = repo.search(equipment=["Dumbbell"])
    dumbbell_and_mat = repo.search(equipment=["Dumbbell", "Yoga Mat"])
    assert len(dumbbell_and_mat) >= len(dumbbell_only), (
        "Adding Yoga Mat to available equipment should not reduce results"
    )


def test_search_movement_patterns_filter_works(repo) -> None:
    """movement_patterns filter returns only exercises matching that pattern."""
    pattern = "upper push - horizontal"
    results = repo.search(movement_patterns=[pattern])
    assert results, "Expected at least one exercise with horizontal push pattern"
    for ex in results:
        patterns_lower = [p.casefold() for p in ex.movement_patterns]
        assert pattern.casefold() in patterns_lower, (
            f"{ex.name!r} does not have pattern {pattern!r}"
        )
