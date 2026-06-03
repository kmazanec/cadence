"""Unit tests for the output gate's contraindication check.

The gate is the defense-in-depth layer (ADR-009 + ADR-010): even if a
contraindicated exercise slips past the search pre-filter (e.g. due to a
build_workout call with a manually-crafted ID), the gate must catch it and
return GateResult.valid=False so the subgraph can retry or recover gracefully.
"""

from __future__ import annotations

from app.agents.generator.build_workout import build_workout
from app.agents.generator.output_gate import GateResult, validate_workout
from app.agents.generator.schemas import Block, Prescription, WorkoutPayload
from app.data.json_repository import JsonExerciseRepository

_REPO = JsonExerciseRepository()

# Knee-loading exercise from the real dataset.
_KNEE_ID = "00036a08-7c22-42e4-8fe5-323b53e31667"   # Kettlebell Goblet Cyclist Squat
_SAFE_ID = "0e3201e9-4394-4902-a717-f4ce544d98de"   # Push-Up to Knee-Drive
_SAFE_ID2 = "0a2dc786-fb42-4571-9b26-f58cdeb2c70e"  # Bodyweight Pike


def _prescription(exercise_id: str, name: str) -> Prescription:
    return Prescription(
        exercise_id=exercise_id,
        name=name,
        sets=3,
        reps=10,
        rest_seconds=60,
    )


def _payload_with_knee() -> WorkoutPayload:
    return WorkoutPayload(blocks=[
        Block(name="warmup", exercises=[_prescription(_SAFE_ID, "Push-Up to Knee-Drive")]),
        Block(name="main", exercises=[_prescription(_KNEE_ID, "Kettlebell Goblet Cyclist Squat")]),
        Block(name="cooldown", exercises=[_prescription(_SAFE_ID2, "Bodyweight Pike")]),
    ])


def _payload_safe() -> WorkoutPayload:
    return build_workout(
        warmup_ids=[_SAFE_ID],
        main_ids=[_SAFE_ID],
        cooldown_ids=[_SAFE_ID2],
        repo=_REPO,
    )


# ---------------------------------------------------------------------------
# Gate with no injuries (baseline — existing contract)
# ---------------------------------------------------------------------------


def test_gate_no_injuries_passes_valid_payload() -> None:
    """Without injuries, a valid payload passes the gate."""
    result = validate_workout(_payload_safe(), _REPO)
    assert result.valid
    assert result.contraindicated_ids == set()


# ---------------------------------------------------------------------------
# Gate with knee injury
# ---------------------------------------------------------------------------


def test_gate_rejects_contraindicated_exercise(
) -> None:
    """validate_workout with a knee-loading exercise under injuries=['knee'] fails."""
    result = validate_workout(_payload_with_knee(), _REPO, injuries=["knee"])
    assert not result.valid


def test_gate_names_contraindicated_ids() -> None:
    """The gate result carries the offending ID in contraindicated_ids."""
    result = validate_workout(_payload_with_knee(), _REPO, injuries=["knee"])
    assert _KNEE_ID in result.contraindicated_ids


def test_gate_passes_safe_payload_under_knee_injury() -> None:
    """A workout with no knee-loading exercises passes under injuries=['knee']."""
    result = validate_workout(_payload_safe(), _REPO, injuries=["knee"])
    assert result.valid
    assert result.contraindicated_ids == set()


def test_gate_empty_injuries_does_not_block_any_exercise() -> None:
    """injuries=[] applies no contraindication filter."""
    result = validate_workout(_payload_with_knee(), _REPO, injuries=[])
    # The knee exercise is real (not unknown), so the only failure mode would
    # be contraindication. With empty injuries list there should be none.
    assert result.contraindicated_ids == set()


def test_gate_result_is_dataclass() -> None:
    """validate_workout returns a GateResult, not raises."""
    result = validate_workout(_payload_with_knee(), _REPO, injuries=["knee"])
    assert isinstance(result, GateResult)
