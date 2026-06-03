"""Integration tests for the build_workout assembler.

Feeds hand-picked real exercise IDs through build_workout and asserts:
- Exactly three named blocks (warmup, main, cooldown).
- Every prescription has sets, reps-or-duration (not both None), and rest.
- Every exercise_id resolves via the repository (no ghost IDs).

This is the deterministic core of acceptance criterion 1, independent of the
LLM model layer.
"""

from __future__ import annotations

import pytest

from app.agents.generator.build_workout import build_workout
from app.agents.generator.schemas import WorkoutPayload
from app.data.json_repository import JsonExerciseRepository

# ---------------------------------------------------------------------------
# Stable exercise IDs from the dataset (no-equipment or Yoga-Mat-only so
# these are environment-independent and always resolve in the repo).
# ---------------------------------------------------------------------------

# Warmup candidates (mobility / activation)
_WARMUP_IDS = [
    "0a4d99cf-5075-468e-9551-b9f8efa267f1",  # World's Greatest Stretch
    "1423ff58-68de-47da-8884-cb6f438f5774",  # Walking Toe Touches
]

# Main work block
_MAIN_IDS = [
    "0e3201e9-4394-4902-a717-f4ce544d98de",  # Push-Up to Knee-Drive
    "00e18a26-70dd-4d43-b013-5038b75a41f3",  # Alternating Low Plank To Low Side Plank
    "01f5a2bb-ecf7-4168-92b3-35bd78592e26",  # High Plank Bird Dog
]

# Cooldown candidates (stretch / low-intensity)
_COOLDOWN_IDS = [
    "1965072a-7e34-4d37-98f5-bde8cb6629a4",  # Cow Pose
    "0a9d8d01-a52d-453e-92bc-dd9238e9a930",  # Ground Upper Trap Stretch
]


@pytest.fixture(scope="module")
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


@pytest.fixture(scope="module")
def payload(repo) -> WorkoutPayload:
    return build_workout(
        warmup_ids=_WARMUP_IDS,
        main_ids=_MAIN_IDS,
        cooldown_ids=_COOLDOWN_IDS,
        repo=repo,
    )


# ---------------------------------------------------------------------------
# Block structure
# ---------------------------------------------------------------------------


def test_exactly_three_blocks(payload) -> None:
    """build_workout must produce exactly three blocks."""
    assert len(payload.blocks) == 3


def test_blocks_are_named_warmup_main_cooldown(payload) -> None:
    """Blocks must be named in warmup -> main -> cooldown order."""
    names = [b.name for b in payload.blocks]
    assert names == ["warmup", "main", "cooldown"]


def test_each_block_is_non_empty(payload) -> None:
    """No block may be empty -- every supplied ID must yield an exercise."""
    for block in payload.blocks:
        assert len(block.exercises) > 0, f"Block {block.name!r} is empty"


# ---------------------------------------------------------------------------
# Prescription completeness
# ---------------------------------------------------------------------------


def test_every_prescription_has_sets(payload) -> None:
    for block in payload.blocks:
        for p in block.exercises:
            assert p.sets > 0, f"{p.name!r}: sets must be positive"


def test_every_prescription_has_reps_or_duration(payload) -> None:
    for block in payload.blocks:
        for p in block.exercises:
            has_value = (p.reps is not None) or (p.duration_seconds is not None)
            assert has_value, (
                f"{p.name!r}: both reps and duration_seconds are None"
            )


def test_every_prescription_has_rest(payload) -> None:
    for block in payload.blocks:
        for p in block.exercises:
            assert p.rest_seconds > 0, f"{p.name!r}: rest_seconds must be positive"


# ---------------------------------------------------------------------------
# Dataset integrity: all IDs resolve
# ---------------------------------------------------------------------------


def test_all_exercise_ids_resolve_in_repo(payload, repo) -> None:
    """Every exercise_id in the payload must exist in the repository."""
    for block in payload.blocks:
        for p in block.exercises:
            ex = repo.get_by_id(p.exercise_id)
            assert ex is not None, (
                f"exercise_id {p.exercise_id!r} ({p.name!r}) "
                "does not resolve in the repository"
            )


def test_prescription_name_matches_repo_name(payload, repo) -> None:
    """Prescription.name must match the repository's canonical name."""
    for block in payload.blocks:
        for p in block.exercises:
            ex = repo.get_by_id(p.exercise_id)
            assert ex is not None
            assert p.name == ex.name, (
                f"Prescription name {p.name!r} != repo name {ex.name!r}"
            )


# ---------------------------------------------------------------------------
# Exercise count integrity
# ---------------------------------------------------------------------------


def test_warmup_block_has_correct_exercise_count(payload) -> None:
    warmup = next(b for b in payload.blocks if b.name == "warmup")
    assert len(warmup.exercises) == len(_WARMUP_IDS)


def test_main_block_has_correct_exercise_count(payload) -> None:
    main = next(b for b in payload.blocks if b.name == "main")
    assert len(main.exercises) == len(_MAIN_IDS)


def test_cooldown_block_has_correct_exercise_count(payload) -> None:
    cooldown = next(b for b in payload.blocks if b.name == "cooldown")
    assert len(cooldown.exercises) == len(_COOLDOWN_IDS)
