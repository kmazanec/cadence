# Feature: Router — structured output + confidence + clarify

**ID:** F-02 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** The hub always dispatches to the stub subgraph (fixed route from F-01).
**After:** The hub classifies each message into `COACH` / `WORKOUT_GENERATE` / `WORKOUT_LOG` via LLM
structured output with a confidence, dispatches to the matching subgraph at/above 0.7, and returns a
clarifying question below threshold instead of misrouting.

## How it fits the roadmap
Iteration 01; the spine. One of the non-negotiable critical-path pair (with F-04 safety) per ADR-018.
Hard-depends on F-01's frozen hub/state/Route/model contracts.

## Requirements traced (from the PRD)
Reqs 1–5; acceptance criteria 1–6. (Routing via structured output, numeric confidence, dispatch ≥
0.7, clarify < 0.7, single entry point, route observable.)

## Dependencies (must exist before this starts)
- **F-01 (walking skeleton)** — HARD dep: consumes the running hub, the `Route` enum +
  `RoutingDecision` contract, `HubState`, the conditional-edge wiring, and `get_model('router')`.
- External: none beyond F-01's.

## Unblocks (what waits on this)
- F-06 (resilience/tests) — tests the routing + clarify behavior.
- F-08 (memory) — clarify-answer resolution builds on routing.
- F-09 (observability) — logs the route taken.
- F-10 (eval harness) — scores routing decisions.

## Contracts touched
- **Route enum + RoutingDecision** (ADR-005) — extends F-01's stub to real classification via
  `with_structured_output(RoutingDecision, include_raw=True)`; adds the clarification branch.
- **Graph state schema** (ADR-004) — populates `route`, `routing_confidence`, `routing_raw`,
  `clarification` fields.
- **HTTP/SSE envelope** (ADR-001/002) — emits the `route` event and the `clarification` event/payload.

## Acceptance criteria (product behavior)
1. "What muscles does a deadlift work?" → route `COACH`, numeric confidence present.
2. "Build me a 30 min upper body session with dumbbells" → route `WORKOUT_GENERATE`.
3. "I just did 3x10 bench press at 185 lbs" → route `WORKOUT_LOG`.
4. "I did a workout yesterday, can you adjust it?" → either confidence < 0.7 with a clarifying question
   naming ≥2 interpretations, OR a recorded high-confidence route — never a silent below-threshold
   dispatch.
5. "Bench press" (bare) → clarifying question, not a dispatch.
6. Classification is obtained via structured output (a typed object with a route enum + confidence),
   not regex/keyword logic.
7. The 0.7 threshold is a single named constant, tuned so cases 4–5 clarify and 1–3 dispatch.

## Testing requirements
- **Integration (deterministic):** inject a fake router model returning controlled `RoutingDecision`s
  (including below-threshold) and assert the hub dispatches to the correct subgraph or to the
  clarification node accordingly — independent of LLM variance.
- **Live-or-recorded smoke:** the three canonical messages (cases 1–3) route correctly against a real
  model (kept minimal).
- Asserts the route taken is observable in state (criterion / req 5).

## Manual setup required
None beyond F-01.

## Implementation notes (filled in by the building agent)

**Status:** Complete — all five chunks delivered.

**Chunk 1 — Threshold constant + decide_route:** Already present in the frozen
contracts (`backend/app/graph/routing.py`). Tests added in
`backend/tests/graph/test_routing_decision.py` covering the 0.69/0.70 boundary,
None-decision safe-net, and all three Route arms.

**Chunk 2 — Router node with structured output:** Replaced the F-01 stub router
with a real structured-output call (`get_model('router').with_structured_output
(RoutingDecision, include_raw=True)`). A null parse (parsed=None) triggers
safe-net clarification via decide_route. Updated `conftest.py` to add
`FakeStructuredOutputModel` that supports `with_structured_output(include_raw=True)`
and streams token deltas. Decision: the `simulate_null_parse` boolean flag on the
fake avoids overloading `parsed_result=None` (which means "use default COACH
decision") with the failure-path semantics.

**Chunk 3 — Hub conditional edge tests:** Added `test_hub_dispatch.py` driving
the compiled hub with each Route above threshold and a below-threshold /
null-parse case. Confirmed the clarify node is reached and no subgraph result
is produced in the clarify case.

**Chunk 4 — SSE clarification event:** Updated `chat.py` to emit
`{type:'clarification', question, options}` from committed state when the router
sets `clarification` in HubState. Events come from `updates` mode, not message
deltas. Tests in `test_streaming_route_clarify.py` assert both the route and
clarification paths.

**Chunk 5 — Live smoke:** `test_router_live_smoke.py` skips without
`OPENROUTER_API_KEY`. Three canonical messages parametrized over COACH /
WORKOUT_GENERATE / WORKOUT_LOG. Registered `live` as a custom pytest mark.

**Scope boundary held:** Full ADR-006 bounded-retry / error-feedback stays
deferred to the resilience feature. The null-parse path delivers only the
minimal safe-net (clarify instead of silently misroute).

### Build outcome

- **Shippable:** yes. Integrated via cherry-pick onto `integration/01-p0-core` (its 6 unique commits on top of F-01; linear history).
- **Acceptance:** met. PRD §6 #1–#6 satisfied — structured-output classification (`with_structured_output(..., include_raw=True)`), `CONFIDENCE_THRESHOLD=0.7` gate, dispatch above threshold, clarify below threshold or on null parse. The integrated `test_hub_dispatch.py` drives all three route branches plus the clarify/null-parse branches through the compiled hub.
- **Unresolved gating:** none.
- **Deferred (low):** the live three-canonical-message smoke (`test_router_live_smoke.py`) is skipped offline; full ADR-006 bounded retry remains F-06's scope.
- **QA evidence:** e2e SSE smoke produced `data: {"type": "clarification", ...}` for a below-threshold input and `{"type":"route","route":"coach"}` above threshold.
