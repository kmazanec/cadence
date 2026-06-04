"""Routing contract: the closed Route enum, the router's structured-output
decision shape, and the confidence gate that turns a decision into either a
route or a clarifying question.
"""

from __future__ import annotations

from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

# Below this routing confidence the hub asks a clarifying question rather than
# committing to a route.
CONFIDENCE_THRESHOLD: float = 0.7


class Route(str, Enum):
    """The closed set of destinations the hub can dispatch a turn to."""

    COACH = "coach"
    WORKOUT_GENERATE = "workout_generate"
    WORKOUT_LOG = "workout_log"


# The router's system prompt: the single source of truth for how a turn is
# classified. The schema field names alone are not enough — without this, the
# model conflates "a question ABOUT an exercise" with "a request to BUILD a
# session" (e.g. it routed "What muscles does a deadlift work?" to
# workout_generate). The discriminator below is intentionally blunt: the verb
# and intent of the message decide the route, not whether an exercise is named.
ROUTER_SYSTEM_PROMPT: str = (
    "You are the router for Cadence, a fitness assistant. Classify each user "
    "message into exactly one route. Decide on the user's INTENT — what they are "
    "asking you to DO — not merely on which words appear.\n"
    "\n"
    "Routes:\n"
    "- coach: The user is asking a QUESTION or wants information, explanation, "
    "advice, or discussion. This includes any question about an exercise, "
    "muscle, technique, programming, nutrition, or motivation — even when a "
    "specific exercise is named. 'What muscles does X work?', 'How do I improve "
    "my squat?', 'Is soreness normal?' are all coach.\n"
    "- workout_generate: The user is REQUESTING that you create or build a new "
    "workout, session, plan, or routine for them to do. Look for an imperative "
    "to produce something: 'Build me…', 'Give me a 30-minute…', 'Make a leg "
    "day…', 'Design a program…'.\n"
    "- workout_log: The user is REPORTING a workout they have ALREADY done, so "
    "it can be recorded. Look for past-tense completion with sets/reps/weight: "
    "'I just did 3x10 bench at 185', 'Finished my run', 'Logged 5 sets of "
    "squats'.\n"
    "\n"
    "Key discriminator: a QUESTION about an exercise is coach, not "
    "workout_generate. Only route to workout_generate when the user explicitly "
    "asks you to CREATE a workout for them. Asking what a lift does, how it "
    "works, or which muscles it targets is always coach.\n"
    "\n"
    "Examples:\n"
    "- 'What muscles does a deadlift work?' -> coach (a question about an "
    "exercise; the user wants information, not a session built).\n"
    "- 'Build me a 30 min upper body session with dumbbells' -> "
    "workout_generate (an explicit request to create a workout).\n"
    "- 'I just did a 3x10 bench press at 185 lbs' -> workout_log (a completed "
    "workout being reported).\n"
    "\n"
    "Set confidence to your honest probability the route is correct. If the "
    "message is genuinely ambiguous, lower the confidence and provide a "
    "clarification with concrete options."
)


class ClarificationPrompt(BaseModel):
    """A question (with suggested options) offered when intent is ambiguous."""

    question: str
    options: list[str]


class RoutingDecision(BaseModel):
    """The router's structured output for a single turn."""

    route: Route
    confidence: float
    rationale: str
    clarification: ClarificationPrompt | None = None


def decide_route(
    decision: RoutingDecision | None,
) -> tuple[Route | None, ClarificationPrompt | None]:
    """Apply the confidence gate to a routing decision.

    Returns ``(route, None)`` when a decision is present and confident enough;
    otherwise ``(None, clarification)`` — covering both a below-threshold
    decision and a missing decision (e.g. structured output failed).
    """

    if decision is not None and decision.confidence >= CONFIDENCE_THRESHOLD:
        return decision.route, None

    clarification = decision.clarification if decision is not None else None
    if clarification is None:
        clarification = ClarificationPrompt(
            question="Could you tell me a bit more about what you'd like to do?",
            options=[
                "Ask a fitness question",
                "Build me a workout",
                "Log a workout I did",
            ],
        )
    return None, clarification


async def classify(
    message: str,
    model: BaseChatModel,
    prior: list = [],  # noqa: B006 — read-only; never mutated.
) -> RoutingDecision | None:
    """Classify one user turn into a :class:`RoutingDecision`.

    Drives the router's structured output with the routing system prompt, the
    prior thread messages, and the current turn. Returns ``None`` when the model
    fails to produce a parseable decision, leaving the confidence gate
    (:func:`decide_route`) to fall back to a clarifying question.
    """

    structured = model.with_structured_output(RoutingDecision, include_raw=True)
    router_input = (
        [SystemMessage(content=ROUTER_SYSTEM_PROMPT)]
        + list(prior)
        + [HumanMessage(content=message)]
    )
    raw_result: dict = await structured.ainvoke(router_input)
    parsed = raw_result.get("parsed")
    return parsed if isinstance(parsed, RoutingDecision) else None
