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

- **Coach subgraph placement:** `graph.py` added to `backend/app/agents/coach/`; exports `COACH_SYSTEM_PROMPT` (module-level constant) so tests can assert voice-directive presence without invoking the model.
- **Voice prompt construction:** The system prompt encodes each BRAND.md do/don't directive as a sentence — conversational/direct/confident/partnership/results-focused, never clinical/robotic/hedged/disclaimer-heavy. Tests assert substring presence from each group.
- **Explanation note:** Emitted in `_coach_boundary_node` in `hub.py`, not in the subgraph itself, because `CoachState` carries no `explanation` field (HubState owns the explanation list). Uses `claim='note'`, `relation='name_match'` (frozen vocab), `subject='coach'`, `detail='answered by coach'`. Exactly one note per coach turn.
- **Hub wiring:** `hub.py` reproduced in this branch (forked from contracts-only base); coach boundary and response-assembly nodes connect without change from the F-01 pattern. No new node names introduced.
- **Live smoke test:** skipped unless `OPENROUTER_API_KEY` is set; asserts at least one primary deadlift muscle is mentioned. Never gates CI.

### Build outcome

- **Shippable:** yes. Integrated via cherry-pick onto `integration/01-p0-core`. Predicted convergence resolved in place: this branch forked off the contracts-only base, so its `hub.py`/`coach/graph.py` collided with F-02's real router and F-03's own BRAND voice prompt — resolved by keeping the real router (F-02) and the BRAND voice prompt + coach explanation note (F-03). Linear history preserved.
- **Acceptance:** met. PRD §6 #1 (coach answers a fitness question conversationally) satisfied; the coach subgraph is reached via the unique `coach_boundary` node and emits exactly one `claim='note'` explanation. Integrated suite includes the coach conversation + node tests.
- **Unresolved gating:** none.
- **Deferred (low):** voice quality is asserted by prompt-substring checks, not by judging live model output; the live answer smoke is skipped offline.
- **QA evidence:** "139 passed, 4 skipped" (full suite, offline); e2e smoke routed a coach question and emitted `{"type":"route","route":"coach"}` then `{"type":"done"}`.
