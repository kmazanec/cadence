"""JSON-backed implementation of :class:`ExerciseRepository`.

Loads the typed exercise catalogue once at construction. Selection criteria
are matched case-insensitively against the relevant list fields.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .repository import Exercise

# Env override: an explicit path always wins. docker-compose sets this so the
# container never has to guess where the read-only ``/app/data`` volume mounts.
_DATASET_ENV = "CADENCE_EXERCISES_PATH"


def _discover_default_dataset() -> Path:
    """Locate ``data/exercises.json`` by walking up from this file.

    The dataset lives at the project root in ``data/exercises.json``, but how
    many directories sit between this module and that root differs by layout:
    locally it is ``backend/app/data/...`` (root is three parents up), while the
    container's ``COPY . .`` flattens ``backend/`` away so it is ``app/data/...``
    (root is one fewer). A fixed ``parents[N]`` hop is correct for exactly one of
    those and silently wrong for the other. Walking up until we find the file is
    correct for both — and for any future re-nesting.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "exercises.json"
        if candidate.is_file():
            return candidate
    # Fall back to the historical local layout so the error message names a
    # concrete path rather than failing inside the loop.
    return here.parents[3] / "data" / "exercises.json"


def _default_dataset() -> Path:
    override = os.environ.get(_DATASET_ENV)
    if override:
        return Path(override)
    return _discover_default_dataset()


def _normalize(values: list[str]) -> set[str]:
    return {v.casefold() for v in values}


class JsonExerciseRepository:
    """In-memory repository backed by a JSON dataset file."""

    def __init__(self, dataset_path: Path | str | None = None) -> None:
        path = Path(dataset_path) if dataset_path is not None else _default_dataset()
        raw = json.loads(path.read_text())
        self._exercises: list[Exercise] = [Exercise.model_validate(row) for row in raw]
        self._by_id: dict[str, Exercise] = {ex.id: ex for ex in self._exercises}

    def search(
        self,
        muscle_groups: list[str] | None = None,
        equipment: list[str] | None = None,
        movement_patterns: list[str] | None = None,
    ) -> list[Exercise]:
        wanted_muscles = _normalize(muscle_groups) if muscle_groups else None
        # ``None`` means no equipment filter; a list (including empty) enforces
        # subset-satisfiability: every item in the exercise's equipment_required
        # must be present in the caller's available-equipment set. This ensures a
        # returned exercise can actually be performed with what the user has.
        available_equipment: set[str] | None = (
            _normalize(equipment) if equipment is not None else None
        )
        wanted_patterns = _normalize(movement_patterns) if movement_patterns else None

        results: list[Exercise] = []
        for ex in self._exercises:
            if wanted_muscles and not (wanted_muscles & _normalize(ex.muscle_groups)):
                continue
            if available_equipment is not None:
                # Subset check: exercise is satisfiable iff all required equipment
                # is in the available set. An empty required-set means bodyweight,
                # which is always satisfiable.
                if not _normalize(ex.equipment_required) <= available_equipment:
                    continue
            if wanted_patterns and not (wanted_patterns & _normalize(ex.movement_patterns)):
                continue
            results.append(ex)
        return results

    def get_by_id(self, id: str) -> Exercise | None:
        return self._by_id.get(id)

    def contraindicated_ids(self, injuries: list[str]) -> set[str]:
        wanted = _normalize(injuries) if injuries else set()
        if not wanted:
            return set()
        return {
            ex.id
            for ex in self._exercises
            if wanted & _normalize(ex.joints_loaded)
        }

    def bilateral_pair(self, id: str) -> Exercise | None:
        ex = self._by_id.get(id)
        if ex is None or ex.bilateral_pair_id is None:
            return None
        return self._by_id.get(ex.bilateral_pair_id)

    def all(self) -> list[Exercise]:
        return list(self._exercises)
