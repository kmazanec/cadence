# ADR-005: Router via structured output, confidence-gated clarify at threshold 0.7

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The hub must classify each message into one of `COACH`, `WORKOUT_GENERATE`, `WORKOUT_LOG` using
**LLM structured output** (not regex/keywords), carry a **confidence**, and **clarify** below a
threshold rather than misroute (PRD reqs 1–4, criteria 1–6). Research is specific here: a
`confidence_score` field from `with_structured_output()` is **LLM-generated, not statistically
calibrated**, and the recommended production pattern is to use it as a **routing threshold signal
(~0.7)**, sending below-threshold queries to a clarification node; `include_raw=True` lets us
distinguish the three documented structured-output failure modes (null output, schema hallucination,
token exhaustion) (TECHNOLOGY.md §structured output, refs [17][18]).

Serves: PRD reqs 1–5, criteria 1–6; §8.5 (threshold is a tuning decision).

## Options considered

- **Regex/keyword routing.** Explicitly forbidden by the brief (req 2). Rejected.
- **Embedding/semantic router.** 92–96% precision at lower cost (low-confidence single source), but
  adds an embedding store M1 doesn't otherwise need and doesn't itself produce the *confidence +
  clarification* the PRD wants. Deferred — noted as a future routing optimization, not M1.
- **LLM structured-output classification with a calibrated-probability confidence.** Not achievable
  without an extra scoring pass (CONSTRUCT-style); over-budget and over-claims calibration. Rejected.
- **LLM structured-output classification, confidence as a threshold signal (chosen).** A Pydantic
  `RoutingDecision` via `with_structured_output(include_raw=True)`, confidence treated as a gate.

## Decision

The router node calls the model's `with_structured_output(RoutingDecision, include_raw=True)` where
`RoutingDecision = { route: Route, confidence: float, rationale: str, clarification:
ClarificationPrompt | None }`. If `confidence >= 0.7`, the hub dispatches to the route's subgraph; if
`confidence < 0.7` (or structured output failed), the hub routes to the **clarification node**, which
returns a question naming ≥2 plausible interpretations and does **not** dispatch. The 0.7 threshold is
a named constant, tunable against the ambiguous test cases (criteria 4–5).

## Rationale

This is exactly the research-recommended pattern and it satisfies every routing criterion: structured
output (criterion 6), numeric confidence (criterion 1), clarify-not-misroute below threshold
(criteria 4–5). Treating confidence as a *signal not a probability* is the honest framing a CTO will
respect — we don't claim calibration we don't have. `include_raw=True` is what lets the resilience
layer (ADR-006) tell *which* failure mode occurred instead of a blanket catch.

## Tradeoffs & risks

- **The 0.7 threshold is a guess until tuned.** Mitigation: it's a single named constant; the
  ambiguous acceptance tests (criteria 4–5) are its calibration set (PRD §8.5). Over-asking vs
  under-asking is a dial, not a redesign.
- **LLM confidence can be miscalibrated/overconfident.** Accepted and documented: it's a routing
  heuristic with a clarify safety-net, not a trust score. The README's evaluation section names
  routing accuracy + clarification rate as the metrics to watch (PRD req 24).

## Consequences for the build

- **Contract (Route enum + RoutingDecision).** Shared shape; adding a route is a deliberate change.
  - **Source of truth:** `backend/app/graph/routing.py` (`Route` enum, `RoutingDecision`,
    `ClarificationPrompt` Pydantic models).
  - **Shape (initial):** `Route = COACH | WORKOUT_GENERATE | WORKOUT_LOG` (closed enum);
    `RoutingDecision` as above; `ClarificationPrompt = { question: str, options: list[str] }`.
  - **Exhaustive consumers:** the router node, the hub's conditional edges (one branch per route +
    the clarify branch), the response-assembly node, the SSE `route` event (ADR-002), and the
    frontend route-render branches (ADR-001). Adding a `Route` member must update every one — the
    conditional-edge map and the frontend switch must stay exhaustive. (M2+ may add member-scoped
    coach routes to this enum family.)
- **Policy:** confidence is a threshold signal, never presented as a calibrated probability.
- **Policy:** the 0.7 threshold is one named constant, not scattered magic numbers.
