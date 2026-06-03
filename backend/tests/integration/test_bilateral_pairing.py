"""Integration tests for bilateral auto-pairing in build_workout.

Tests run against a synthetic fixture repository with a resolvable reciprocal
pair, because all 18 bilateral_pair_id values in the shipped dataset are
dangling. The auto-pairing code path is fully exercised; the dataset limitation
is documented.

Acceptance criteria tested:
- AC #2: selecting a unilateral exercise with a resolvable bilateral_pair_id
  yields both the source and its partner in the same block.
- A contraindicated partner is NOT auto-added (exclusion wins over pairing).
- No duplicate when the partner is already present in the selected IDs.
- build_workout returns None-pair exercises unchanged (dangling guard).
"""

from __future__ import annotations

import pytest

from app.agents.generator.build_workout import build_workout
from app.data.repository import Exercise

# ---------------------------------------------------------------------------
# Synthetic fixture repo: one resolvable reciprocal left/right pair
# ---------------------------------------------------------------------------

_LEFT_ID = "fixture-left-0001"
_RIGHT_ID = "fixture-right-0002"
_SAFE_ONLY_ID = "fixture-safe-0003"
_KNEE_PAIR_SRC_ID = "fixture-knee-src-0004"
_KNEE_PAIR_PARTNER_ID = "fixture-knee-partner-0005"


def _ex(
    id: str,
    name: str,
    joints: list[str] | None = None,
    pair_id: str | None = None,
) -> Exercise:
    return Exercise(
        id=id,
        name=name,
        muscle_groups=["glutes"],
        joints_loaded=joints or ["hip"],
        movement_patterns=["hinge"],
        equipment_required=[],
        is_bilateral=False,
        side=None,
        priority_tier=1,
        is_reps=True,
        is_duration=False,
        supports_weight=False,
        estimated_rep_duration=None,
        bilateral_pair_id=pair_id,
    )


class _FixtureRepo:
    def __init__(self) -> None:
        exercises = [
            _ex(_LEFT_ID, "Left Hip Hinge", pair_id=_RIGHT_ID),
            _ex(_RIGHT_ID, "Right Hip Hinge", pair_id=_LEFT_ID),
            _ex(_SAFE_ONLY_ID, "Safe No-Pair Exercise"),
            # Pair where one member loads the knee (for contraindicated-partner test)
            _ex(_KNEE_PAIR_SRC_ID, "Left Knee Exercise", joints=["knee"], pair_id=_KNEE_PAIR_PARTNER_ID),
            _ex(_KNEE_PAIR_PARTNER_ID, "Right Knee Exercise", joints=["knee"], pair_id=_KNEE_PAIR_SRC_ID),
        ]
        self._by_id: dict[str, Exercise] = {e.id: e for e in exercises}
        self._exercises = exercises

    def search(self, **kwargs) -> list[Exercise]:
        return list(self._exercises)

    def get_by_id(self, id: str) -> Exercise | None:
        return self._by_id.get(id)

    def contraindicated_ids(self, injuries: list[str]) -> set[str]:
        wanted = {j.casefold() for j in injuries} if injuries else set()
        if not wanted:
            return set()
        return {ex.id for ex in self._exercises if wanted & {j.casefold() for j in ex.joints_loaded}}

    def bilateral_pair(self, id: str) -> Exercise | None:
        ex = self._by_id.get(id)
        if ex is None or ex.bilateral_pair_id is None:
            return None
        return self._by_id.get(ex.bilateral_pair_id)

    def all(self) -> list[Exercise]:
        return list(self._exercises)


@pytest.fixture(scope="module")
def repo() -> _FixtureRepo:
    return _FixtureRepo()


# ---------------------------------------------------------------------------
# AC #2: unilateral selection pulls in its pair
# ---------------------------------------------------------------------------


def test_unilateral_selection_pulls_in_bilateral_pair(repo: _FixtureRepo) -> None:
    """Selecting a unilateral exercise auto-includes its bilateral partner in the
    same block when the partner resolves and is not contraindicated."""
    payload = build_workout(
        warmup_ids=[_LEFT_ID],
        main_ids=[_SAFE_ONLY_ID],
        cooldown_ids=[_SAFE_ONLY_ID],
        repo=repo,
        injuries=None,
    )
    warmup_ids = [p.exercise_id for p in payload.blocks[0].exercises]
    assert _LEFT_ID in warmup_ids, "Source exercise must still be present"
    assert _RIGHT_ID in warmup_ids, "Bilateral partner must be auto-included in same block"


def test_bilateral_partner_in_same_block_not_other_blocks(repo: _FixtureRepo) -> None:
    """The auto-included partner appears only in the block that selected the source."""
    payload = build_workout(
        warmup_ids=[_LEFT_ID],
        main_ids=[_SAFE_ONLY_ID],
        cooldown_ids=[_SAFE_ONLY_ID],
        repo=repo,
        injuries=None,
    )
    main_ids = [p.exercise_id for p in payload.blocks[1].exercises]
    cooldown_ids = [p.exercise_id for p in payload.blocks[2].exercises]
    assert _RIGHT_ID not in main_ids, "Partner must not appear in main block"
    assert _RIGHT_ID not in cooldown_ids, "Partner must not appear in cooldown block"


# ---------------------------------------------------------------------------
# Contraindicated partner is NOT auto-added (exclusion wins over pairing)
# ---------------------------------------------------------------------------


def test_contraindicated_partner_not_added(repo: _FixtureRepo) -> None:
    """When the bilateral partner is contraindicated, it is NOT auto-included.

    Exclusion takes precedence over bilateral pairing to preserve the safety
    invariant: a contraindicated exercise must never appear in the workout.
    """
    payload = build_workout(
        warmup_ids=[_KNEE_PAIR_SRC_ID],
        main_ids=[_SAFE_ONLY_ID],
        cooldown_ids=[_SAFE_ONLY_ID],
        repo=repo,
        injuries=["knee"],
    )
    # Both source and partner load the knee, but source was explicitly requested.
    # Partner must not be auto-added since it is contraindicated.
    warmup_ids = [p.exercise_id for p in payload.blocks[0].exercises]
    assert _KNEE_PAIR_PARTNER_ID not in warmup_ids, (
        "Contraindicated partner must not be auto-added even when a bilateral "
        "pair exists — exclusion wins over pairing."
    )


# ---------------------------------------------------------------------------
# No duplicate when partner is already in the selected set
# ---------------------------------------------------------------------------


def test_no_duplicate_when_partner_already_selected(repo: _FixtureRepo) -> None:
    """When both sides of a bilateral pair are explicitly requested, the partner
    is not added again — no duplicate prescriptions."""
    payload = build_workout(
        warmup_ids=[_LEFT_ID, _RIGHT_ID],
        main_ids=[_SAFE_ONLY_ID],
        cooldown_ids=[_SAFE_ONLY_ID],
        repo=repo,
        injuries=None,
    )
    warmup_ids = [p.exercise_id for p in payload.blocks[0].exercises]
    assert warmup_ids.count(_LEFT_ID) == 1, "Left must appear exactly once"
    assert warmup_ids.count(_RIGHT_ID) == 1, "Right must appear exactly once"


# ---------------------------------------------------------------------------
# No-pair exercise passes through unchanged
# ---------------------------------------------------------------------------


def test_exercise_without_pair_not_affected(repo: _FixtureRepo) -> None:
    """An exercise with no bilateral_pair_id is assembled as-is, unchanged."""
    payload = build_workout(
        warmup_ids=[_SAFE_ONLY_ID],
        main_ids=[_SAFE_ONLY_ID],
        cooldown_ids=[_SAFE_ONLY_ID],
        repo=repo,
        injuries=None,
    )
    for block in payload.blocks:
        ids = [p.exercise_id for p in block.exercises]
        assert ids == [_SAFE_ONLY_ID], f"Block {block.name!r} unexpectedly modified"
