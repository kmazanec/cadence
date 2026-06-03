"""Isolated state for the generator subgraph.

Carries its own retry budget (ceiling 2) so a failed tool/validation pass can be
retried without leaking the counter into hub state.
"""

from __future__ import annotations

from typing import TypedDict

from ..generator.schemas import WorkoutPayload

RETRY_CEILING: int = 2


class GeneratorState(TypedDict):
    user_message: str
    injuries: list[str]
    targets: list[str]
    workout: WorkoutPayload | None
    selected_exercise_ids: list[str]
    retry_count: int
