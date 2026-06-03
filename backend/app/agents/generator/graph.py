"""Generator subgraph: search exercises and assemble a workout.

The generator runs a model-driven tool loop within a single graph node, then
validates the assembled workout through the output gate as a separate node.

Flow:
  generate (tool loop internally) -> gate -> END or generate (on gate failure)

The tool loop's own message history lives as a local variable within the generate
node. GeneratorState carries a read-only ``messages`` key for prior conversation
context (supplied by the hub boundary) so follow-up requests like 'make it
shorter' can resolve against the prior workout. The generator never writes back
to this key — ADR-004 isolated-state: the hub remains the single owner of the
conversation thread.

ADR-006: retries are bounded by state.retry_count < RETRY_CEILING; no RetryPolicy.
ADR-002: the assembled workout is stored on state, never inferred from deltas.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

import app.models.factory as _factory
from app.agents.generator.build_workout import build_workout
from app.agents.generator.output_gate import validate_workout
from app.agents.generator.schemas import Prescription, WorkoutPayload
from app.agents.generator.state import RETRY_CEILING, GeneratorState
from app.agents.generator.tools import (
    BuildWorkoutInput,
    SearchExercisesInput,
    build_workout_tool,
    search_exercises_tool,
)
from app.data.repository import ExerciseRepository

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a workout generator. Use the search_exercises tool to find exercises "
    "that match the user's request, then use the build_workout tool to assemble a "
    "complete warmup/main/cooldown workout. Every exercise you include must come "
    "from the search_exercises results — never invent exercise IDs."
)

# Maximum tool-call rounds per generate invocation to prevent runaway loops.
_TOOL_LOOP_MAX = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_message(tool_call_id: str, content: str) -> ToolMessage:
    return ToolMessage(tool_call_id=tool_call_id, content=content)


def _execute_search(
    args: dict,
    repo: ExerciseRepository,
    injuries: list[str] | None = None,
) -> str:
    """Execute search_exercises and return a JSON string of results.

    When *injuries* is supplied, contraindicated exercises are dropped from the
    results before serialising so the model never sees an unsafe option.
    """
    try:
        params = SearchExercisesInput.model_validate(args)
    except Exception as exc:
        return json.dumps({"error": f"Invalid search parameters: {exc}"})

    results = repo.search(
        muscle_groups=params.muscle_groups,
        equipment=params.equipment,
        movement_patterns=params.movement_patterns,
    )
    if injuries:
        blocked = repo.contraindicated_ids(injuries)
        results = [ex for ex in results if ex.id not in blocked]
    return json.dumps([
        {
            "id": ex.id,
            "name": ex.name,
            "muscle_groups": ex.muscle_groups,
            "equipment_required": ex.equipment_required,
            "is_reps": ex.is_reps,
            "is_duration": ex.is_duration,
            "supports_weight": ex.supports_weight,
        }
        for ex in results
    ])


def _execute_build_workout(
    args: dict,
    repo: ExerciseRepository,
    injuries: list[str] | None = None,
) -> tuple[WorkoutPayload | None, str, list[str]]:
    """Execute build_workout and return (payload, message, selected_ids).

    When *injuries* is supplied, bilateral auto-pairing in build_workout will
    skip any partner that is contraindicated.
    """
    try:
        params = BuildWorkoutInput.model_validate(args)
    except Exception as exc:
        return None, f"Invalid build_workout parameters: {exc}", []

    all_ids = list(params.warmup_ids) + list(params.main_ids) + list(params.cooldown_ids)

    try:
        prescriptions: list[Prescription] = list(params.prescriptions)
        payload = build_workout(
            warmup_ids=list(params.warmup_ids),
            main_ids=list(params.main_ids),
            cooldown_ids=list(params.cooldown_ids),
            repo=repo,
            prescriptions=prescriptions,
            injuries=injuries,
        )
    except ValueError as exc:
        return None, str(exc), []

    return payload, "Workout assembled successfully.", all_ids


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def _make_generate_node(repo: ExerciseRepository):
    """Return an async generate node that runs the full tool loop internally.

    The node drives search_exercises and build_workout calls until the model
    stops issuing tool calls or the loop limit is reached. The assembled workout
    (if produced) is stored in the returned state dict.
    """

    async def _generate_node(state: GeneratorState) -> dict:
        model = _factory.get_model("generator")

        # Pull the active injuries from state so both the search pre-filter and
        # the build assembly can apply the contraindication exclusion.
        injuries: list[str] = state.get("injuries") or []

        # Bind tools so the model knows the available tool signatures.
        # Use the StructuredTool wrappers (not the bare Pydantic classes) so
        # that LangChain serialises tool names as "search_exercises" and
        # "build_workout" — matching the dispatch keys below.
        tools = [search_exercises_tool, build_workout_tool]
        try:
            bound_model = model.bind_tools(tools)
        except (AttributeError, NotImplementedError):
            bound_model = model

        # Seed the tool-loop with prior conversation context (if any) so the
        # model can adjust a prior workout. Prior messages come from the hub
        # thread; the current request lands as the final HumanMessage. On retry
        # we restart from the same seed — no prior tool history — so the model
        # gets a clean slate to try a different exercise selection.
        prior_context = list(state.get("messages", []))
        messages: list = [
            SystemMessage(content=_SYSTEM_PROMPT),
            *prior_context,
            HumanMessage(content=state["user_message"]),
        ]

        assembled_payload: WorkoutPayload | None = None
        selected_ids: list[str] = []

        for _ in range(_TOOL_LOOP_MAX):
            response = await bound_model.ainvoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # Model finished without any tool calls.
                break

            for tc in tool_calls:
                name: str = tc["name"]
                args: dict = tc["args"]
                call_id: str = tc.get("id", "unknown")

                if name == "search_exercises":
                    # Pass injuries so contraindicated candidates are dropped
                    # before the model ever sees them (hard pre-filter layer).
                    result_str = _execute_search(args, repo, injuries=injuries)
                    messages.append(_tool_message(call_id, result_str))

                elif name == "build_workout":
                    # Pass injuries so bilateral auto-pairing can skip
                    # contraindicated partners.
                    payload, msg, ids = _execute_build_workout(args, repo, injuries=injuries)
                    if payload is not None:
                        assembled_payload = payload
                        selected_ids = ids
                    messages.append(_tool_message(call_id, msg))

                else:
                    messages.append(_tool_message(call_id, f"Unknown tool: {name!r}"))

            if assembled_payload is not None:
                # Workout assembled; stop the loop so the gate can validate it.
                break

        update: dict = {
            "selected_exercise_ids": selected_ids,
        }
        if assembled_payload is not None:
            update["workout"] = assembled_payload

        return update

    return _generate_node


def _make_gate_node(repo: ExerciseRepository):
    """Return an async output-gate node that validates the assembled workout.

    Passes the active injuries into validate_workout so contraindicated exercises
    are caught even if they slipped through the search pre-filter (defense-in-depth,
    see ADR-009).
    """

    async def _gate_node(state: GeneratorState) -> dict:
        payload: WorkoutPayload | None = state.get("workout")

        if payload is None:
            retry = (state.get("retry_count") or 0) + 1
            return {"retry_count": retry}

        injuries: list[str] = state.get("injuries") or []
        gate = validate_workout(payload, repo, injuries=injuries)
        if gate.valid:
            return {}

        # Gate failed: clear workout and increment retry.
        retry = (state.get("retry_count") or 0) + 1
        return {"workout": None, "retry_count": retry}

    return _gate_node


# ---------------------------------------------------------------------------
# Edge conditions
# ---------------------------------------------------------------------------


def _route_after_gate(
    state: GeneratorState,
) -> Literal["generate", "__end__"]:
    """If the gate failed and retries remain, retry; else END."""
    if state.get("workout") is not None:
        return END
    if (state.get("retry_count") or 0) < RETRY_CEILING:
        return "generate"
    return END


# ---------------------------------------------------------------------------
# Subgraph builder
# ---------------------------------------------------------------------------


def build_generator_subgraph(
    repo: ExerciseRepository | None = None,
) -> Any:
    """Build and compile the generator StateGraph.

    ``repo`` defaults to :class:`~app.data.json_repository.JsonExerciseRepository`
    if not supplied.
    """
    from app.data.json_repository import JsonExerciseRepository

    if repo is None:
        repo = JsonExerciseRepository()

    generate_node = _make_generate_node(repo)
    gate_node = _make_gate_node(repo)

    builder = StateGraph(GeneratorState)
    builder.add_node("generate", generate_node)
    builder.add_node("gate", gate_node)

    builder.set_entry_point("generate")
    builder.add_edge("generate", "gate")
    builder.add_conditional_edges(
        "gate",
        _route_after_gate,
        {"generate": "generate", END: END},
    )

    return builder.compile()
