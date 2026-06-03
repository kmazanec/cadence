"""Exercise model and the repository seam through which all dataset access flows."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class Exercise(BaseModel):
    """A single exercise, mirroring the dataset record one-to-one.

    ``is_reps`` and ``is_duration`` are independent flags; an exercise may be
    both. ``bilateral_pair_id`` may reference a row that is not present in the
    dataset — callers must tolerate a dangling reference rather than assume
    integrity.
    """

    id: str
    name: str
    muscle_groups: list[str]
    joints_loaded: list[str]
    movement_patterns: list[str]
    equipment_required: list[str]
    is_bilateral: bool
    side: str | None
    priority_tier: int
    is_reps: bool
    is_duration: bool
    supports_weight: bool
    estimated_rep_duration: float | None
    bilateral_pair_id: str | None


@runtime_checkable
class ExerciseRepository(Protocol):
    """Read access to the exercise catalogue.

    The selection surface intentionally omits ``priority_tier``: it is uniform
    across the catalogue and is never used to rank or filter.
    """

    def search(
        self,
        muscle_groups: list[str] | None = None,
        equipment: list[str] | None = None,
        movement_patterns: list[str] | None = None,
    ) -> list[Exercise]:
        """Return exercises matching every supplied criterion (AND across criteria)."""
        ...

    def get_by_id(self, id: str) -> Exercise | None:
        """Return the exercise with this id, or None if absent."""
        ...

    def contraindicated_ids(self, injuries: list[str]) -> set[str]:
        """Return the ids of exercises to exclude for the given injuries."""
        ...

    def bilateral_pair(self, id: str) -> Exercise | None:
        """Return the paired exercise, or None when there is no resolvable pair."""
        ...

    def all(self) -> list[Exercise]:
        """Return every exercise in the catalogue."""
        ...
