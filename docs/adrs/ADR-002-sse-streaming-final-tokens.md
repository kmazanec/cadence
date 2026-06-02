# ADR-002: SSE streaming of final response tokens (safe-pattern), transport stream-ready

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** yes (promoted into M1 P0) · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The PRD originally **deferred streaming** (§4 Deferred #2). During architecture, the user promoted
streaming into M1 P0 scope for the premium "live-typing coach" feel that the branded UI (ADR-001)
trades on. This is a scope change and is being reflected back into the PRD as a new version (per the
pipeline rule that the PRD stays the source of truth for WHAT).

A documented LangGraph footgun bears directly on *how* we stream: using `subgraph=True` with
`stream_mode='messages'` can **corrupt tool-call argument values** (TECHNOLOGY.md §footguns,
ref [12] — *low confidence, single forum report, but a known sharp edge*). Relying on streamed
message events for the tool-calling internals risks feeding corrupted arguments to the Generator.

Serves: PRD reqs 19–21 (web chat UI premium feel), criterion 16 (UI renders each route); promoted
stretch.

## Options considered

- **Plain request/response, defer transport entirely.** Simplest; one POST returns the full
  response. But no live feel, and some rework when streaming lands in M6.
- **Request/response now, transport merely stream-ready.** Honors the original deferral; pick a shape
  that *could* add SSE later. Less polish now.
- **Full streaming incl. intermediate "agent thinking" steps.** Most impressive, but touches the
  riskier `stream_mode='messages'` path and costs more M1 time.
- **SSE streaming of final response tokens only, safe pattern (chosen).** Stream the *final assistant
  text* token-by-token over Server-Sent Events for the premium feel, while reading tool-call
  internals (the Generator's exercise selections, the Logger's parsed entries) from **graph state**
  via `stream_mode='updates'`/`'values'`, never from streamed message deltas.

## Decision

The chat endpoint streams over **SSE**. We stream the **final assistant response tokens** for the
typing effect, but all structured/tool-derived content (workout, log entries, route, explanation) is
read from **graph state** (`stream_mode='updates'`/`'values'`), not from streamed `messages` events.
The SSE event stream carries typed events: `token` (text delta), `structured` (the completed
workout/log payload), `route` (the chosen route, once known), and `done`/`error` terminal events.

## Rationale

This buys the premium live-typing UX the P0 UI needs while structurally **avoiding the documented
tool-argument corruption** — the corruption only affects streamed message events, and we deliberately
source all tool-derived data from committed state instead. SSE (not WebSockets) fits a one-way
server→client token stream with far less machinery, and degrades gracefully (a client that ignores
streaming still gets a coherent final message). The same SSE envelope is what M6's server-side
generation will emit, so the transport graduates cleanly.

## Tradeoffs & risks

- **More complex than a single JSON response.** Accepted for the P0 premium feel; mitigated by
  keeping the event schema small and typed.
- **Streaming footgun if someone later switches to `stream_mode='messages'`.** Mitigation: this ADR
  records the constraint explicitly; tool-derived data is read from state by policy, and a test
  asserts the Generator's chosen exercise IDs come from state (so a regression to message-streaming
  would be caught).
- **SSE buffering through some proxies.** Mitigation: disable response buffering for the SSE route;
  documented for the deploy path.

## Consequences for the build

- **Policy:** structured/tool-derived content is **always** read from graph state, never from
  streamed message deltas. `stream_mode` is `'updates'`/`'values'`; `'messages'` is not used for
  tool internals.
- **Policy:** the endpoint must still produce a coherent complete response if streaming is disabled
  (graceful degradation) — the CLI demo and tests consume the non-streamed/aggregated form.
- **Contract (SSE event envelope).** Shared wire shape between backend and frontend.
  - **Source of truth:** `backend/app/api/streaming.py` (SSE event types) + mirrored in
    `frontend/src/types/api.ts`.
  - **Shape (initial):** discriminated event union — `{type: 'route', route}` ·
    `{type: 'token', text}` · `{type: 'structured', payload}` · `{type: 'clarification', question,
    options}` · `{type: 'done'}` · `{type: 'error', message}`.
  - **Exhaustive consumers:** the backend SSE emitter, the frontend SSE client reducer, and the
    frontend render branches per event type. Adding an event type (e.g. M6 `{type: 'trace'}`) must
    update all three.
