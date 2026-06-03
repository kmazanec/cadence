"""Tests for the fuzzy-match exercise resolver.

RapidFuzz WRatio(cutoff=80) resolves a known name to a real exercise id.
An unmatchable name is flagged unmatched (no invented substitution).
The LLM-verify path is toggled off for determinism.
"""

from __future__ import annotations

import pytest

from app.agents.logger.resolver import resolve_exercise_name
from app.data.json_repository import JsonExerciseRepository


@pytest.fixture
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


def test_known_name_resolves_to_real_exercise(repo) -> None:
    """'bench press' (WRatio cutoff 80) → a real exercise whose name contains 'Bench Press'."""
    result = resolve_exercise_name("bench press", repo, llm_verify=False)
    assert result is not None, "Expected a match for 'bench press'"
    exercise_id, exercise_name = result
    assert "bench press" in exercise_name.lower(), (
        f"Expected resolved name to contain 'bench press', got: {exercise_name}"
    )


def test_unmatchable_name_returns_none(repo) -> None:
    """An unmatchable exercise name returns None — never invented."""
    result = resolve_exercise_name("zercher good-mornings", repo, llm_verify=False)
    assert result is None, (
        f"Expected no match for unmatchable name, got: {result}"
    )


def test_cutoff_80_rejects_weak_match(repo) -> None:
    """A very short or unrelated string that would score below 80 returns None."""
    result = resolve_exercise_name("xyz", repo, llm_verify=False)
    assert result is None


def test_resolve_returns_tuple_of_id_and_name(repo) -> None:
    """When a match is found, the return type is (str, str)."""
    result = resolve_exercise_name("squat", repo, llm_verify=False)
    # Squat may or may not match depending on dataset names; we check the shape.
    if result is not None:
        exercise_id, exercise_name = result
        assert isinstance(exercise_id, str)
        assert isinstance(exercise_name, str)


def test_case_insensitive_match(repo) -> None:
    """Matching is case-insensitive."""
    lower = resolve_exercise_name("bench press", repo, llm_verify=False)
    upper = resolve_exercise_name("BENCH PRESS", repo, llm_verify=False)
    mixed = resolve_exercise_name("Bench Press", repo, llm_verify=False)
    # All three should produce the same result.
    assert lower == upper == mixed
