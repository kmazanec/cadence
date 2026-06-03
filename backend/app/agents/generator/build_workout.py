"""Assembles a WorkoutPayload from pre-selected exercise IDs.

All dataset access goes through the ExerciseRepository interface; no direct
JSON reads. The caller supplies three ordered ID lists (one per block) and
optional per-exercise prescriptions; this function resolves each ID, falls back
to the prescription helper for any missing prescription, and assembles the final
three-block payload.

Raises ``ValueError`` if any supplied ID does not resolve in the repository.
The output-validation gate in ``validate_workout`` is the post-hoc check;
this function raises eagerly to surface caller errors before the gate runs.
"""

from __future__ import annotations

from app.agents.generator.prescription import make_prescription
from app.agents.generator.schemas import Block, Prescription, WorkoutPayload
from app.data.repository import Exercise, ExerciseRepository


def build_workout(
    warmup_ids: list[str],
    main_ids: list[str],
    cooldown_ids: list[str],
    repo: ExerciseRepository,
    prescriptions: list[Prescription] | None = None,
) -> WorkoutPayload:
    """Assemble a WorkoutPayload from three ordered lists of exercise IDs.

    Each ID is resolved via ``repo.get_by_id``; if it does not exist the call
    raises ``ValueError`` immediately. A ``prescriptions`` list may supply
    per-exercise overrides keyed by ``exercise_id``; any ID without a matching
    prescription falls back to :func:`make_prescription`.

    The returned payload has exactly three blocks in warmup → main → cooldown
    order.
    """
    # Index provided prescriptions by exercise_id for O(1) lookup.
    prescription_map: dict[str, Prescription] = {}
    if prescriptions:
        for p in prescriptions:
            prescription_map[p.exercise_id] = p

    def _resolve(ids: list[str], block_name: str) -> list[Prescription]:
        resolved: list[Prescription] = []
        for ex_id in ids:
            ex: Exercise | None = repo.get_by_id(ex_id)
            if ex is None:
                raise ValueError(
                    f"exercise_id {ex_id!r} not found in repository "
                    f"(block={block_name!r})"
                )
            if ex_id in prescription_map:
                resolved.append(prescription_map[ex_id])
            else:
                resolved.append(make_prescription(ex))
        return resolved

    return WorkoutPayload(
        blocks=[
            Block(name="warmup", exercises=_resolve(warmup_ids, "warmup")),
            Block(name="main", exercises=_resolve(main_ids, "main")),
            Block(name="cooldown", exercises=_resolve(cooldown_ids, "cooldown")),
        ]
    )
