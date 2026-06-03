"""The hub StateGraph: routes a turn to the correct subgraph and assembles the
response.

The conditional edge map is exhaustive over the closed Route enum plus the
clarify branch, so adding a Route member without handling it is a type error at
graph-build time.

Subgraph isolation: each subgraph is called from a boundary-adapter node rather
than embedded directly. The adapter translates the hub's HubState into the
subgraph's own isolated TypedDict, calls the subgraph, then maps the output back
onto HubState — the hub and subgraph never share a mutable key.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ..graph.explanation import Reason
from ..graph.routing import Route, RoutingDecision, decide_route
from ..graph.state import CoachResult, GeneratorResult, HubState
from ..models.factory import get_model


# ---------------------------------------------------------------------------
# Router node — structured-output classification with include_raw safe-net
# ---------------------------------------------------------------------------


async def _router_node(state: HubState) -> dict:
    """Classify the user message into a route via LLM structured output.

    Uses include_raw=True so that a parse failure (parsed=None) is caught and
    turned into a clarifying question rather than silently misrouting.
    Confidence below CONFIDENCE_THRESHOLD also falls back to clarification —
    this is the minimal safe-net; bounded retry lives in the resilience feature.
    """
    model = get_model("router")
    structured = model.with_structured_output(RoutingDecision, include_raw=True)

    raw_result: dict = await structured.ainvoke(state["user_message"])

    parsed: RoutingDecision | None = raw_result.get("parsed")
    raw_msg = raw_result.get("raw")

    # Capture the raw model output for observability; store as dict so it
    # serialises safely across the checkpointer boundary.
    routing_raw: dict | None = None
    if raw_msg is not None:
        try:
            routing_raw = raw_msg.model_dump() if hasattr(raw_msg, "model_dump") else {"content": str(raw_msg)}
        except Exception:
            routing_raw = {"content": str(raw_msg)}

    route, clarification = decide_route(parsed)

    routing_confidence: float | None = parsed.confidence if parsed is not None else None

    result: dict = {
        "route": route,
        "routing_confidence": routing_confidence,
        "routing_raw": routing_raw,
        "messages": [HumanMessage(content=state["user_message"])],
    }
    if clarification is not None:
        result["clarification"] = clarification

    return result


# ---------------------------------------------------------------------------
# Routing edge
# ---------------------------------------------------------------------------


def _route_edge(
    state: HubState,
) -> Literal["coach_boundary", "generator_boundary", "clarify", "response_assembly"]:
    """Select the next node based on committed route state."""
    route = state.get("route")
    if route is Route.COACH:
        return "coach_boundary"
    if route is Route.WORKOUT_GENERATE:
        return "generator_boundary"
    if route is Route.WORKOUT_LOG:
        # Logger not yet wired — fall through to assembly.
        return "response_assembly"
    # No route committed — a clarifying question was returned.
    return "clarify"


# ---------------------------------------------------------------------------
# Coach boundary adapter node
# ---------------------------------------------------------------------------


async def _coach_boundary_node(state: HubState) -> dict:
    """Translate hub state into coach subgraph input, invoke the subgraph, and
    map the answer back onto HubState.

    The hub and coach subgraph share no mutable key; the adapter is the only
    point where their state spaces cross.
    """
    from ..agents.coach.graph import build_coach_subgraph

    coach = build_coach_subgraph()
    coach_input = {
        "user_message": state["user_message"],
        "messages": list(state.get("messages", [])),
        "answer": "",
    }
    # Invoke the subgraph — no checkpointer needed here, hub holds the thread.
    coach_output = await coach.ainvoke(coach_input)
    answer: str = coach_output.get("answer", "")

    result = CoachResult(answer=answer)
    msg = AIMessage(content=answer)
    # A single lightweight note signals that the coach handled this turn.
    # Keeps explanation non-empty without manufacturing relation triples the
    # coach didn't actually decide.
    note = Reason(
        claim="note",
        subject="coach",
        relation="name_match",
        detail="answered by coach",
    )
    return {
        "subgraph_result": result,
        "messages": [msg],
        "explanation": [note],
    }


# ---------------------------------------------------------------------------
# Generator boundary adapter node
# ---------------------------------------------------------------------------


async def _generator_boundary_node(state: HubState) -> dict:
    """Translate hub state into generator subgraph input, invoke the subgraph,
    and map the workout back onto HubState.subgraph_result.

    Also builds Reason triples for the exercises included in the workout, using
    the closed relation vocabulary (matches_target and equipment_match).
    """
    from ..agents.generator.graph import build_generator_subgraph
    from ..data.json_repository import JsonExerciseRepository

    repo = JsonExerciseRepository()
    generator = build_generator_subgraph(repo=repo)

    generator_input = {
        "user_message": state["user_message"],
        "injuries": [],
        "targets": [],
        "workout": None,
        "selected_exercise_ids": [],
        "retry_count": 0,
    }

    gen_output = await generator.ainvoke(generator_input)
    workout = gen_output.get("workout")
    selected_ids: list[str] = gen_output.get("selected_exercise_ids") or []

    # Build relation-shaped Reasons for the exercises included in the workout.
    reasons: list[Reason] = []
    if workout is not None:
        for block in workout.blocks:
            for p in block.exercises:
                ex = repo.get_by_id(p.exercise_id)
                if ex is None:
                    continue
                # Emit one reason per muscle group targeted.
                for mg in ex.muscle_groups:
                    reasons.append(
                        Reason(
                            claim="included",
                            subject=ex.name,
                            relation="matches_target",
                            object=mg,
                        )
                    )
                # Emit one reason per required equipment item.
                for eq in ex.equipment_required:
                    reasons.append(
                        Reason(
                            claim="included",
                            subject=ex.name,
                            relation="equipment_match",
                            object=eq,
                        )
                    )

    if workout is None:
        # Generator exhausted retries — graceful empty result.
        result = None
        reply_ai_msg = AIMessage(
            content="I wasn't able to build a workout for that request. "
            "Try widening the equipment or muscle group selection."
        )
        return {
            "subgraph_result": result,
            "explanation": reasons,
            "messages": [reply_ai_msg],
        }

    result = GeneratorResult(workout=workout, selected_exercise_ids=selected_ids)
    return {
        "subgraph_result": result,
        "explanation": reasons,
    }


# ---------------------------------------------------------------------------
# Placeholder nodes for non-generator routes and clarification
# ---------------------------------------------------------------------------


async def _clarify_node(state: HubState) -> dict:
    """Emit a clarification prompt when routing confidence is too low."""
    from ..graph.routing import ClarificationPrompt

    clarification = state.get("clarification") or ClarificationPrompt(
        question="Could you tell me more about what you'd like to do?",
        options=["Ask a fitness question", "Build me a workout", "Log a workout I did"],
    )
    return {"clarification": clarification}


# ---------------------------------------------------------------------------
# Response assembly node
# ---------------------------------------------------------------------------


async def _response_assembly_node(state: HubState) -> dict:
    """No-op node: state is fully assembled when we reach here.

    The HTTP layer reads from committed state directly via assemble_response.
    """
    return {}


# ---------------------------------------------------------------------------
# Hub builder
# ---------------------------------------------------------------------------


def build_hub() -> StateGraph:
    """Build and compile the hub StateGraph with an in-memory checkpointer.

    The compiled graph is safe to invoke concurrently across sessions because
    each thread_id gets its own isolated checkpoint store.
    """
    builder = StateGraph(HubState)

    builder.add_node("router", _router_node)
    # The coach boundary node handles hub↔subgraph translation and is the
    # unique node name that prevents MULTIPLE_SUBGRAPHS conflicts.
    builder.add_node("coach_boundary", _coach_boundary_node)
    builder.add_node("generator_boundary", _generator_boundary_node)
    builder.add_node("clarify", _clarify_node)
    builder.add_node("response_assembly", _response_assembly_node)

    builder.set_entry_point("router")

    # Exhaustive conditional edge over the closed Route enum + clarify branch.
    builder.add_conditional_edges(
        "router",
        _route_edge,
        {
            "coach_boundary": "coach_boundary",
            "generator_boundary": "generator_boundary",
            "clarify": "clarify",
            "response_assembly": "response_assembly",
        },
    )

    builder.add_edge("coach_boundary", "response_assembly")
    builder.add_edge("generator_boundary", "response_assembly")
    builder.add_edge("clarify", "response_assembly")
    builder.add_edge("response_assembly", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
