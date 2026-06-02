# ADR-016: Non-functional targets — latency budgets, perceived-latency via streaming, scale deferred

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The PRD doesn't fix M1 latency numbers, but the build needs targets to verify against, and the M2
brief later sets <5s for AI responses. Research measured the supervisor pattern at ~4.2s for a
single-domain request (router call + agent call) and ~9.1s multi-domain (TECHNOLOGY.md §supervisor).
M1 adds one routing LLM call ahead of each agent. Scale is a non-issue for a single-user demo but
should be a recorded deferral, not silence.

Serves: PRD reqs 19–21 (responsive UI), §10 M6 (<5s platform target inherited).

## Options considered

Targets, not mutually-exclusive options. The real choice was whether to state numbers and a
perceived-latency strategy now (chosen) or leave performance unstated (rejected — an unstated target
can't be verified).

## Decision

- **Latency budget (happy path, M1):** routing classification target **< 1.5s**; a single-route
  end-to-end response target **< 5s** to completion, consistent with the M2 brief's bar. These are
  targets, not hard SLAs, for M1.
- **Perceived latency via streaming (ADR-002):** **time-to-first-token target < 1.5s** after routing
  — the SSE token stream makes the coach feel responsive even when full completion takes a few
  seconds. Perceived latency is the metric the premium UX actually trades on.
- **Model choice as the latency lever:** per-role models (ADR-007) let the router use a cheap/fast
  model and the generator a stronger one, tuning the budget without code changes.
- **Scale:** M1 is **single-instance, single-user (demo)** — horizontal scale, concurrency, and load
  are **explicitly deferred** to M6's platform stage. This is a conscious choice given no real users
  in scope, not an omission.
- **Availability / retention:** no availability SLA for M1; logged data retention is "local store,
  session-oriented" (ADR-011) — durable but not subject to a compliance retention policy until real
  member data (M6).

## Rationale

Stating budgets makes them verifiable downstream and ties M1 to the platform's eventual <5s bar.
Streaming converts the supervisor pattern's inherent two-call latency from a liability into an
acceptable UX by front-loading the first token — the honest way to hit "feels premium" without
pretending the absolute latency is faster than two LLM calls allow. Deferring scale is correct for a
demo and is recorded so a CTO sees it was decided, with M6 named as where it changes.

## Tradeoffs & risks

- **Two LLM calls per turn set a latency floor** the router can't beat. Mitigation: fast router model
  + streaming for perceived speed; documented.
- **OpenRouter adds a network hop** vs a native provider. Accepted for swappability (ADR-007);
  `init_chat_model` escape hatch exists if a role needs a direct provider for latency.

## Consequences for the build

- **Policy:** routing < 1.5s and time-to-first-token < 1.5s are the perceived-latency targets the
  build tunes toward (model selection is the lever).
- **Policy:** M1 is single-instance; do not build concurrency/scaling machinery — deferred to M6.
- The README "how I'd evaluate" section (req 24) reports these budgets and the metrics that track
  them (routing latency, TTFT, completion latency).
