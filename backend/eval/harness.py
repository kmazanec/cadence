"""Routing split-test harness.

Scores the router's :func:`~app.graph.routing.classify` function across one or
more models and prints accuracy + average latency per model.

Usage (from backend/):
    uv run python -m eval.harness                            # uses MODEL_CONFIG["router"]
    uv run python -m eval.harness openai/gpt-4o-mini openai/gpt-4o

Config-only: swapping or adding a model requires only a CLI argument or an
env-var override of ``MODEL_CONFIG["router"]`` — no code changes.

The harness works against any :class:`~langchain_core.language_models.BaseChatModel`
that supports ``with_structured_output``; a fake/deterministic model can be
injected for offline/CI use (see :func:`run_eval`).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.graph.routing import decide_route, classify
from app.models.config import API_KEY_ENV, OPENROUTER_BASE_URL
from eval.cases import CASES, RoutingCase


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------


async def run_eval(
    model: BaseChatModel,
    cases: Sequence[RoutingCase] | None = None,
) -> dict[str, object]:
    """Run every case through ``model`` and return a result dict.

    Returns:
        {
            "total": int,
            "correct": int,
            "accuracy": float,          # 0.0 – 1.0
            "avg_latency_s": float,
            "results": list[{           # one entry per case
                "message": str,
                "expected": str | None,
                "route": str | None,
                "correct": bool,
                "latency_s": float,
            }]
        }
    """
    if cases is None:
        cases = CASES

    results = []
    total_correct = 0

    for case in cases:
        start = time.perf_counter()
        try:
            decision = await classify(case.message, model)
        except Exception:
            decision = None
        latency = time.perf_counter() - start

        route, _ = decide_route(decision)

        if case.ambiguous:
            # Ambiguous cases verify the clarify-not-dispatch path: correct only
            # when the router did NOT confidently dispatch (route is None).
            correct = route is None
        else:
            correct = route == case.expected_route

        if correct:
            total_correct += 1

        results.append(
            {
                "message": case.message,
                "expected": case.expected_route.value if case.expected_route else None,
                "route": route.value if route else None,
                "correct": correct,
                "latency_s": latency,
            }
        )

    total = len(cases)
    accuracy = total_correct / total if total > 0 else 0.0
    avg_latency = sum(r["latency_s"] for r in results) / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": total_correct,
        "accuracy": accuracy,
        "avg_latency_s": avg_latency,
        "results": results,
    }


def _print_report(model_id: str, report: dict[str, object]) -> None:
    """Print a human-readable per-model accuracy + latency report."""
    print(f"\n{'=' * 60}")
    print(f"Model: {model_id}")
    print(f"{'=' * 60}")
    print(f"  Accuracy:     {report['accuracy']:.1%}  ({report['correct']}/{report['total']})")
    print(f"  Avg latency:  {report['avg_latency_s']:.3f}s")
    print()

    results: list[dict] = report["results"]  # type: ignore[assignment]
    for r in results:
        status = "PASS" if r["correct"] else "FAIL"
        expected = r["expected"] or "clarify"
        actual = r["route"] or "clarify"
        print(
            f"  [{status}] {r['message'][:55]!r:<57}  "
            f"{expected} -> {actual}  ({r['latency_s']:.3f}s)"
        )


def _build_model(model_id: str) -> BaseChatModel:
    """Construct an OpenRouter-backed model for the given ID."""
    api_key = os.environ.get(API_KEY_ENV)
    return ChatOpenAI(
        model=model_id,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(api_key) if api_key is not None else None,
    )


async def _main(model_ids: list[str]) -> None:
    for model_id in model_ids:
        model = _build_model(model_id)
        report = await run_eval(model)
        _print_report(model_id, report)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Accept model IDs as positional args; default to the router's configured model.
    from app.models.config import MODEL_CONFIG

    ids: list[str] = sys.argv[1:] if len(sys.argv) > 1 else [MODEL_CONFIG["router"]]
    asyncio.run(_main(ids))
