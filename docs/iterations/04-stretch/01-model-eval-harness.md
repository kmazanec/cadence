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

- [x] **Chunk 1 — labeled case set** (`backend/eval/cases.py`): 12 cases covering all three Route
  values (coach × 4, workout_generate × 3, workout_log × 3) plus 2 ambiguous cases; frozen as a
  Python module so the harness can import them and tests can parametrize over them.
- [x] **Chunk 2 — eval harness** (`backend/eval/harness.py`): async `run_eval(model, cases)` that
  times each `classify()` call and scores it (ambiguous cases always pass); `_print_report()` prints
  per-model accuracy + avg latency + per-case PASS/FAIL; `__main__` entry point accepts model IDs
  as positional args (default: `MODEL_CONFIG["router"]`) — config-only swap as required by AC-3.
- [x] **Chunk 3 — smoke tests** (`backend/tests/test_routing_eval.py`): 8 deterministic tests using
  `FakeStructuredOutputModel` from the shared conftest — verifies report shape, ambiguous scoring,
  correct/incorrect clear-intent scoring, case-set coverage, and `_print_report` output — all
  network-free.

**Decisions:**
- `classify()` already existed as the frozen seam in `routing.py`; the harness consumes it directly.
- `run_eval` accepts a `BaseChatModel` (not a role string) so callers inject any model — including
  the fake from conftest — without touching the factory or monkeypatching in the harness itself.
- Ambiguous cases score as always-correct: the correct answer for genuinely ambiguous input is
  "any reasonable outcome" — enforcing a specific route would make the test brittle and misleading.
- The CLI accepts positional model IDs, defaulting to `MODEL_CONFIG["router"]`, so comparing two
  models is `uv run python -m eval.harness openai/gpt-4o-mini openai/gpt-4o` — no code change.
