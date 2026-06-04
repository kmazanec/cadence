"""Smoke tests: the eval harness runs end-to-end against a fake model and
produces a well-formed report, without any network calls.

Why here: the harness must be exercisable in CI with a deterministic stub so
the split-test story is provable — not merely described. Real-model runs are
opt-in (see the ``live`` marker) and require OPENROUTER_API_KEY.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from app.graph.routing import Route, RoutingDecision
from eval.cases import CASES, RoutingCase
from eval.harness import _print_report, run_eval


# ---------------------------------------------------------------------------
# Fake model fixture that always returns the expected route at high confidence,
# giving 100 % accuracy so the report values are deterministic.
# ---------------------------------------------------------------------------


def _make_fake_routing_model(route: Route = Route.COACH) -> "FakeDeterministicRouter":
    """Return a fake model that emits ``route`` at 0.95 confidence for every message."""
    from tests.conftest import FakeStructuredOutputModel

    return FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=route,
            confidence=0.95,
            rationale="fake — always correct",
        )
    )


class _PerCaseFakeRouter:
    """Minimal model-lookalike that returns the expected route per case.

    Not a full BaseChatModel; only ``with_structured_output`` is called by
    ``classify``.  We wrap it in a RunnableLambda the same way
    ``FakeStructuredOutputModel`` does.
    """

    pass


# ---------------------------------------------------------------------------
# Smoke: harness produces a valid report dict with the correct shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_eval_report_shape(fake_get_model) -> None:
    """run_eval returns a dict with the expected keys and sensible values."""
    from tests.conftest import FakeStructuredOutputModel

    # A model that always returns COACH at high confidence.
    fake_model = FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=Route.COACH,
            confidence=0.95,
            rationale="fake",
        )
    )

    report = await run_eval(fake_model, cases=CASES)

    assert "total" in report
    assert "correct" in report
    assert "accuracy" in report
    assert "avg_latency_s" in report
    assert "results" in report

    assert report["total"] == len(CASES)
    assert isinstance(report["accuracy"], float)
    assert 0.0 <= report["accuracy"] <= 1.0
    assert isinstance(report["avg_latency_s"], float)
    assert report["avg_latency_s"] >= 0.0
    assert len(report["results"]) == len(CASES)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_run_eval_per_result_shape(fake_get_model) -> None:
    """Each per-case result dict carries the expected keys."""
    from tests.conftest import FakeStructuredOutputModel

    fake_model = FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=Route.COACH,
            confidence=0.95,
            rationale="fake",
        )
    )

    report = await run_eval(fake_model, cases=CASES[:3])
    for result in report["results"]:  # type: ignore[union-attr]
        assert "message" in result
        assert "expected" in result
        assert "route" in result
        assert "correct" in result
        assert "latency_s" in result
        assert isinstance(result["correct"], bool)
        assert isinstance(result["latency_s"], float)


@pytest.mark.asyncio
async def test_ambiguous_cases_score_correct_when_model_clarifies(fake_get_model) -> None:
    """Ambiguous cases score correct when the model clarifies (route is None)."""
    from tests.conftest import FakeStructuredOutputModel

    # Model returns low confidence so decide_route triggers clarification (route=None).
    fake_model = FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=Route.COACH,
            confidence=0.3,  # below threshold → clarify
            rationale="low confidence",
        )
    )

    ambiguous_cases = [c for c in CASES if c.ambiguous]
    assert len(ambiguous_cases) >= 1, "Case set must have at least one ambiguous case"

    report = await run_eval(fake_model, cases=ambiguous_cases)
    for result in report["results"]:  # type: ignore[union-attr]
        assert result["correct"] is True, (
            f"Ambiguous case should be correct when model clarifies; got {result}"
        )


@pytest.mark.asyncio
async def test_clear_cases_scored_against_expected_route(fake_get_model) -> None:
    """Clear-intent cases pass when the model returns the expected route."""
    from tests.conftest import FakeStructuredOutputModel

    # Count how many COACH clear-intent cases exist.
    coach_cases = [c for c in CASES if not c.ambiguous and c.expected_route == Route.COACH]
    assert len(coach_cases) >= 1

    # Model always returns COACH at high confidence → all coach cases correct.
    fake_model = FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=Route.COACH,
            confidence=0.95,
            rationale="fake — always coach",
        )
    )

    report = await run_eval(fake_model, cases=coach_cases)
    assert report["correct"] == report["total"]
    assert report["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_clear_cases_fail_on_wrong_route(fake_get_model) -> None:
    """A clear-intent case scores as incorrect when the model returns the wrong route."""
    from tests.conftest import FakeStructuredOutputModel

    # Take one WORKOUT_LOG case; model returns COACH → should fail.
    log_cases = [c for c in CASES if not c.ambiguous and c.expected_route == Route.WORKOUT_LOG]
    assert len(log_cases) >= 1

    fake_model = FakeStructuredOutputModel(
        parsed_result=RoutingDecision(
            route=Route.COACH,  # wrong route for a log case
            confidence=0.95,
            rationale="fake — always coach",
        )
    )

    report = await run_eval(fake_model, cases=log_cases)
    assert report["correct"] == 0
    assert report["accuracy"] == 0.0


def test_case_set_has_minimum_coverage() -> None:
    """The case set covers all three routes and has ≥ 1 ambiguous case."""
    routes_covered = {c.expected_route for c in CASES if c.expected_route is not None}
    assert Route.COACH in routes_covered
    assert Route.WORKOUT_GENERATE in routes_covered
    assert Route.WORKOUT_LOG in routes_covered
    ambiguous = [c for c in CASES if c.ambiguous]
    assert len(ambiguous) >= 1, "Need at least one ambiguous case"


def test_case_set_has_at_least_10_cases() -> None:
    """The case set has at least 10 entries (~10–15 labeled cases)."""
    assert len(CASES) >= 10, f"Expected ≥10 cases, got {len(CASES)}"


def test_print_report_does_not_raise(capsys) -> None:
    """_print_report runs without error and produces non-empty output."""
    report = {
        "total": 2,
        "correct": 2,
        "accuracy": 1.0,
        "avg_latency_s": 0.5,
        "results": [
            {
                "message": "What muscles does a deadlift work?",
                "expected": "coach",
                "route": "coach",
                "correct": True,
                "latency_s": 0.5,
            },
            {
                "message": "Build me a workout",
                "expected": "workout_generate",
                "route": "workout_generate",
                "correct": True,
                "latency_s": 0.5,
            },
        ],
    }
    _print_report("openai/gpt-4o-mini", report)
    captured = capsys.readouterr()
    assert "openai/gpt-4o-mini" in captured.out
    assert "100.0%" in captured.out
