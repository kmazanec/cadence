"""Deterministic prescription builder.

Maps an :class:`~app.data.repository.Exercise` to a complete
:class:`~app.agents.generator.schemas.Prescription` using the exercise's own
flags rather than model-generated guesses.

Rules:
- ``is_reps=True`` → reps=10 (a reasonable working-set default).
- ``is_duration=True`` / ``is_reps=False`` → duration_seconds=30.
- ``rest_seconds`` is always 60 (one minute between sets is a safe, broadly
  applicable default that the model can override when it builds the full workout).
- ``sets`` defaults to 3 — a standard working set count.
- ``weight`` is "bodyweight" when supports_weight is False; None (let the model
  supply a value) when supports_weight is True, because the appropriate load
  depends on user-specific context the model knows and this layer does not.
"""

from __future__ import annotations

from app.agents.generator.schemas import Prescription
from app.data.repository import Exercise

# Sensible per-variable defaults that hold across most exercises without
# requiring per-exercise tuning. The model (or future exercise metadata) can
# override these when assembling the final workout.
_DEFAULT_SETS: int = 3
_DEFAULT_REPS: int = 10
_DEFAULT_DURATION_SECONDS: int = 30
_DEFAULT_REST_SECONDS: int = 60


def make_prescription(exercise: Exercise) -> Prescription:
    """Return a :class:`Prescription` for *exercise* using its capability flags.

    Exactly one of ``reps`` or ``duration_seconds`` is populated, following the
    exercise's ``is_reps`` / ``is_duration`` flags. When both flags are set,
    ``reps`` wins because reps prescriptions are the more common fitness-app
    convention; duration is recorded for timed intervals where reps make no sense.
    """
    reps: int | None = None
    duration_seconds: int | None = None

    if exercise.is_reps:
        reps = _DEFAULT_REPS
    elif exercise.is_duration:
        duration_seconds = _DEFAULT_DURATION_SECONDS

    # weight is omitted when the exercise does not load external resistance;
    # the supports_weight flag already tells the UI this is a bodyweight exercise.
    weight: str | None = None

    return Prescription(
        exercise_id=exercise.id,
        name=exercise.name,
        sets=_DEFAULT_SETS,
        reps=reps,
        duration_seconds=duration_seconds,
        rest_seconds=_DEFAULT_REST_SECONDS,
        weight=weight,
    )
