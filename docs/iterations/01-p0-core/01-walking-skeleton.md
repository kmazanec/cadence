# Feature: Walking skeleton (branded chat ↔ SSE ↔ hub stub)

**ID:** F-01 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** There is no application — no backend, no UI, no graph.
**After:** A user opens the branded Future-style chat UI, types a message, and sees a streamed reply
produced by a minimal LangGraph hub (FastAPI → SSE → graph → one real subgraph), end-to-end.

This is the thinnest possible vertical slice through every layer. It owns ALL the foundational infra
and the minimum-viable form of nearly every cross-cutting contract — later features extend each facet
without redoing it. Its purpose is also to **de-risk the LangGraph composition + SSE streaming
patterns first**, before any agent logic is built on them.

## How it fits the roadmap
First feature of iteration 01; **no hard dependencies**. It freezes the contracts (HTTP API, SSE
envelope, graph state, Route enum, model factory/registry, ExerciseRepository, brand tokens) that
F-02/F-03/F-04/F-05 then build against concurrently.

## Requirements traced (from the PRD)
Partial scaffolding for reqs 1–5 (hub entry point + Route enum + state), 19–21 (web chat UI shell,
streaming render), 22–23 (model abstraction + capability registry), §7.1 (typed StateGraph, composed
subgraph), 11a (SSE streaming); acceptance criteria 16–17 (UI exists, branded), 21 (model swap path).

## Dependencies (must exist before this starts)
None — can start immediately.
- External: an OpenRouter API key in env (manual setup) to exercise the real model path; the skeleton
  must also run with a fake/stub model so it boots without a key.

## Unblocks (what waits on this)
- F-02 (router), F-03 (coach), F-04 (generator), F-05 (logger) — all consume F-01's frozen contracts
  and its running hub/UI/SSE plumbing.

## Contracts touched
- **HTTP chat API** (ADR-001) — introduces the request/response envelope + the `/chat` route.
- **SSE event envelope** (ADR-002) — introduces typed events `route·token·structured·clarification·
  done·error`; structured/tool content read from state, not message deltas.
- **Graph state schema** (ADR-004) — introduces `HubState` + the boundary-adapter pattern + one
  subgraph state (the stub coach), session-keyed `messages`, single-owner reducers, first-invocation
  rule.
- **Route enum + RoutingDecision** (ADR-005) — introduces the closed `Route` enum and the
  `RoutingDecision`/`ClarificationPrompt` shapes; F-01's router is a stub that returns a fixed route.
- **Model config + capability registry** (ADR-007) — introduces `get_model(role)`, the registry,
  per-role config, fail-fast startup validation, and the fake-model injection seam.
- **ExerciseRepository** (ADR-008) — introduces the interface + `JsonExerciseRepository` loading
  `data/exercises.json` into typed `Exercise` models at startup.
- **Brand & voice design tokens** (ADR-013) — introduces the Tailwind theme tokens + `BRAND.md`;
  includes the eyedropper pass to confirm the accent hex against the live future.co site.

## Acceptance criteria (product behavior)
1. `git clone` → documented setup → one command brings up backend + frontend; the chat UI loads in a
   browser.
2. Typing a message and sending it streams a visible reply token-by-token (SSE), rendered in the
   branded UI (neutral palette, sans-serif, generous spacing — demonstrably not a default chatbot).
3. The backend is a LangGraph `StateGraph` hub with typed state and explicit edges, routing to at
   least one separately-compiled subgraph (the stub coach) via a unique node name — runnable headless
   (CLI/curl) with no frontend.
4. The app boots with a fake/stub model and no API key (for tests/CI); with an OpenRouter key + a
   registry-capable model configured, it uses the real model. Startup fails fast with a clear message
   if a structured-output role is assigned a non-capable model.
5. Tool/structured content in the SSE stream is sourced from graph state, not from streamed message
   deltas (the ADR-002 safe pattern), verifiable by inspecting the emitter.
6. Changing the configured model via config only (no code change) still boots and replies.

## Testing requirements
- **Integration:** a headless request through the hub returns a streamed response; the stub subgraph
  is reached via its unique node name (no `MULTIPLE_SUBGRAPHS` error).
- **Unit:** `get_model(role)` returns a configured model; startup validation rejects a non-capable
  model for a structured-output role; `JsonExerciseRepository` loads 50 typed exercises and
  `get_by_id`/`search` work.
- **Contract:** the SSE event types and the HTTP envelope serialize/deserialize between backend and
  the frontend type mirror.
- Must run with the fake model (no network) in CI.

## Manual setup required
- OpenRouter API key in `.env` (for the real-model path); `.env.example` documents it. The app must
  still boot + test without it via the fake model.
- Eyedropper pass against live future.co to confirm the accent hex token (human visual check).

## Implementation notes (filled in by the building agent)

### Subgraph boundary adapter pattern

The coach subgraph (`app/agents/coach/graph.py`) is called from a boundary
node (`coach_boundary`) inside the hub rather than embedded as a compiled
subgraph node. This avoids LangGraph's output-key-merge conflict when the
child state (`CoachState.answer`) has no corresponding field in `HubState`. The
boundary node translates HubState → CoachState input, calls `coach.ainvoke()`,
then wraps the answer in `CoachResult` before writing back to HubState.

### Streaming token path

The SSE emitter uses `graph.astream(..., stream_mode=["messages","updates"], subgraphs=True)`.
With `subgraphs=True`, each yielded item is a `(namespace, mode, data)` 3-tuple.
Token chunks (`AIMessageChunk`) arrive in the `messages` mode from the coach
boundary's internal model call; the route event is read from the `updates` mode
when the router node commits its output. This satisfies ADR-002: route/structured
events come from committed state, never from message deltas.

### Model injection seam

`app/models/factory.py` exports `get_model`; the coach graph imports the module
(not the function) so monkeypatching `app.models.factory.get_model` in tests
affects the running agent. All 35 backend tests run without a network call.

### Acceptance criteria status

1. docker compose up → http://localhost:5173 (verified: Vite dev server + backend start)
2. Streaming SSE reply rendered token-by-token (verified: 166 token events for a real question)
3. LangGraph hub with typed state, explicit edges, and coach_boundary unique node name (verified by test)
4. Boots with fake model/no key (35 tests, no network); fails fast with bad model config (test)
5. Route/structured events sourced from committed state updates, not message deltas (see emitter)
6. Changing MODEL_CONFIG dict changes the model without code change (architecture, not test-verified)
