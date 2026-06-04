"""Contract-shape tests: lock the frozen signatures and prove the exhaustive
consumers stay total over their closed unions/vocabularies.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.agents.coach.state import CoachState
from app.agents.generator.schemas import Block, WorkoutPayload
from app.agents.generator.state import GeneratorState
from app.agents.generator.tools import BuildWorkoutInput, SearchExercisesInput
from app.agents.logger.state import LoggerState
from app.api.schemas import ChatRequest, ChatResponse, LogPayload
from app.api.streaming import (
    ClarificationEvent,
    DoneEvent,
    ErrorEvent,
    ExplanationEvent,
    RouteEvent,
    SSEEvent,
    StructuredEvent,
    TokenEvent,
    encode_sse,
)
from app.data.json_repository import JsonExerciseRepository
from app.data.log_repository import LogEntry, get_log_repository
from app.data.repository import Exercise, ExerciseRepository
from app.data.sqlite_log_repository import SqliteLogRepository
from app.graph.explanation import Reason
from app.graph.response_assembly import assemble_response
from app.graph.routing import (
    CONFIDENCE_THRESHOLD,
    ClarificationPrompt,
    Route,
    RoutingDecision,
    decide_route,
)
from app.graph.state import (
    CoachResult,
    GeneratorResult,
    HubState,
    RecoveryInfo,
    WorkoutLogResult,
)
from app.models.config import MODEL_CONFIG, STRUCTURED_OUTPUT_ROLES
from app.models.registry import ModelCapability, validate_model_config


# --- Exercise repository -------------------------------------------------


def test_json_repository_loads_fifty_typed_models() -> None:
    repo = JsonExerciseRepository()
    everything = repo.all()
    assert len(everything) == 50
    assert all(isinstance(e, Exercise) for e in everything)
    assert isinstance(repo, ExerciseRepository)


def test_exercise_has_all_fourteen_fields() -> None:
    assert set(Exercise.model_fields) == {
        "id",
        "name",
        "muscle_groups",
        "joints_loaded",
        "movement_patterns",
        "equipment_required",
        "is_bilateral",
        "side",
        "priority_tier",
        "is_reps",
        "is_duration",
        "supports_weight",
        "estimated_rep_duration",
        "bilateral_pair_id",
    }


def test_repository_methods_are_total() -> None:
    repo = JsonExerciseRepository()
    one = repo.all()[0]
    assert repo.get_by_id(one.id) == one
    assert repo.get_by_id("missing") is None
    assert isinstance(repo.search(muscle_groups=["chest"]), list)
    assert isinstance(repo.contraindicated_ids(["shoulder"]), set)
    # bilateral_pair returns None for an exercise with no resolvable pair.
    assert repo.bilateral_pair("missing") is None


# --- Injury / bilateral surface signatures -------------------------------


def test_validate_workout_accepts_injuries_and_reports_contraindicated() -> None:
    from app.agents.generator.output_gate import GateResult, validate_workout

    repo = JsonExerciseRepository()
    empty = WorkoutPayload(blocks=[])
    # injuries defaults to None — existing callers keep working unchanged.
    result = validate_workout(empty, repo)
    assert isinstance(result, GateResult)
    assert result.contraindicated_ids == set()
    # Passing injuries is accepted and a clean payload still validates.
    result_with_injury = validate_workout(empty, repo, injuries=["shoulder"])
    assert result_with_injury.valid is True
    assert result_with_injury.contraindicated_ids == set()


def test_build_workout_accepts_injuries_param() -> None:
    import inspect

    from app.agents.generator.build_workout import build_workout

    params = inspect.signature(build_workout).parameters
    assert "injuries" in params
    assert params["injuries"].default is None


def test_execute_search_accepts_injuries_param() -> None:
    import inspect

    from app.agents.generator.graph import _execute_search

    params = inspect.signature(_execute_search).parameters
    assert "injuries" in params
    assert params["injuries"].default is None


def test_extract_injuries_is_total() -> None:
    from app.agents.generator.injury_extraction import extract_injuries

    result = extract_injuries("my shoulder hurts")
    assert isinstance(result, list)
    assert all(isinstance(term, str) for term in result)


def test_reason_vocabulary_covers_injury_and_pairing() -> None:
    # The closed vocabulary must admit the exclusion and pairing triples the
    # generator boundary emits.
    excluded = Reason(
        claim="excluded", subject="Barbell Press", relation="loads_joint", object="shoulder"
    )
    added = Reason(
        claim="added", subject="Single-Arm Row", relation="bilateral_pair_of", object="row-left"
    )
    assert excluded.claim == "excluded"
    assert added.relation == "bilateral_pair_of"


# --- Log repository ------------------------------------------------------


def test_log_repository_round_trip(tmp_path) -> None:
    repo = SqliteLogRepository(tmp_path / "log.db")
    entry = LogEntry(
        session_id="s1",
        exercise_id=None,
        raw_name="bench press",
        sets=3,
        reps=10,
        weight=60.0,
        unmatched=True,
        logged_at=datetime.now(timezone.utc),
    )
    repo.append([entry], "s1")
    fetched = repo.for_session("s1")
    assert len(fetched) == 1
    assert fetched[0].raw_name == "bench press"
    assert fetched[0].unmatched is True


def test_log_repository_factory_branches(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sqlite_repo = get_log_repository()
    assert isinstance(sqlite_repo, SqliteLogRepository)


# --- Routing -------------------------------------------------------------


def test_route_enum_is_closed() -> None:
    assert {r.name for r in Route} == {"COACH", "WORKOUT_GENERATE", "WORKOUT_LOG"}


def test_decide_route_total_over_every_route_above_threshold() -> None:
    for route in Route:
        decision = RoutingDecision(route=route, confidence=0.9, rationale="clear")
        resolved, clarification = decide_route(decision)
        assert resolved is route
        assert clarification is None


def test_decide_route_below_threshold_clarifies() -> None:
    decision = RoutingDecision(
        route=Route.COACH,
        confidence=CONFIDENCE_THRESHOLD - 0.1,
        rationale="unsure",
        clarification=ClarificationPrompt(question="Which?", options=["a", "b"]),
    )
    resolved, clarification = decide_route(decision)
    assert resolved is None
    assert clarification is not None


def test_decide_route_handles_missing_decision() -> None:
    resolved, clarification = decide_route(None)
    assert resolved is None
    assert isinstance(clarification, ClarificationPrompt)


# --- Model registry ------------------------------------------------------


def test_default_config_passes_validation() -> None:
    validate_model_config()


def test_logger_is_a_structured_output_role() -> None:
    assert "logger" in STRUCTURED_OUTPUT_ROLES


def test_validate_rejects_unknown_model() -> None:
    bad = dict(MODEL_CONFIG)
    bad["router"] = "unknown/model"
    with pytest.raises(ValueError):
        validate_model_config(bad)


def test_validate_rejects_incapable_model() -> None:
    from app.models import registry

    registry.REGISTRY["test/incapable"] = ModelCapability(
        supports_structured_output=False,
        supports_tools=False,
        context_window=8000,
        notes="for tests",
    )
    bad = dict(MODEL_CONFIG)
    bad["generator"] = "test/incapable"
    with pytest.raises(ValueError):
        validate_model_config(bad)
    del registry.REGISTRY["test/incapable"]


# --- Response assembly: exhaustive over the SubgraphResult union ---------


def _base_state(**overrides) -> HubState:
    state: HubState = {
        "session_id": "s1",
        "messages": [],
        "user_message": "hi",
        "route": None,
        "routing_confidence": None,
        "routing_raw": None,
        "subgraph_result": None,
        "explanation": [],
        "clarification": None,
        "error": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


def test_assemble_coach_arm() -> None:
    state = _base_state(
        route=Route.COACH,
        subgraph_result=CoachResult(answer="Drink water."),
    )
    response = assemble_response(state)
    assert response.reply_text == "Drink water."
    assert response.structured is None


def test_assemble_workout_arm() -> None:
    workout = WorkoutPayload(
        blocks=[Block(name="main", exercises=[])],
    )
    state = _base_state(
        route=Route.WORKOUT_GENERATE,
        subgraph_result=GeneratorResult(workout=workout, selected_exercise_ids=["x"]),
    )
    response = assemble_response(state)
    assert isinstance(response.structured, WorkoutPayload)


def test_assemble_log_arm() -> None:
    entry = LogEntry(
        session_id="s1",
        exercise_id="x",
        raw_name="squat",
        unmatched=False,
        logged_at=datetime.now(timezone.utc),
    )
    state = _base_state(
        route=Route.WORKOUT_LOG,
        subgraph_result=WorkoutLogResult(entries=[entry], session_id="s1"),
    )
    response = assemble_response(state)
    assert isinstance(response.structured, LogPayload)
    assert response.structured.entries[0].raw_name == "squat"


def test_assemble_clarification_no_subgraph() -> None:
    state = _base_state(
        clarification=ClarificationPrompt(question="Which?", options=["a", "b"]),
    )
    response = assemble_response(state)
    assert response.route is None
    assert response.structured is None
    assert response.clarification is not None


# --- SSE envelope: exhaustive over all six variants ----------------------


def test_encode_every_sse_variant() -> None:
    workout = WorkoutPayload(blocks=[])
    reason = Reason(claim="note", subject="coach", relation="name_match")
    events: list[SSEEvent] = [
        RouteEvent(route=Route.COACH),
        TokenEvent(text="hi"),
        StructuredEvent(payload=workout),
        ExplanationEvent(reasons=[reason]),
        ClarificationEvent(question="Which?", options=["a", "b"]),
        DoneEvent(),
        ErrorEvent(message="something went wrong"),
    ]
    for event in events:
        frame = encode_sse(event)
        assert frame.startswith("data: ")
        assert frame.endswith("\n\n")


def test_error_event_carries_no_traceback() -> None:
    event = ErrorEvent(message="We hit a snag — please try again.")
    assert "Traceback" not in event.message


# --- Reason vocabulary ---------------------------------------------------


def test_reason_closed_vocabularies() -> None:
    r = Reason(
        claim="included",
        subject="Goblet Squat",
        relation="matches_target",
        object="quads",
        detail=None,
    )
    assert r.claim == "included"
    with pytest.raises(Exception):
        Reason(claim="invented", subject="x", relation="name_match")
    with pytest.raises(Exception):
        Reason(claim="note", subject="x", relation="invented_relation")


# --- Chat envelope width -------------------------------------------------


def test_chat_response_is_wide() -> None:
    assert set(ChatResponse.model_fields) == {
        "route",
        "reply_text",
        "structured",
        "explanation",
        "clarification",
    }
    resp = ChatResponse(reply_text="hi")
    assert resp.explanation == []
    assert resp.route is None


def test_chat_request_shape() -> None:
    req = ChatRequest(message="hi")
    assert req.session_id is None


# --- Generator tool input schemas ----------------------------------------


def test_generator_input_schemas_are_field_described() -> None:
    for field in SearchExercisesInput.model_fields.values():
        assert field.description
    for field in BuildWorkoutInput.model_fields.values():
        assert field.description


def test_recovery_info_default_retry_count() -> None:
    info = RecoveryInfo(message="caught", recovered=True)
    assert info.retry_count == 0


# --- Subgraph states are isolated TypedDicts -----------------------------


def test_subgraph_states_exist() -> None:
    assert "answer" in CoachState.__annotations__
    assert "retry_count" in GeneratorState.__annotations__
    assert "retry_count" in LoggerState.__annotations__


# --- Model factory seam --------------------------------------------------


def test_get_model_seam_is_overridable(fake_get_model) -> None:
    # The fixture monkeypatches the factory; import-site call returns the stub.
    from app.models import factory

    model = factory.get_model("coach")
    chunks = list(model.stream("hi"))
    assert len(chunks) >= 1
