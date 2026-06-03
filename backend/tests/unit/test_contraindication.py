"""Unit tests for ExerciseRepository.contraindicated_ids.

Locks the behavior of the contraindication method: exact set of knee-loading IDs
from the real dataset, empty injuries produces empty set, case-insensitive matching.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data.json_repository import JsonExerciseRepository

_DATASET = Path(__file__).resolve().parents[3] / "data" / "exercises.json"


@pytest.fixture(scope="module")
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


def _expected_knee_ids() -> set[str]:
    """Compute the expected knee-loading IDs directly from the dataset."""
    data = json.loads(_DATASET.read_text())
    return {
        ex["id"]
        for ex in data
        if any(j.casefold() == "knee" for j in ex.get("joints_loaded", []))
    }


def test_contraindicated_ids_knee_exact_set(repo: JsonExerciseRepository) -> None:
    """contraindicated_ids(['knee']) returns exactly the set of knee-loading IDs."""
    result = repo.contraindicated_ids(["knee"])
    expected = _expected_knee_ids()
    assert result == expected, (
        f"Expected {len(expected)} knee IDs, got {len(result)}. "
        f"Extra: {result - expected}, Missing: {expected - result}"
    )


def test_contraindicated_ids_empty_list(repo: JsonExerciseRepository) -> None:
    """contraindicated_ids([]) returns an empty set — no injuries, no exclusions."""
    assert repo.contraindicated_ids([]) == set()


def test_contraindicated_ids_empty_string_in_list(repo: JsonExerciseRepository) -> None:
    """An empty string in the injury list does not match any joint."""
    result = repo.contraindicated_ids([""])
    assert result == set()


def test_contraindicated_ids_case_insensitive(repo: JsonExerciseRepository) -> None:
    """'Knee', 'KNEE', 'knee' all produce the same contraindicated set."""
    lower = repo.contraindicated_ids(["knee"])
    title = repo.contraindicated_ids(["Knee"])
    upper = repo.contraindicated_ids(["KNEE"])
    assert lower == title == upper


def test_contraindicated_ids_multiple_injuries(repo: JsonExerciseRepository) -> None:
    """contraindicated_ids(['knee', 'shoulder']) is a superset of either alone."""
    knee_only = repo.contraindicated_ids(["knee"])
    shoulder_only = repo.contraindicated_ids(["shoulder"])
    combined = repo.contraindicated_ids(["knee", "shoulder"])
    assert knee_only <= combined
    assert shoulder_only <= combined
    assert combined == knee_only | shoulder_only


def test_contraindicated_ids_unknown_joint(repo: JsonExerciseRepository) -> None:
    """An unrecognised joint term produces an empty set, not an error."""
    result = repo.contraindicated_ids(["notajoint"])
    assert result == set()
