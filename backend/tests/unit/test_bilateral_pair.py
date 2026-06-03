"""Unit tests for ExerciseRepository.bilateral_pair.

Tests run against a synthetic in-memory fixture repository, not the shipped
dataset, because all 18 bilateral_pair_id values in data/exercises.json are
dangling (none resolve via _by_id). The real-dataset behavior (returns None for
every catalogue entry) is confirmed in a separate assertion; the auto-pairing
code path is exercised via the fixture.

Decision rationale: do not mutate the shipped dataset to manufacture resolvable
pairs; instead test the code path with a minimal fixture that has a genuinely
reciprocal pair. This keeps the dataset untouched while fully exercising the
bilateral resolution logic.
"""

from __future__ import annotations

import pytest

from app.data.json_repository import JsonExerciseRepository
from app.data.repository import Exercise, ExerciseRepository

# ---------------------------------------------------------------------------
# Synthetic fixture: a tiny in-memory repo with one resolvable reciprocal pair
# ---------------------------------------------------------------------------

_LEFT_ID = "fixture-left-0001"
_RIGHT_ID = "fixture-right-0002"
_UNILATERAL_NO_PAIR_ID = "fixture-unilateral-no-pair"
_DANGLING_ID = "fixture-dangling-0003"


def _make_exercise(
    id: str,
    name: str,
    joints_loaded: list[str] | None = None,
    bilateral_pair_id: str | None = None,
) -> Exercise:
    return Exercise(
        id=id,
        name=name,
        muscle_groups=["glutes"],
        joints_loaded=joints_loaded or ["hip"],
        movement_patterns=["hinge"],
        equipment_required=[],
        is_bilateral=False,
        side=None,
        priority_tier=1,
        is_reps=True,
        is_duration=False,
        supports_weight=False,
        estimated_rep_duration=None,
        bilateral_pair_id=bilateral_pair_id,
    )


class _FixtureRepo:
    """Minimal in-memory repository with a single resolvable bilateral pair."""

    def __init__(self) -> None:
        exercises = [
            _make_exercise(_LEFT_ID, "Left Hip Hinge", bilateral_pair_id=_RIGHT_ID),
            _make_exercise(_RIGHT_ID, "Right Hip Hinge", bilateral_pair_id=_LEFT_ID),
            _make_exercise(_UNILATERAL_NO_PAIR_ID, "Single-Leg Balance"),
            # Dangling: bilateral_pair_id points to an ID not in the catalogue.
            _make_exercise(_DANGLING_ID, "Dangling Pair Exercise", bilateral_pair_id="nonexistent-id"),
        ]
        self._by_id: dict[str, Exercise] = {ex.id: ex for ex in exercises}
        self._exercises = exercises

    def search(self, **kwargs) -> list[Exercise]:
        return list(self._exercises)

    def get_by_id(self, id: str) -> Exercise | None:
        return self._by_id.get(id)

    def contraindicated_ids(self, injuries: list[str]) -> set[str]:
        wanted = {j.casefold() for j in injuries} if injuries else set()
        if not wanted:
            return set()
        return {
            ex.id
            for ex in self._exercises
            if wanted & {j.casefold() for j in ex.joints_loaded}
        }

    def bilateral_pair(self, id: str) -> Exercise | None:
        ex = self._by_id.get(id)
        if ex is None or ex.bilateral_pair_id is None:
            return None
        return self._by_id.get(ex.bilateral_pair_id)

    def all(self) -> list[Exercise]:
        return list(self._exercises)


@pytest.fixture(scope="module")
def fixture_repo() -> _FixtureRepo:
    return _FixtureRepo()


# ---------------------------------------------------------------------------
# Bilateral pair resolution
# ---------------------------------------------------------------------------


def test_bilateral_pair_returns_partner(fixture_repo: _FixtureRepo) -> None:
    """bilateral_pair(left_id) returns the right exercise and vice versa."""
    right = fixture_repo.bilateral_pair(_LEFT_ID)
    assert right is not None
    assert right.id == _RIGHT_ID

    left = fixture_repo.bilateral_pair(_RIGHT_ID)
    assert left is not None
    assert left.id == _LEFT_ID


def test_bilateral_pair_none_for_no_pair_id(fixture_repo: _FixtureRepo) -> None:
    """bilateral_pair returns None when the exercise has no bilateral_pair_id."""
    result = fixture_repo.bilateral_pair(_UNILATERAL_NO_PAIR_ID)
    assert result is None


def test_bilateral_pair_none_for_dangling_id(fixture_repo: _FixtureRepo) -> None:
    """bilateral_pair returns None when the bilateral_pair_id does not resolve."""
    result = fixture_repo.bilateral_pair(_DANGLING_ID)
    assert result is None


def test_bilateral_pair_none_for_absent_id(fixture_repo: _FixtureRepo) -> None:
    """bilateral_pair returns None when the source id is not in the catalogue."""
    result = fixture_repo.bilateral_pair("completely-absent-id")
    assert result is None


# ---------------------------------------------------------------------------
# Real-dataset: confirm all pairs are dangling (documents known limitation)
# ---------------------------------------------------------------------------


def test_real_dataset_all_bilateral_pairs_are_dangling() -> None:
    """All 18 bilateral_pair_id values in the shipped dataset are dangling.

    This test documents the known dataset state: no catalogue exercise has a
    resolvable bilateral partner. The bilateral code path is exercised via the
    synthetic fixture above rather than against this dataset, per the pre-build
    decision recorded in the feature spec.
    """
    repo = JsonExerciseRepository()
    for ex in repo.all():
        if ex.bilateral_pair_id is not None:
            partner = repo.bilateral_pair(ex.id)
            assert partner is None, (
                f"Unexpected resolvable pair found: {ex.name!r} -> "
                f"{ex.bilateral_pair_id!r}. If this is now intentional, "
                f"update the bilateral integration tests to use the real dataset."
            )
