"""Integration tests for explanation Reason emission.

Verifies that:
- A knee-injury request produces Reason(claim='excluded', relation='loads_joint')
  for contraindicated exercises (AC #4 — exclusion reasons).
- When a bilateral pair is auto-included, a Reason(claim='added',
  relation='bilateral_pair_of') is emitted (AC #4 — pairing reasons).

Both tests drive _generator_boundary_node directly via the hub's internal
adapter, using a deterministic fake model (no LLM).
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.graph.explanation import Reason
from app.graph.hub import _generator_boundary_node
from app.graph.state import HubState

# ---------------------------------------------------------------------------
# Fake model (schema-aware, reuses _SequentialFakeModel pattern)
# ---------------------------------------------------------------------------

_SAFE_WARMUP = "0e3201e9-4394-4902-a717-f4ce544d98de"   # Push-Up to Knee-Drive
_SAFE_MAIN = "0a2dc786-fb42-4571-9b26-f58cdeb2c70e"     # Bodyweight Pike
_SAFE_COOLDOWN = "1423ff58-68de-47da-8884-cb6f438f5774"  # Walking Toe Touches


def _search_msg() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "s1",
            "name": "search_exercises",
            "args": {"muscle_groups": ["chest"]},
            "type": "tool_call",
        }],
    )


def _build_msg(
    warmup: str = _SAFE_WARMUP,
    main: str = _SAFE_MAIN,
    cooldown: str = _SAFE_COOLDOWN,
) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{
            "id": "b1",
            "name": "build_workout",
            "args": {
                "warmup_ids": [warmup],
                "main_ids": [main],
                "cooldown_ids": [cooldown],
                "prescriptions": [
                    {"exercise_id": warmup, "name": "Warmup", "sets": 2, "reps": 8, "rest_seconds": 30},
                    {"exercise_id": main, "name": "Main", "sets": 3, "reps": 10, "rest_seconds": 60},
                    {"exercise_id": cooldown, "name": "Cooldown", "sets": 1, "duration_seconds": 30, "rest_seconds": 30},
                ],
            },
            "type": "tool_call",
        }],
    )


class _SequentialFakeModel(GenericFakeChatModel):
    def __init__(self, responses: list[AIMessage]) -> None:
        super().__init__(messages=iter([]))
        self._responses = iter(responses)

    def invoke(self, *args, **kwargs):
        return next(self._responses)

    async def ainvoke(self, *args, **kwargs):
        return next(self._responses)

    def bind_tools(self, tools, **kwargs):
        return self


def _hub_state(message: str) -> HubState:
    from app.graph.routing import Route
    return {
        "user_message": message,
        "session_id": "test-session",
        "route": Route.WORKOUT_GENERATE,
        "messages": [],
        "routing_confidence": None,
        "routing_raw": None,
        "clarification": None,
        "subgraph_result": None,
        "explanation": [],
    }


# ---------------------------------------------------------------------------
# Exclusion reasons: knee injury → excluded/loads_joint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_excluded_reason_emitted_for_knee_injury(monkeypatch) -> None:
    """A knee-injury request produces at least one Reason(claim='excluded',
    relation='loads_joint', object='knee') in the explanation."""
    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _SequentialFakeModel([_search_msg(), _build_msg()]),
    )
    # Also patch extract_injuries so message text → ['knee'] deterministically.
    monkeypatch.setattr(
        "app.graph.hub.extract_injuries",
        lambda msg: ["knee"],
    )

    result = await _generator_boundary_node(_hub_state("knee injury workout"))
    reasons: list[Reason] = result.get("explanation", [])

    excluded = [
        r for r in reasons
        if r.claim == "excluded" and r.relation == "loads_joint"
    ]
    assert excluded, (
        "Expected at least one excluded/loads_joint Reason for a knee request; "
        f"got: {[r.model_dump() for r in reasons]}"
    )
    objects = {r.object for r in excluded}
    assert "knee" in objects, (
        f"Expected 'knee' in excluded Reason objects; got {objects}"
    )


# ---------------------------------------------------------------------------
# Pairing reasons: bilateral auto-include → added/bilateral_pair_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_added_reason_emitted_for_bilateral_pair(monkeypatch) -> None:
    """When a bilateral pair is auto-included, a Reason(claim='added',
    relation='bilateral_pair_of') appears in the explanation.

    This test uses a synthetic fixture repo with a resolvable pair, since all
    pairs in the real dataset are dangling.
    """
    from app.data.repository import Exercise

    # Synthetic exercises for the pair.
    _L = "fixture-left-x"
    _R = "fixture-right-x"
    _C = _SAFE_COOLDOWN

    class _PairFixtureRepo:
        def __init__(self) -> None:
            exs = [
                Exercise(
                    id=_L, name="Left Curl",
                    muscle_groups=["biceps"], joints_loaded=["elbow"],
                    movement_patterns=["pull"], equipment_required=[],
                    is_bilateral=False, side=None, priority_tier=1,
                    is_reps=True, is_duration=False, supports_weight=False,
                    estimated_rep_duration=None, bilateral_pair_id=_R,
                ),
                Exercise(
                    id=_R, name="Right Curl",
                    muscle_groups=["biceps"], joints_loaded=["elbow"],
                    movement_patterns=["pull"], equipment_required=[],
                    is_bilateral=False, side=None, priority_tier=1,
                    is_reps=True, is_duration=False, supports_weight=False,
                    estimated_rep_duration=None, bilateral_pair_id=_L,
                ),
                Exercise(
                    id=_C, name="Walking Toe Touches",
                    muscle_groups=["hamstrings"], joints_loaded=["lumbar spine", "shoulder", "hip"],
                    movement_patterns=["hinge"], equipment_required=[],
                    is_bilateral=True, side=None, priority_tier=1,
                    is_reps=True, is_duration=False, supports_weight=False,
                    estimated_rep_duration=None, bilateral_pair_id=None,
                ),
            ]
            self._by_id = {e.id: e for e in exs}
            self._exs = exs

        def search(self, **kwargs): return list(self._exs)
        def get_by_id(self, id): return self._by_id.get(id)
        def contraindicated_ids(self, injuries): return set()
        def bilateral_pair(self, id):
            ex = self._by_id.get(id)
            if ex is None or ex.bilateral_pair_id is None:
                return None
            return self._by_id.get(ex.bilateral_pair_id)
        def all(self): return list(self._exs)

    fixture_repo = _PairFixtureRepo()

    monkeypatch.setattr(
        "app.models.factory.get_model",
        lambda role: _SequentialFakeModel([
            _search_msg(),
            _build_msg(warmup=_L, main=_C, cooldown=_C),
        ]),
    )
    monkeypatch.setattr(
        "app.graph.hub.extract_injuries",
        lambda msg: [],
    )
    # Patch the repo factory used by the boundary node.
    monkeypatch.setattr(
        "app.graph.hub.JsonExerciseRepository",
        lambda: fixture_repo,
    )
    # Patch the generator subgraph builder so it uses the fixture repo.
    import app.agents.generator.graph as gen_graph
    _orig_build = gen_graph.build_generator_subgraph
    monkeypatch.setattr(
        gen_graph,
        "build_generator_subgraph",
        lambda repo=None: _orig_build(repo=fixture_repo),
    )

    result = await _generator_boundary_node(_hub_state("arm workout"))
    reasons: list[Reason] = result.get("explanation", [])

    added = [
        r for r in reasons
        if r.claim == "added" and r.relation == "bilateral_pair_of"
    ]
    assert added, (
        "Expected at least one added/bilateral_pair_of Reason; "
        f"got: {[r.model_dump() for r in reasons]}"
    )
    # The added reason should name the auto-included partner.
    subjects = {r.subject for r in added}
    assert "Right Curl" in subjects, (
        f"Expected 'Right Curl' as added subject; got {subjects}"
    )
