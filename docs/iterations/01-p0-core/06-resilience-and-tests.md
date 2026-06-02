# Feature: Resilience hardening + critical-path tests + demo/README

**ID:** F-06 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** The three agents work on the happy path; failures may crash or be ungraceful; no committed
tests/transcript/README.
**After:** Empty/thin searches and invalid tool calls recover gracefully (no crash, no hallucination);
the designated critical-path tests pass; a committed transcript + a README (with the "how I'd evaluate
in production" section) ship — the repo runs end-to-end from a clean clone.

## How it fits the roadmap
The closing feature of iteration 01 — it makes the must-ship milestone actually shippable and gradeable.
Hard-depends on the router + generator + logger being real.

## Requirements traced (from the PRD)
Reqs 16–18 (resilience), 5/24 (route observable, evaluation README); acceptance criteria 14–15
(recovery, invalid tool call), 18 (≥2 critical-path tests + rationale), 19 (clean-clone run +
transcript), 20 (evaluation README section), 21 (model-swap routing tests pass).

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: tests the routing/clarify critical path; needs real classification.
- **F-04 (generator)** — HARD dep: hardens empty/thin/invalid-tool-call recovery and tests the output
  gate + injury-safety-adjacent paths.
- **F-05 (logger)** — HARD dep: tests resolve-or-flag.
(F-03 coach is exercised but not a hard dep — the critical tests target routing, generation-safety,
output-gate, and logger per ADR-018.)

## Unblocks (what waits on this)
- Nothing in iteration 01; it's the milestone closer. (Later iterations build on the merged P0 core.)

## Contracts touched
- Conforms to all iteration-01 contracts; introduces none. Exercises the error path of the SSE
  envelope (`error` event) and the resilience policy (ADR-006).

## Acceptance criteria (product behavior)
1. A generation request for equipment absent from the dataset (e.g. "only a sled") returns a graceful
   recovery (acknowledge gap / clarify), raises no unhandled exception, and names no non-dataset
   exercise.
2. A simulated invalid tool call (unknown exercise ID / schema-invalid args) is caught and answered
   meaningfully; no stack trace crosses the API boundary.
3. At least two automated critical-path tests pass from a clean clone, each with a written rationale
   (priority order per ADR-018: routing+clarify, injury/output-gate safety, no-hallucination+recovery,
   logger resolve-or-flag).
4. A committed transcript shows the three routes, the clarifying-question path, and a resilience
   recovery.
5. The README documents clean-clone setup and contains a "How I would evaluate this system in
   production" section (metrics, failure modes, correctness signals, model split-testing story).
6. Swapping the default model via config (no code change) keeps the routing tests passing.

## Testing requirements
- The designated critical-path tests (ADR-018) implemented and passing, each test file stating its
  rationale (graded). Bounded retries + error-feedback-in-state asserted. Empty/thin and invalid-tool
  recovery asserted without an unhandled exception.
- Tests run from a clean clone with the fake model (no network) for the deterministic suite.

## Manual setup required
- Record/curate the demo transcript (human-run interaction captured to a file).
- Author the README "how I'd evaluate" section (human-reviewed prose).

## Implementation notes (filled in by the building agent)
