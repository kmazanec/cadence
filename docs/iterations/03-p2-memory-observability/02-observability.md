# Feature: Observability — structured tracing (P2)

**ID:** F-09 · **Iteration:** 03-p2-memory-observability · **Status:** Not started

## What this delivers (before → after)
**Before:** A request's internal path (route, model calls, tool calls) is opaque.
**After:** Every LLM call and tool invocation is recorded in structured logs so that, for any user
message, the route taken and each tool call with its outcome can be reconstructed — with secrets
redacted. An optional vendor tracer can be enabled by env.

## How it fits the roadmap
Second feature of iteration 03 (P2 depth); independent of F-08 within the iteration (both extend
iteration-01 features, neither consumes the other). Underpins the README's evaluation story.

## Requirements traced (from the PRD)
Reqs 24 (evaluation story), 26; acceptance criterion 23.

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: the route taken is a core thing to log; instrumentation hooks attach
  at the router + tool nodes + model factory.
(Instruments the F-01 `get_model` factory and the F-04/F-05 tool nodes — contract-mediated, not hard
deps on those features' behavior.)

## Unblocks (what waits on this)
- Nothing downstream in M1.

## Contracts touched
- Conforms to the model-factory + tool-node instrumentation points (ADR-007/017). Introduces no shared
  data contract; the log shape is internal.

## Acceptance criteria (product behavior)
1. For a processed message, the structured log lets an operator reconstruct: the route taken, each LLM
   call (role, model, latency), each tool invocation (name, outcome/error), retry counts, total
   latency.
2. Secrets (API keys) never appear in logs (redacted).
3. A vendor tracer (LangSmith/Langfuse) is enabled only when its key is present; the app runs and
   tests fully without it.

## Testing requirements
- **Integration:** run a request and assert the emitted structured log contains the route + at least
  one tool/model event with outcome, and contains no secret value.

## Manual setup required
- Optional: a tracing-vendor key to demo the vendor path (not required to run/test).

## Implementation notes (filled in by the building agent)
