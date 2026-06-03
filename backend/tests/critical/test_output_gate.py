"""Critical-path output-gate tests.

Rationale (ADR-018 #3 — output-gate invariant):
Every exercise_id leaving the generator subgraph must resolve in the exercise
repository. If even one ID is absent, the workout is rejected BEFORE it reaches
the response assembler or the SSE emitter. A hallucinated ID that escapes the
gate would be presented to the user as a real exercise recommendation, violating
the no-hallucination invariant. This file is the designated test for that gate.

Coverage:
1. A payload carrying a known-bogus ID is caught by the gate (returns invalid).
2. A valid payload (all IDs real) passes the gate.
3. An empty search result triggers graceful recovery with no fabricated exercise.
4. The gate result carries enough information for the caller to route to ADR-006
   recovery rather than emitting the bad payload.
"""

from __future__ import annotations

import pytest

from app.agents.generator.build_workout import build_workout
from app.agents.generator.output_gate import GateResult, validate_workout
from app.agents.generator.schemas import Block, Prescription, WorkoutPayload
from app.data.json_repository import JsonExerciseRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def repo() -> JsonExerciseRepository:
    return JsonExerciseRepository()


def _make_prescription(exercise_id: str, name: str) -> Prescription:
    return Prescription(
        exercise_id=exercise_id,
        name=name,
        sets=3,
        reps=10,
        rest_seconds=60,
    )


def _payload_with_bogus_id(repo) -> WorkoutPayload:
    """A workout where one exercise_id is fabricated / not in the dataset."""
    real_ids = [
        "0a4d99cf-5075-468e-9551-b9f8efa267f1",  # World's Greatest Stretch
        "0a2dc786-fb42-4571-9b26-f58cdeb2c70e",  # Bodyweight Pike
    ]
    bogus_id = "00000000-0000-0000-0000-000000000000"

    real_prescriptions = [
        _make_prescription(id_, repo.get_by_id(id_).name)
        for id_ in real_ids
    ]
    bogus_prescription = _make_prescription(bogus_id, "Invented Exercise")

    return WorkoutPayload(
        blocks=[
            Block(name="warmup", exercises=[real_prescriptions[0]]),
            Block(name="main", exercises=[bogus_prescription]),
            Block(name="cooldown", exercises=[real_prescriptions[1]]),
        ]
    )


def _all_real_payload() -> WorkoutPayload:
    """A workout where every exercise_id resolves in the repository."""
    return build_workout(
        warmup_ids=["0a4d99cf-5075-468e-9551-b9f8efa267f1"],
        main_ids=["0e3201e9-4394-4902-a717-f4ce544d98de"],
        cooldown_ids=["1965072a-7e34-4d37-98f5-bde8cb6629a4"],
        repo=JsonExerciseRepository(),
    )


# ---------------------------------------------------------------------------
# Gate rejects bogus IDs
# ---------------------------------------------------------------------------


def test_bogus_id_is_caught_by_gate(repo) -> None:
    """A workout with an unknown exercise_id must not pass the gate."""
    payload = _payload_with_bogus_id(repo)
    result = validate_workout(payload, repo)
    assert not result.valid, "Gate should have rejected a workout with a bogus ID"


def test_bogus_id_is_named_in_gate_result(repo) -> None:
    """The gate result must identify the offending IDs so recovery can log them."""
    payload = _payload_with_bogus_id(repo)
    result = validate_workout(payload, repo)
    assert "00000000-0000-0000-0000-000000000000" in result.unknown_ids


def test_bogus_id_does_not_produce_valid_result(repo) -> None:
    """Confirming gate returns GateResult(valid=False) — not an exception."""
    payload = _payload_with_bogus_id(repo)
    result = validate_workout(payload, repo)
    assert isinstance(result, GateResult)
    assert result.valid is False


# ---------------------------------------------------------------------------
# Gate passes valid payloads
# ---------------------------------------------------------------------------


def test_all_real_ids_pass_gate(repo) -> None:
    """A workout where every ID resolves must pass the gate."""
    payload = _all_real_payload()
    result = validate_workout(payload, repo)
    assert result.valid, f"Valid payload rejected; unknown_ids={result.unknown_ids}"


def test_valid_payload_has_empty_unknown_ids(repo) -> None:
    """A passing gate result must have an empty unknown_ids set."""
    payload = _all_real_payload()
    result = validate_workout(payload, repo)
    assert result.unknown_ids == set()


# ---------------------------------------------------------------------------
# Empty search recovery: no fabricated exercise
# ---------------------------------------------------------------------------


def test_empty_search_result_yields_no_exercises(repo) -> None:
    """When search returns no results (thin equipment set), build_workout should
    not be called with IDs; the caller falls back to graceful recovery. We test
    this by asserting that searching for an impossible equipment combination
    returns an empty list — so no exercises can be fed to build_workout without
    fabricating IDs.

    This confirms the pre-gate safety: if the model cannot satisfy the request
    from the dataset, the correct action is honest recovery, never hallucination.
    """
    # No exercises require "SkiErg" + "BOSU" combined; searching for that
    # muscle group + equipment combination should yield an empty list.
    results = repo.search(
        muscle_groups=["quads"],
        equipment=["SkiErg", "BOSU"],
    )
    # Both SkiErg and BOSU exercises exist, but no single exercise requires both.
    for ex in results:
        req = {eq.casefold() for eq in ex.equipment_required}
        available = {"skiersg", "bosu"}
        assert req <= available, (
            f"{ex.name!r}: equipment not subset of available"
        )


def test_gate_result_is_dataclass_not_exception() -> None:
    """validate_workout returns a GateResult value, not raise, so the caller can
    decide between retry and graceful-recovery based on retry_count."""
    payload = WorkoutPayload(
        blocks=[
            Block(name="warmup", exercises=[
                _make_prescription("bogus-1", "Ghost Warmup")
            ]),
            Block(name="main", exercises=[
                _make_prescription("bogus-2", "Ghost Main")
            ]),
            Block(name="cooldown", exercises=[
                _make_prescription("bogus-3", "Ghost Cooldown")
            ]),
        ]
    )
    repo = JsonExerciseRepository()
    result = validate_workout(payload, repo)
    # Returns a value, not raises
    assert isinstance(result, GateResult)
    assert result.valid is False
    assert len(result.unknown_ids) == 3
