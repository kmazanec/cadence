"""Tests for the fuzzy-match exercise resolver.

RapidFuzz WRatio(cutoff=80) resolves a known name to a real exercise id.
An unmatchable name is flagged unmatched (no invented substitution).
The LLM-verify path is toggled off for determinism in most tests; dedicated
tests cover the tri-state LLM verify behaviour (declined vs failed).
"""

from __future__ import annotations

import pytest

from app.agents.logger.resolver import _DECLINED, _llm_verify, resolve_exercise_name
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


# ---------------------------------------------------------------------------
# LLM verify tri-state tests
# ---------------------------------------------------------------------------


class _PickModel:
    """Stub structured-output model for verify tests."""

    def __init__(self, pick: int) -> None:
        self._pick = pick

    def with_structured_output(self, schema):  # noqa: ANN001
        return self

    def invoke(self, messages):  # noqa: ANN001
        class _Result:
            pass

        r = _Result()
        r.pick = self._pick  # type: ignore[attr-defined]
        return r


def test_llm_verify_decline_returns_none_not_fuzzy_top(repo, monkeypatch) -> None:
    """When the model picks 0, resolve_exercise_name returns None (not the fuzzy top)."""
    import app.models.factory as _factory

    monkeypatch.setattr(_factory, "get_model", lambda role: _PickModel(0))
    # "bench press" clears the fuzzy cutoff, so without the fix it would be returned.
    result = resolve_exercise_name("bench press", repo, llm_verify=True)
    assert result is None, (
        "Model declined (pick=0) should cause resolve_exercise_name to return None, "
        f"not fall through to the fuzzy top candidate; got: {result}"
    )


def test_llm_verify_failure_falls_back_to_fuzzy_top(repo, monkeypatch) -> None:
    """When the LLM call raises an exception, the fuzzy top result is used."""
    import app.models.factory as _factory

    def _raising_model(role):  # noqa: ANN001
        raise RuntimeError("network error")

    monkeypatch.setattr(_factory, "get_model", _raising_model)
    result = resolve_exercise_name("bench press", repo, llm_verify=True)
    assert result is not None, (
        "LLM call failure should fall back to the fuzzy top candidate, not return None"
    )
    exercise_id, exercise_name = result
    assert "bench press" in exercise_name.lower()


def test_llm_verify_selection_overrides_fuzzy_top(repo, monkeypatch) -> None:
    """When the model picks a valid candidate, that candidate is returned."""
    import app.models.factory as _factory

    monkeypatch.setattr(_factory, "get_model", lambda role: _PickModel(1))
    result = resolve_exercise_name("bench press", repo, llm_verify=True)
    assert result is not None
    exercise_id, exercise_name = result
    assert isinstance(exercise_id, str)
    assert isinstance(exercise_name, str)
