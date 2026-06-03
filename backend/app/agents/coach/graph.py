"""The coach subgraph: answers fitness questions conversationally.

A single answer node invokes the model and writes the reply into CoachState.
The boundary adapter in the hub maps the output onto HubState.subgraph_result.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

import app.models.factory as _factory
from .state import CoachState

_SYSTEM_PROMPT = (
    "You are Cadence, a knowledgeable and supportive fitness coach. "
    "Answer the user's question clearly and concisely. "
    "Be conversational, confident, and direct — like a training partner."
)


async def _answer_node(state: CoachState) -> dict:
    """Invoke the coach model and return the answer."""
    model = _factory.get_model("coach")
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        *state.get("messages", []),
        HumanMessage(content=state["user_message"]),
    ]
    response = await model.ainvoke(messages)
    return {"answer": response.content}


def build_coach_subgraph() -> StateGraph:
    """Compile and return the coach subgraph."""
    builder = StateGraph(CoachState)
    builder.add_node("coach_answer", _answer_node)
    builder.set_entry_point("coach_answer")
    builder.add_edge("coach_answer", END)
    return builder.compile()
