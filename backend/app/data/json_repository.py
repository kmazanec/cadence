"""JSON-backed implementation of :class:`ExerciseRepository`.

Loads the typed exercise catalogue once at construction. Selection criteria
are matched case-insensitively against the relevant list fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from .repository import Exercise

# data/exercises.json sits at the repository root, two levels above ``backend/``.
_DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "data" / "exercises.json"


def _normalize(values: list[str]) -> set[str]:
    return {v.casefold() for v in values}


class JsonExerciseRepository:
    """In-memory repository backed by a JSON dataset file."""

    def __init__(self, dataset_path: Path | str | None = None) -> None:
        path = Path(dataset_path) if dataset_path is not None else _DEFAULT_DATASET
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
