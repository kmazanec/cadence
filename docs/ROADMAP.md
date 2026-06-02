# Roadmap — Cadence (Milestone 1)

**Status:** agreed · **Date:** 2026-06-02
**Source:** [ARCHITECTURE.md](./ARCHITECTURE.md) · [PRD.md](./PRD.md) · [research/](./research/)

## Overview

Cadence M1 is a multi-agent fitness chat coach: a LangGraph hub routes each message (via LLM
structured output + confidence) to a Coach, Workout Generator, or Workout Logger sub-agent, surfaced
through a premium Future-branded React chat UI over an SSE-streaming FastAPI backend. This is a **2–3
hour graded take-home**, so the iteration arc is deliberately the PRD's **P0 → P1 → P2 → stretch
cut-order**: each iteration is a clean cut-line that leaves a shippable, gradeable product, and later
iterations are exactly what gets cut if time runs short. Team-shape assumption: a small build where the
skeleton lands first (freezing contracts) and the three sub-agents then build concurrently against them.

## The iteration arc

- **Iteration 01 — P0 core** ([docs/iterations/01-p0-core/](./iterations/01-p0-core/)) — *After this,
  a user can hold a real branded chat conversation that correctly routes to all three working
  sub-agents (or asks a clarifying question), with resilient, no-hallucination behavior and passing
  critical-path tests.* This is the must-ship milestone; everything below is additive and cut-able.
- **Iteration 02 — P1 differentiators** ([docs/iterations/02-p1-injury-bilateral/](./iterations/02-p1-injury-bilateral/))
  — *After this, the generator avoids exercises that load an injured joint and auto-pairs bilateral
  exercises.* Cheap, dataset-backed; cut before P0, after nothing.
- **Iteration 03 — P2 depth** ([docs/iterations/03-p2-memory-observability/](./iterations/03-p2-memory-observability/))
  — *After this, the coach remembers earlier turns within a session, and every LLM/tool call is
  traceable.* Cut before P1.
- **Iteration 04 — Stretch polish** ([docs/iterations/04-stretch/](./iterations/04-stretch/)) —
  *After this, a grader can run a model-eval split-test, see a "why these?" explanation panel on
  workouts, and feel a cohesive coach personality.* Cut first of all.

**Cut-order = arc order.** Ship through iteration N; N+1… is what's dropped under time pressure. Within
iteration 01, the feature order also encodes priority (router + generator-safety are the
non-negotiable critical-path pair per ADR-018).

## Features index

| ID | Feature | Iteration | Spec | "Before → After" (one line) | Depends on (hard) |
|----|---------|-----------|------|------------------------------|--------------------|
| F-01 | Walking skeleton (branded chat ↔ SSE ↔ hub stub) | 01 | [01-p0-core/01-walking-skeleton.md](./iterations/01-p0-core/01-walking-skeleton.md) | No app → a user types in the branded UI and gets a streamed reply from a minimal routed hub | none |
| F-02 | Router: structured output + confidence + clarify | 01 | [01-p0-core/02-router-confidence-clarify.md](./iterations/01-p0-core/02-router-confidence-clarify.md) | Hub always hits the stub → hub classifies intent and clarifies when unsure | F-01 |
| F-03 | Coach sub-agent | 01 | [01-p0-core/03-coach-subagent.md](./iterations/01-p0-core/03-coach-subagent.md) | Coach is a stub → real fitness Q&A in coach voice | F-01 |
| F-04 | Workout Generator sub-agent + output gate | 01 | [01-p0-core/04-workout-generator.md](./iterations/01-p0-core/04-workout-generator.md) | No generation → structured warmup/main/cooldown workout from real dataset exercises | F-01 |
| F-05 | Workout Logger sub-agent + persistence | 01 | [01-p0-core/05-workout-logger.md](./iterations/01-p0-core/05-workout-logger.md) | No logging → NL workout parsed, fuzzy-matched/flagged, persisted | F-01 |
| F-06 | Resilience hardening + critical-path tests | 01 | [01-p0-core/06-resilience-and-tests.md](./iterations/01-p0-core/06-resilience-and-tests.md) | Happy-path only → empty/invalid recovers gracefully, ≥2 critical-path tests pass, transcript+README | F-02, F-04, F-05 |
| F-07 | Injury avoidance + bilateral pairing (P1) | 02 | [02-p1-injury-bilateral/01-injury-and-bilateral.md](./iterations/02-p1-injury-bilateral/01-injury-and-bilateral.md) | Generator ignores injuries/sides → excludes injured-joint exercises, auto-pairs bilateral | F-04 |
| F-08 | Multi-turn session memory (P2) | 03 | [03-p2-memory-observability/01-multi-turn-memory.md](./iterations/03-p2-memory-observability/01-multi-turn-memory.md) | Each turn is independent → "adjust it"/clarify-answers resolve against prior turns | F-02, F-04 |
| F-09 | Observability: structured tracing (P2) | 03 | [03-p2-memory-observability/02-observability.md](./iterations/03-p2-memory-observability/02-observability.md) | Opaque runs → every LLM/tool call + route reconstructable from structured logs | F-02 |
| F-10 | Model-eval harness (stretch) | 04 | [04-stretch/01-model-eval-harness.md](./iterations/04-stretch/01-model-eval-harness.md) | Eval is prose in README → runnable split-test scoring routing across ≥2 models | F-02 |
| F-11 | "Why these?" explanation panel (stretch) | 04 | [04-stretch/02-explanation-panel.md](./iterations/04-stretch/02-explanation-panel.md) | Explanation payload unseen → expandable "why these?" panel on workouts | F-04, F-07 |
| F-12 | Coach voice/personality polish (stretch) | 04 | [04-stretch/03-coach-voice-polish.md](./iterations/04-stretch/03-coach-voice-polish.md) | Generic agent tone → cohesive warm coach personality across all states | F-03, F-04, F-05 |

**Concurrency note:** within iteration 01, F-02/F-03/F-04/F-05 all hard-depend only on F-01, so once
F-01 freezes the contracts they build **concurrently**; F-06 waits on the router + generator + logger.
Iterations 02 and 03 are **independent of each other** (both extend iteration-01 features, neither
consumes the other) — they can be planned/built concurrently once iteration 01 is merged.

## Cross-cutting contracts

Each cites the ADR that decided it (source of truth — not restated here). These are what
`kmaz-plan-iteration` freezes with concrete signatures before the build. Every one is **introduced by
F-01** (the walking skeleton lands the minimum-viable form of all of them), then extended.

| Contract | Source of truth (ADR) | Introduced by | Extended by |
|----------|------------------------|---------------|-------------|
| HTTP chat API (request/response envelope) | [ADR-001](./adrs/ADR-001-split-python-api-react-frontend.md) | F-01 | F-02 (clarification), F-04 (workout), F-05 (log) |
| SSE event envelope (route·token·structured·clarification·done·error) | [ADR-002](./adrs/ADR-002-sse-streaming-final-tokens.md) | F-01 | F-04, F-05 (structured payloads), F-11 (explanation rendering) |
| Graph state schema (HubState + isolated subgraph states) | [ADR-004](./adrs/ADR-004-state-contract-isolated-subgraphs-session-memory.md) | F-01 | F-02 (routing fields), F-03/F-04/F-05 (subgraph states), F-08 (memory) |
| Route enum + RoutingDecision | [ADR-005](./adrs/ADR-005-router-structured-output-confidence-clarify.md) | F-01 (enum + stub) | F-02 (real classification + clarify), F-10 (eval cases) |
| Model config + capability registry (`get_model(role)`) | [ADR-007](./adrs/ADR-007-model-abstraction-openrouter-capability-registry.md) | F-01 | F-02/F-03/F-04/F-05 (per-role models), F-10 (split-test) |
| ExerciseRepository interface | [ADR-008](./adrs/ADR-008-exercise-repository-seam.md) | F-01 (JSON impl) | F-04 (search/build), F-05 (fuzzy match), F-07 (contraindicated_ids/bilateral_pair) |
| LogRepository + log entry schema | [ADR-011](./adrs/ADR-011-log-persistence-postgres-or-sqlite.md) | F-05 | (M3 future) |
| Reason / explanation payload | [ADR-012](./adrs/ADR-012-explanation-payload-relation-shaped.md) | F-04 (generator emits reasons) | F-07 (exclusion/pairing reasons), F-11 (UI panel) |
| Brand & voice design tokens | [ADR-013](./adrs/ADR-013-frontend-brand-tokens-contract.md) | F-01 | every UI feature; F-12 (voice personality) |

> Note: ADR-011's `LogRepository` is introduced by **F-05**, not F-01 — it's the one contract the
> skeleton doesn't need (no logging yet). All others land in F-01's minimum-viable form.

## Risk-weighted ordering

- **Biggest unknown: LangGraph composition footguns** (silent state corruption, `MULTIPLE_SUBGRAPHS`,
  retry/ValidationError, streaming corruption — TECHNOLOGY.md caveats). De-risked **first**: F-01
  stands up the hub + one real subgraph + SSE end-to-end, proving the composition and streaming
  patterns (ADR-002/003/004) before any agent logic is built on them.
- **Safety invariant (no hallucinated exercise / injury exclusion)** is the highest-stakes
  correctness path. De-risked in F-04 (output-validation gate) and F-06 (tests), with the hard-exclusion
  extension in F-07 — the gate exists from the moment generation does.
- **Routing accuracy + clarify threshold** (the 0.7 tuning) is de-risked in F-02 with the ambiguous
  test cases as the calibration set, then locked by F-06's tests.
- **Brand fidelity** (subjective; exact accent hex unconfirmed) is de-risked early: F-01 lands the
  brand tokens so every later UI feature inherits a verified look, with the eyedropper pass in F-01.
- **Scope-vs-time** is the meta-risk; the cut-order arc itself is the mitigation — ship iteration 01,
  cut upward.

## Non-goals and deferred work

(Mirrors PRD §4 Out-of-Scope + Deferred after the architecture-v2 promotions.)

- **No M2+ knowledge-graph work** — no graph DB, GraphRAG, vector store, or Neo4j. M1 only shapes its
  seams (ExerciseRepository, injury-as-relationship, explanation payload) to graduate later. Building
  graph infra now is the over-engineering PRD §8.8 forbids.
- **No auth / multi-user / per-member isolation** (single-user demo; auth → M6).
- **No nutrition, scheduling, real human coaches, payment, onboarding.**
- **No exercise data beyond the 50-entry dataset; no external exercise APIs.**
- **No horizontal scale / concurrency machinery** (single-instance for M1).
- **No formal eval pipeline** — F-10 is a deliberately tiny seed, not the M-cross-cutting harness.

## Open questions

- Exact Future accent hex (eyedropper pass during F-01 — ADR-013).
- 0.7 confidence threshold + RapidFuzz cutoff 80 are starting values, tuned against test cases in
  F-02/F-05 (ADR-005/010).
- Whether the logger's LLM-verify step is on by default vs. pure-deterministic (decided in F-05 by
  accuracy on test inputs — ADR-010).
- Reproduce the low-confidence LangGraph footgun claims against the pinned version during F-01.
