# Feature: Coach sub-agent

**ID:** F-03 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** The coach route reaches only the F-01 stub subgraph.
**After:** Coach-routed messages get a real, conversational fitness/training knowledge answer in an
on-brand coach voice, and the coach serves as the safe destination for general conversation.

## How it fits the roadmap
Iteration 01; builds concurrently with F-04/F-05 once F-01's contracts are frozen. Hard-depends only
on F-01.

## Requirements traced (from the PRD)
Reqs 6–7; acceptance criterion 16 (coach question → appropriate answer in the UI).

## Dependencies (must exist before this starts)
- **F-01 (walking skeleton)** — HARD dep: replaces the stub coach subgraph with a real one using the
  frozen `CoachState`, boundary adapter, and `get_model('coach')`.
(Does NOT hard-depend on F-02: it can be built against the frozen contracts and tested by invoking the
coach subgraph directly; F-02 wires real routing to it, but that's contract-mediated.)

## Unblocks (what waits on this)
- F-12 (coach voice polish) — extends the coach's voice/personality.

## Contracts touched
- **Graph state schema** (ADR-004) — implements `CoachState` + its boundary adapter.
- **Model config** (ADR-007) — uses `get_model('coach')`.
- **Brand & voice tokens** (ADR-013) — coach responses follow the voice guidelines.
- **Reason/explanation payload** (ADR-012) — populates `explanation` lightly (e.g. a `note` reason).

## Acceptance criteria (product behavior)
1. "What muscles does a deadlift work?" returns a correct, conversational answer naming the relevant
   muscles, in a warm coach voice (not clinical/robotic).
2. General non-generation, non-logging conversation routes to and is handled by the coach gracefully.
3. The coach is a separately-compiled subgraph with a unique node name (not an inlined function).
4. The response renders in the branded UI as readable text.

## Testing requirements
- **Integration:** invoking the coach subgraph with a knowledge question returns a non-empty answer;
  can use a fake model returning a canned answer to assert wiring + adapter + voice-prompt application
  deterministically.
- A minimal live smoke check that a real model produces a relevant answer (optional/minimal).

## Manual setup required
None beyond F-01.

## Implementation notes (filled in by the building agent)
