"""Labeled routing cases for the split-test harness.

Each case captures:
- ``message``: the raw user utterance to classify.
- ``expected_route``: the ``Route`` the classifier must emit above the confidence
  threshold; ``None`` for cases where a clarification is the correct outcome.
- ``ambiguous``: when ``True`` the case tests the clarify-not-dispatch path.
  The harness scores an ambiguous case as correct when the classifier returns
  ``None`` (i.e. decide_route triggered clarification, not dispatch).

Covers the three route types with both clear-intent and ambiguous turns.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.routing import Route


@dataclass(frozen=True)
class RoutingCase:
    """A single labeled turn for routing evaluation."""

    message: str
    expected_route: Route | None  # None means clarify is the correct outcome
    ambiguous: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Clear-intent cases — the classifier should hit these above CONFIDENCE_THRESHOLD
# ---------------------------------------------------------------------------

CASES: list[RoutingCase] = [
    # Coach: information / question intent
    RoutingCase(
        message="What muscles does a deadlift work?",
        expected_route=Route.COACH,
        description="canonical-coach: question about an exercise",
    ),
    RoutingCase(
        message="How do I improve my squat form?",
        expected_route=Route.COACH,
        description="coach: technique question",
    ),
    RoutingCase(
        message="Is muscle soreness the day after a workout normal?",
        expected_route=Route.COACH,
        description="coach: general fitness question",
    ),
    RoutingCase(
        message="What's the difference between a Romanian deadlift and a conventional deadlift?",
        expected_route=Route.COACH,
        description="coach: exercise comparison",
    ),
    # Workout generate: imperative create intent
    RoutingCase(
        message="Build me a 30 minute upper body session with dumbbells",
        expected_route=Route.WORKOUT_GENERATE,
        description="canonical-generate: explicit create request",
    ),
    RoutingCase(
        message="Give me a leg day routine",
        expected_route=Route.WORKOUT_GENERATE,
        description="generate: routine request",
    ),
    RoutingCase(
        message="Design a 5-day full body program for a beginner",
        expected_route=Route.WORKOUT_GENERATE,
        description="generate: program design request",
    ),
    # Workout log: past-tense completion intent
    RoutingCase(
        message="I just did 3x10 bench press at 185 lbs",
        expected_route=Route.WORKOUT_LOG,
        description="canonical-log: past-tense sets/reps/weight",
    ),
    RoutingCase(
        message="Finished my run — 5 km in 28 minutes",
        expected_route=Route.WORKOUT_LOG,
        description="log: completed cardio",
    ),
    RoutingCase(
        message="Just wrapped up back day: 4x8 deadlift at 225, 3x10 rows at 135",
        expected_route=Route.WORKOUT_LOG,
        description="log: multi-exercise session",
    ),
    # ---------------------------------------------------------------------------
    # Ambiguous cases — either clarify OR the expected route is acceptable
    # ---------------------------------------------------------------------------
    RoutingCase(
        message="Bench press",
        expected_route=None,
        ambiguous=True,
        description="ambiguous: single exercise name, no verb or intent",
    ),
    RoutingCase(
        message="Deadlift?",
        expected_route=None,
        ambiguous=True,
        description="ambiguous: bare question mark, could be info or log",
    ),
]
