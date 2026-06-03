"""Unit tests for the prescription helper that maps Exercise flags to complete
sets/reps-or-duration/rest Prescription records.

Invariants checked:
- is_reps=True exercises yield a non-None reps value.
- is_duration=True / is_reps=False exercises yield a non-None duration_seconds.
- rest_seconds is always present and positive.
- supports_weight=True exercises may carry a weight string; False ones don't.
- sets is always positive.
"""

from __future__ import annotations

import pytest

from app.agents.generator.prescription import make_prescription
from app.data.json_repository import JsonExerciseRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


def _get(repo: JsonExerciseRepository, name: str):
    """Return the first exercise whose name matches (case-insensitive)."""
    for ex in repo.all():
        if ex.name.casefold() == name.casefold():
            return ex
    raise KeyError(f"No exercise named {name!r} in dataset")


# ---------------------------------------------------------------------------
# is_reps → reps field populated
# ---------------------------------------------------------------------------


def test_reps_exercise_yields_reps(repo) -> None:
    """An is_reps=True exercise must have a non-None reps value."""
    # "Static Jump" is is_reps=True, is_duration=True, no equipment
    ex = _get(repo, "Static Jump")
    assert ex.is_reps
    p = make_prescription(ex)
    assert p.reps is not None
    assert p.reps > 0


# ---------------------------------------------------------------------------
# duration-only → duration_seconds field populated
# ---------------------------------------------------------------------------


def test_duration_only_exercise_yields_duration_seconds(repo) -> None:
    """An is_duration=True / is_reps=False exercise must have a non-None
    duration_seconds value and reps=None."""
    # "Cow Pose" is is_reps=False, is_duration=True
    ex = _get(repo, "Cow Pose")
    assert not ex.is_reps
    assert ex.is_duration
    p = make_prescription(ex)
    assert p.reps is None
    assert p.duration_seconds is not None
    assert p.duration_seconds > 0


# ---------------------------------------------------------------------------
# rest_seconds always present and positive
# ---------------------------------------------------------------------------


def test_prescription_always_has_positive_rest(repo) -> None:
    """Every exercise, regardless of type, must have rest_seconds > 0."""
    for ex in repo.all():
        p = make_prescription(ex)
        assert p.rest_seconds > 0, (
            f"{ex.name!r}: rest_seconds must be positive, got {p.rest_seconds}"
        )


# ---------------------------------------------------------------------------
# sets always positive
# ---------------------------------------------------------------------------


def test_prescription_always_has_positive_sets(repo) -> None:
    """Every exercise must have sets > 0."""
    for ex in repo.all():
        p = make_prescription(ex)
        assert p.sets > 0, (
            f"{ex.name!r}: sets must be positive, got {p.sets}"
        )


# ---------------------------------------------------------------------------
# exercise_id and name copied faithfully
# ---------------------------------------------------------------------------


def test_prescription_carries_exercise_id_and_name(repo) -> None:
    """Prescription.exercise_id and .name must match the source exercise."""
    ex = repo.all()[0]
    p = make_prescription(ex)
    assert p.exercise_id == ex.id
    assert p.name == ex.name


# ---------------------------------------------------------------------------
# supports_weight semantics
# ---------------------------------------------------------------------------


def test_weight_bearing_exercise_may_have_weight(repo) -> None:
    """For exercises where supports_weight=True, weight may be set."""
    weight_exercises = [ex for ex in repo.all() if ex.supports_weight]
    assert weight_exercises, "Expected at least one weight-supporting exercise"
    for ex in weight_exercises:
        p = make_prescription(ex)
        # weight may be None if not specified by default — we just need no crash
        assert isinstance(p.weight, (str, type(None)))


def test_non_weight_exercise_has_no_weight(repo) -> None:
    """For exercises where supports_weight=False, weight should be None."""
    non_weight = [ex for ex in repo.all() if not ex.supports_weight]
    assert non_weight, "Expected at least one non-weight exercise"
    for ex in non_weight:
        p = make_prescription(ex)
        assert p.weight is None, (
            f"{ex.name!r}: supports_weight=False but weight={p.weight!r}"
        )
