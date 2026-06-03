"""The coach subgraph: answers fitness questions conversationally.

A single answer node invokes the model and writes the reply into CoachState.
The boundary adapter in the hub maps the output onto HubState.subgraph_result.
The system prompt applies the brand voice guidelines: conversational, direct,
confident, partnership-oriented, and never clinical or robotic.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

import app.models.factory as _factory
from app.models.config import MODEL_CONFIG
from app.observability import logging as obs
from .state import CoachState

# Voice guidelines from BRAND.md: conversational, confident, partnership-
# oriented, results-focused; never clinical, hedged, or robotic.
COACH_SYSTEM_PROMPT = (
    "You are Cadence, a knowledgeable and supportive fitness training partner. "
    "Speak conversationally and directly — talk to the person, not at them. "
    "Be confident: give a clear recommendation or answer, then your reasoning. "
    "Be partnership-oriented: use 'let's', 'we', and 'you've got this' naturally. "
    "Be results-focused: tie advice to the outcome the person wants. "
    "Never sound clinical, robotic, or hedged. "
    "Do not bury your answer under disclaimers or dump raw data without framing it."
)


async def _answer_node(state: CoachState) -> dict:
    """Invoke the coach model and return the answer."""
    model = _factory.get_model("coach")
    messages = [
        SystemMessage(content=COACH_SYSTEM_PROMPT),
        *state.get("messages", []),
        HumanMessage(content=state["user_message"]),
    ]
    with obs.llm_call("coach", MODEL_CONFIG["coach"]):
        response = await model.ainvoke(messages)
    return {"answer": response.content}


def build_coach_subgraph() -> StateGraph:
    """Compile and return the coach subgraph."""
    builder = StateGraph(CoachState)
    builder.add_node("coach_answer", _answer_node)
    builder.set_entry_point("coach_answer")
    builder.add_edge("coach_answer", END)
    return builder.compile()
