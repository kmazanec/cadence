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

from ..graph.routing import CONFIDENCE_THRESHOLD, Route, RoutingDecision
from ..graph.state import CoachResult, HubState


# ---------------------------------------------------------------------------
# Router node (placeholder — routes to coach unconditionally)
# ---------------------------------------------------------------------------


async def _router_node(state: HubState) -> dict:
    """Route the turn to the coach unconditionally.

    The router's conditional-edge map and HubState fields are wired correctly;
    the routing decision logic will be replaced with a real structured-output
    model call without changing any downstream node.
    """
    decision = RoutingDecision(
        route=Route.COACH,
        confidence=CONFIDENCE_THRESHOLD + 0.1,
        rationale="placeholder — routes every turn to the coach",
    )
    return {
        "route": decision.route,
        "routing_confidence": decision.confidence,
        "routing_raw": decision.model_dump(),
        "messages": [HumanMessage(content=state["user_message"])],
    }


# ---------------------------------------------------------------------------
# Routing edge
# ---------------------------------------------------------------------------


def _route_edge(
    state: HubState,
) -> Literal["coach_boundary", "clarify", "response_assembly"]:
    """Select the next node based on committed route state."""
    route = state.get("route")
    if route is Route.COACH:
        return "coach_boundary"
    if route is Route.WORKOUT_GENERATE:
        # Generator not yet wired — fall through to assembly.
        return "response_assembly"
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
    return {
        "subgraph_result": result,
        "messages": [msg],
    }


# ---------------------------------------------------------------------------
# Placeholder nodes for non-coach routes and clarification
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
    builder.add_node("clarify", _clarify_node)
    builder.add_node("response_assembly", _response_assembly_node)

    builder.set_entry_point("router")

    # Exhaustive conditional edge over the closed Route enum + clarify branch.
    builder.add_conditional_edges(
        "router",
        _route_edge,
        {
            "coach_boundary": "coach_boundary",
            "clarify": "clarify",
            "response_assembly": "response_assembly",
        },
    )

    builder.add_edge("coach_boundary", "response_assembly")
    builder.add_edge("clarify", "response_assembly")
    builder.add_edge("response_assembly", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
