"""Critical-path #3: no-hallucination output gate + empty/thin-search recovery +
invalid-tool-call recovery.

Rationale (ADR-018, priority #3):
  The safety-critical invariant is that the system NEVER presents a fabricated
  exercise to the user. Two failure modes threaten this: (a) the model searches
  for absent equipment, finds nothing, and is tempted to invent IDs; (b) the
  model emits a build_workout call with a bogus/unknown exercise ID that slips
  through unvalidated. This file tests both paths deterministically — no live
  LLM, no network — by scripting the model's responses via the get_model seam.

Architecture risks pinned:
  1. Empty/thin search must trigger graceful recovery, not fabrication. The
     generator graph must fall through to the graceful-degrade path when the
     assembled workout is None after all retries.
  2. The output gate must reject any exercise_id not present in the repository
     before the result leaves the subgraph. A fake ID must cause retry_count
     to increment, capped at RETRY_CEILING=2, after which the subgraph returns
     a graceful-recovery (workout=None) result.
  3. RetryPolicy must NOT be relied on for tool-call retries. The node must use
     explicit try/except and state-tracked retry_count. This test confirms the
     retry path by counting gate invocations — if RetryPolicy swallowed the
     failure silently the test would see retry_count==0, which fails.

All assertions run offline — no OPENROUTER_API_KEY required.
"""

from __future__ import annotations

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_exercise_ids_from_repo() -> set[str]:
    """Return the full set of exercise IDs in the production dataset."""
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    return {ex.id for ex in repo.all()}


# ---------------------------------------------------------------------------
# Empty/thin search recovery — no-hallucination guarantee
# ---------------------------------------------------------------------------


class _EmptySearchModel(BaseChatModel):
    """A scripted model that searches for 'sled' (absent equipment), gets back
    an empty list, then gives up without calling build_workout.

    This simulates the exact scenario from AC-1: equipment absent from the
    dataset. The model finds nothing and returns a plain text apology.
    """

    _call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "empty-search-stub"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        self.__class__._call_count += 1
        # On first call: search for 'sled' via tool call.
        if self.__class__._call_count == 1:
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "search_exercises",
                        "args": {"equipment": ["sled"]},
                    }
                ],
            )
        else:
            # After getting empty search results, give up gracefully.
            ai_msg = AIMessage(
                content="I couldn't find any exercises that use a sled in our catalogue. "
                "Try asking for equipment like dumbbells or barbells instead."
            )
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.asyncio
async def test_empty_search_no_hallucination(monkeypatch):
    """A request for absent equipment produces no workout (no invented exercises).

    When search_exercises returns an empty list, the generator must not
    fabricate exercise IDs. The subgraph returns workout=None (graceful degrade).
    All exercise IDs in the final state must be a subset of the real catalogue.
    """
    _EmptySearchModel._call_count = 0
    monkeypatch.setattr("app.models.factory.get_model", lambda _role: _EmptySearchModel())

    from app.agents.generator.graph import build_generator_subgraph
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "build me a workout using only a sled",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    # No workout assembled — graceful degrade.
    assert result["workout"] is None, (
        "Expected no workout when search returns empty (absent equipment), "
        f"but got: {result['workout']}"
    )

    # Any selected IDs must come from the real catalogue.
    selected = set(result.get("selected_exercise_ids") or [])
    known_ids = _all_exercise_ids_from_repo()
    invented = selected - known_ids
    assert not invented, (
        f"Generator hallucinated exercise IDs not in the dataset: {invented}"
    )


@pytest.mark.asyncio
async def test_empty_search_no_unhandled_exception(monkeypatch):
    """Empty-search path must not raise an unhandled exception."""
    _EmptySearchModel._call_count = 0
    monkeypatch.setattr("app.models.factory.get_model", lambda _role: _EmptySearchModel())

    from app.agents.generator.graph import build_generator_subgraph
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    # Must not raise.
    result = await generator.ainvoke({
        "user_message": "workout using only a sled",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })
    assert result is not None


# ---------------------------------------------------------------------------
# Invalid tool call (bogus exercise ID) — output gate + bounded retry
# ---------------------------------------------------------------------------


def _make_bogus_id_model(bogus_id: str = "BOGUS_EXERCISE_ID_12345"):
    """Return a model scripted to emit a build_workout call with a bogus ID."""

    call_count = [0]

    class _BogusIdModel(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "bogus-id-stub"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            from langchain_core.messages import AIMessage
            from langchain_core.outputs import ChatGeneration, ChatResult

            call_count[0] += 1
            n = call_count[0]

            if n == 1:
                # First: search for something to get IDs (returns real ones).
                ai_msg = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"call_{n}",
                            "name": "search_exercises",
                            "args": {"muscle_groups": ["chest"]},
                        }
                    ],
                )
            else:
                # Subsequent: always try to build a workout with a bogus ID.
                ai_msg = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"call_{n}",
                            "name": "build_workout",
                            "args": {
                                "warmup_ids": [bogus_id],
                                "main_ids": [bogus_id],
                                "cooldown_ids": [bogus_id],
                                "prescriptions": [
                                    {
                                        "exercise_id": bogus_id,
                                        "name": "Fake Exercise",
                                        "sets": 3,
                                        "reps": 10,
                                        "rest_seconds": 60,
                                    }
                                ],
                            },
                        }
                    ],
                )
            return ChatResult(generations=[ChatGeneration(message=ai_msg)])

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

        def bind_tools(self, tools, **kwargs):
            return self

    return _BogusIdModel(), call_count


@pytest.mark.asyncio
async def test_bogus_exercise_id_gate_rejects_and_retries(monkeypatch):
    """A bogus exercise ID is caught by the output gate; retry_count increments.

    The gate must reject the bogus ID and trigger a retry. The retry_count must
    not exceed RETRY_CEILING (2). After exhausting retries, workout must be None
    (graceful degrade — not a fabricated result).
    """
    from app.agents.generator.state import RETRY_CEILING

    model, call_count = _make_bogus_id_model()
    monkeypatch.setattr("app.models.factory.get_model", lambda _role: model)

    from app.agents.generator.graph import build_generator_subgraph
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "build me a chest workout",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    # Gate rejected the bogus ID — no workout in the final state.
    assert result["workout"] is None, (
        "Expected workout=None after gate rejects bogus ID on all retries, "
        f"but got a payload: {result['workout']}"
    )

    # retry_count is bounded by RETRY_CEILING (2).
    final_retry = result.get("retry_count", 0)
    assert final_retry <= RETRY_CEILING, (
        f"retry_count={final_retry} exceeds RETRY_CEILING={RETRY_CEILING}"
    )

    # Output gate must have rejected the bogus ID — no invented IDs in results.
    selected = set(result.get("selected_exercise_ids") or [])
    known_ids = _all_exercise_ids_from_repo()
    invented = selected - known_ids
    assert not invented, (
        f"Gate allowed fabricated exercise IDs through: {invented}"
    )


@pytest.mark.asyncio
async def test_retry_count_increments_on_gate_failure(monkeypatch):
    """Verify retry_count increments per gate failure, capped at RETRY_CEILING.

    This test is the explicit counter that the retry mechanism is state-tracked
    (not silently swallowed by a RetryPolicy). If RetryPolicy were used and
    swallowed the ValidationError, retry_count would stay at 0, failing this test.
    """
    from app.agents.generator.state import RETRY_CEILING

    model, _count = _make_bogus_id_model()
    monkeypatch.setattr("app.models.factory.get_model", lambda _role: model)

    from app.agents.generator.graph import build_generator_subgraph
    from app.data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    result = await generator.ainvoke({
        "user_message": "build me a chest workout",
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    })

    # retry_count must be > 0 (the gate did fail and increment it).
    final_retry = result.get("retry_count", 0)
    assert final_retry > 0, (
        "retry_count never incremented — the gate did not trigger retries. "
        "This may mean RetryPolicy swallowed the failure rather than the "
        "state-tracked retry path firing."
    )
    # And it must not exceed the ceiling.
    assert final_retry <= RETRY_CEILING, (
        f"retry_count={final_retry} exceeded RETRY_CEILING={RETRY_CEILING}"
    )
