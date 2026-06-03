"""Unit tests for the injury pre-filter in the exercise search path.

The search pre-filter drops contraindicated exercise IDs from results before
serialising them for the model. This is the first defense layer (ADR-009 hard
pre-filter); the output gate is the second.
"""

from __future__ import annotations

import json

from app.agents.generator.graph import _execute_search
from app.data.json_repository import JsonExerciseRepository

_REPO = JsonExerciseRepository()

# Known knee-loading exercise present in the dataset.
_KNOWN_KNEE_ID = "00036a08-7c22-42e4-8fe5-323b53e31667"  # Kettlebell Goblet Cyclist Squat


def test_search_with_no_injuries_returns_knee_exercises() -> None:
    """Without injuries, search can return knee-loading exercises."""
    result_str = _execute_search({"muscle_groups": ["quads"]}, _REPO, injuries=None)
    results = json.loads(result_str)
    ids = {ex["id"] for ex in results}
    # At least one knee-loading exercise should appear in quad results.
    knee_ids = _REPO.contraindicated_ids(["knee"])
    assert ids & knee_ids, "Expected at least one knee-loading result with no injuries"


def test_search_with_knee_injury_excludes_all_knee_loading_ids() -> None:
    """With injuries=['knee'], search results contain no knee-loading exercise."""
    result_str = _execute_search({"muscle_groups": ["quads"]}, _REPO, injuries=["knee"])
    results = json.loads(result_str)
    ids = {ex["id"] for ex in results}
    knee_ids = _REPO.contraindicated_ids(["knee"])
    contraindicated_in_results = ids & knee_ids
    assert not contraindicated_in_results, (
        f"Knee-loading IDs appeared in search results despite injury filter: "
        f"{contraindicated_in_results}"
    )


def test_search_with_empty_injury_list_behaves_like_no_injuries() -> None:
    """An empty injuries list applies no filter — same as injuries=None."""
    no_filter = set(
        ex["id"]
        for ex in json.loads(_execute_search({"muscle_groups": ["quads"]}, _REPO, injuries=None))
    )
    empty_filter = set(
        ex["id"]
        for ex in json.loads(_execute_search({"muscle_groups": ["quads"]}, _REPO, injuries=[]))
    )
    assert no_filter == empty_filter
