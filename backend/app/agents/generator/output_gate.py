"""Dataset-bounded output gate for the generator subgraph.

Every exercise_id in an assembled workout must resolve in the repository before
the payload leaves the graph. This gate is the enforcement point for the
no-hallucination invariant: a workout that slips through with an unknown ID
would present a fabricated exercise to the user.

The gate returns a value (GateResult) rather than raising so the subgraph node
can decide between a bounded retry (state.retry_count < RETRY_CEILING) and a
graceful recovery response (retry budget exhausted). Using an exception here
would collapse that two-path choice into a single catch block.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.generator.schemas import WorkoutPayload
from app.data.repository import ExerciseRepository


@dataclass
class GateResult:
    """Outcome of the output-validation gate.

    ``valid`` is True iff every exercise_id in the payload resolves in the
    repository. ``unknown_ids`` carries any IDs that failed resolution so the
    caller can log or report them.
    """

    valid: bool
    unknown_ids: set[str] = field(default_factory=set)


def validate_workout(payload: WorkoutPayload, repo: ExerciseRepository) -> GateResult:
    """Check that every exercise_id in *payload* exists in *repo*.

    Iterates all blocks and all prescriptions. Returns immediately with the full
    set of unknown IDs rather than short-circuiting on the first failure, so a
    single pass gives the complete picture for logging and recovery.
    """
    unknown: set[str] = set()

    for block in payload.blocks:
        for prescription in block.exercises:
            if repo.get_by_id(prescription.exercise_id) is None:
                unknown.add(prescription.exercise_id)

    return GateResult(valid=len(unknown) == 0, unknown_ids=unknown)
