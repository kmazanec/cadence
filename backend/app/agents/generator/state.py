"""Isolated state for the generator subgraph.

Carries its own retry budget (ceiling 2) so a failed tool/validation pass can be
retried without leaking the counter into hub state.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

from langchain_core.messages import BaseMessage

from ..generator.schemas import WorkoutPayload

RETRY_CEILING: int = 2


class GeneratorState(TypedDict):
    user_message: str
    injuries: list[str]
    targets: list[str]
    workout: WorkoutPayload | None
    selected_exercise_ids: list[str]
    retry_count: int
    # Read-only prior conversation context, supplied by the hub boundary. No
    # reducer: the generator never appends to it, it only seeds the model's
    # tool-loop so follow-up requests ('make it shorter') can resolve against
    # the prior workout. Absent when the generator is driven without a
    # conversation thread; treat as [].
    messages: NotRequired[list[BaseMessage]]
