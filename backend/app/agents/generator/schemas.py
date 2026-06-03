"""The workout payload: the structured shape a generated workout takes when it
leaves the generator and crosses into hub state, the API response, and the UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

BlockName = Literal["warmup", "main", "cooldown"]


class Prescription(BaseModel):
    """A single prescribed exercise within a block.

    Exactly one of ``reps`` / ``duration_seconds`` is expected depending on the
    exercise; ``weight`` is carried as stated text (e.g. "bodyweight", "20kg").
    """

    exercise_id: str
    name: str
    sets: int
    reps: int | None = None
    duration_seconds: int | None = None
    rest_seconds: int
    weight: str | None = None


class Block(BaseModel):
    """A named section of a workout."""

    name: BlockName
    exercises: list[Prescription]


class WorkoutPayload(BaseModel):
    """A complete generated workout."""

    blocks: list[Block]
