# Feature: Multi-turn session memory (P2)

**ID:** F-08 · **Iteration:** 03-p2-memory-observability · **Status:** Not started

## What this delivers (before → after)
**Before:** Each message is handled independently; "adjust it" or a follow-up to a clarifying question
has no prior context.
**After:** Within a session, follow-ups referencing earlier turns ("make it shorter", "I did a workout
yesterday") and answers to the hub's clarifying questions resolve against prior context without the
user restating it.

## How it fits the roadmap
First feature of iteration 03 (P2 depth). Because F-01 already put session-keyed `messages` in state
(ADR-004), this is largely "stop clearing it / use the thread" — a behavior toggle, not a schema
change. Iteration 03 is independent of iteration 02.

## Requirements traced (from the PRD)
Req 25; acceptance criterion 22.

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: clarify-answer resolution and intent-with-context build on routing.
- **F-04 (generator)** — HARD dep: "adjust it" resolves against the prior workout in the session.
(Builds on F-01's session-keyed messages + checkpointer thread; the first-invocation rule prevents
accumulator doubling.)

## Unblocks (what waits on this)
- Nothing downstream in M1.

## Contracts touched
- **Graph state schema** (ADR-004) — exercises the session-keyed `messages` + per-session checkpointer
  thread; honors the pass-initial-state-only-on-first-invocation rule.

## Acceptance criteria (product behavior)
1. After generating a workout, "make it shorter" produces an adjusted workout reflecting the prior
   one, without the user restating the original request.
2. After the hub asks a clarifying question, the user's next message resolves the original intent
   against that exchange (no restating).
3. Re-invoking a session does not duplicate prior turns (no accumulator doubling).

## Testing requirements
- **Integration:** a two-turn session where turn 2 depends on turn 1's context produces a
  context-aware response (can use a fake model asserting the prior messages are present in the
  subgraph input). Assert no turn duplication across re-invocation.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)
