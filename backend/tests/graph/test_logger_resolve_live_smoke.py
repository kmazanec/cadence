"""Live smoke test: generic exercise names resolve through the LLM-verify path.

Why this file: the offline critical test ``test_bench_press_resolves_to_dataset_id``
runs with ``llm_verify=False``, so it exercises only the RapidFuzz layer. But in
production the resolver runs with ``llm_verify=True``, and a too-strict verify
prompt can REJECT a generic name whose shortlist contains only qualified
variants (e.g. 'bench press' vs 'Barbell Decline Bench Press') — silently
flagging the brief's canonical example as unmatched.

This test pins the brief requirement ("user says 'bench press', not 'Barbell
Flat Bench Press'") against the real LLM verify step. Skipped without a key so
CI stays offline.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set — live smoke skipped",
)


@pytest.mark.live
def test_generic_bench_press_resolves_via_llm_verify() -> None:
    """The brief's canonical generic name resolves to a catalogue variant.

    Runs the full resolver including the LLM verify step (llm_verify=True), the
    way production does — guarding against a verify prompt that over-rejects
    generic-to-variant matches.
    """
    from app.agents.logger.resolver import resolve_exercise_name
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    known_ids = {ex.id for ex in repo.all()}

    result = resolve_exercise_name("bench press", repo, llm_verify=True)

    assert result is not None, (
        "Expected the generic 'bench press' to resolve to a catalogue bench "
        "press variant through the LLM verify path, got None (unmatched)."
    )
    exercise_id, exercise_name = result
    assert exercise_id in known_ids, "Resolved id must be a real catalogue id."
    assert "bench press" in exercise_name.casefold(), (
        f"Expected a bench press variant, got {exercise_name!r}."
    )
