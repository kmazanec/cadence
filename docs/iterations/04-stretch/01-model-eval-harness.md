# Feature: Model-eval harness (routing split-test) — stretch

**ID:** F-10 · **Iteration:** 04-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** The "how I'd evaluate" story is prose in the README.
**After:** A runnable script scores ~10–15 labeled routing cases across ≥2 configured models and prints
routing accuracy + latency per model — turning the evaluation story into proof and demonstrating the
model abstraction's split-test promise.

## How it fits the roadmap
Iteration 04 (stretch); cut first under time pressure. Deliberately a tiny seed, not a formal eval
pipeline.

## Requirements traced (from the PRD)
Req 16 (committed stretch), supports req 24 (evaluation story).

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: scores the router's classification behavior.
(Uses F-01's `get_model`/registry + per-role config to swap models — contract-mediated.)

## Unblocks (what waits on this)
- Nothing.

## Contracts touched
- **Model config + capability registry** (ADR-007) — consumes per-role model config to run the same
  routing cases across multiple capable models.
- **Route enum + RoutingDecision** (ADR-005) — the labeled cases assert against the route enum.

## Acceptance criteria (product behavior)
1. Running the script against a labeled case set prints, per configured model, routing accuracy and
   average latency.
2. The case set includes clear-intent and ambiguous cases (the latter checking clarify behavior).
3. Swapping/adding a model is config-only; the script needs no code change to evaluate it.

## Testing requirements
- **Smoke:** the harness runs end-to-end against the fake model (deterministic) producing a report;
  a real-model run is optional/documented.

## Manual setup required
- Optional: API keys for the candidate models to run a real split-test.

## Implementation notes (filled in by the building agent)
