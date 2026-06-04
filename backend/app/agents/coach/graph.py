"""The coach subgraph: answers fitness questions conversationally.

A single answer node invokes the model and writes the reply into CoachState.
The boundary adapter in the hub maps the output onto HubState.subgraph_result.
The system prompt is composed from the shared voice preamble (app.voice) followed
by coach-specific task guidance, so the persona is defined once and reused.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

import app.models.factory as _factory
from app.models.config import MODEL_CONFIG
from app.observability import logging as obs
from app.voice import VOICE_PREAMBLE
from .state import CoachState

# The coach prompt: voice preamble (shared) + task tail (coach-specific).
# ADD voice only — the functional directive ("answer fitness questions…") is
# preserved beneath the preamble so the model knows its task scope.
COACH_SYSTEM_PROMPT = (
    VOICE_PREAMBLE + " "
    "Answer the user's fitness question with a clear recommendation or "
    "explanation. Tie the advice to the outcome they want, and give your "
    "reasoning after your main point — never before."
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
