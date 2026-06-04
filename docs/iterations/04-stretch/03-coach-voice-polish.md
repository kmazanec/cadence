# Feature: Coach voice/personality polish — stretch

**ID:** F-12 · **Iteration:** 04-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** Each agent answers in a serviceable but generic tone.
**After:** A cohesive warm coach personality runs across all states — responses, clarifying questions,
and empty/recovery states — extending the brand-voice contract into a recognizable character.

## How it fits the roadmap
Iteration 04 (stretch); cheap brand polish, cut-able. Plays to Future's human-coach brand.

## Requirements traced (from the PRD)
Req 18 (committed stretch); extends reqs 20 (voice) and the brand contract.

## Dependencies (must exist before this starts)
- **F-03 (coach)**, **F-04 (generator)**, **F-05 (logger)** — HARD deps: applies the personality
  across all three agents' user-facing copy.
(Extends the ADR-013 voice guidelines — contract-mediated for the brand tokens themselves.)

## Unblocks (what waits on this)
- Nothing.

## Contracts touched
- **Brand & voice design tokens** (ADR-013) — extends the voice guidelines into a cohesive personality
  (system prompts + microcopy across responses, clarifications, empty/recovery states).

## Acceptance criteria (product behavior)
1. Coach, generator, and logger responses share a consistent warm, encouraging, specific voice (in the
   spirit of "Nice lift — you recovered quickly between sets"), never clinical/robotic.
2. Clarifying questions and empty/recovery states carry the same voice ("I don't have sled exercises
   in your kit — want to go dumbbell instead?").
3. The voice is demonstrably distinct from a default assistant tone (checkable against the BRAND.md
   voice guidelines).

## Testing requirements
- Largely qualitative/checklist (voice is partly subjective). Where feasible, assert that
  clarification/recovery copy is non-empty and routed through the voice layer rather than hardcoded
  generic strings.

## Manual setup required
- Human review of the voice against the brand contract (subjective polish).

## Implementation notes (filled in by the building agent)

### Chunk 1 — Backend voice layer wiring [x]

`app/voice.py` was present as a frozen contract stub on `build/04-stretch`. The
implementation wired all four consumers:

- **`agents/coach/graph.py`**: `COACH_SYSTEM_PROMPT` is now `VOICE_PREAMBLE + " " + <task tail>`,
  keeping the functional coaching directive intact while making the persona definition come from one
  place. This is the ADD-only pattern: the task tail ("Answer the user's fitness question…") is
  preserved beneath the preamble.

- **`graph/routing.py`** (`decide_route`): The fallback `ClarificationPrompt` copy now matches
  `voice.clarification_fallback()` exactly ("Tell me a bit more about what you'd like to do." with
  the same three options). A direct import was avoided to prevent the circular import —
  `voice.py` already imports `ClarificationPrompt` from `routing.py`. The copies are kept in sync
  via the test `test_decide_route_fallback_matches_voice_clarification_fallback`. A voice sentence
  was added to the tail of `ROUTER_SYSTEM_PROMPT` ("Cadence is a warm training partner, so frame
  the clarifying question conversationally — never robotically.").

- **`graph/hub.py`** (`_clarify_node`): Now calls `clarification_fallback()` directly rather than
  inlining its own `ClarificationPrompt`. The old inline literal is gone.

- **`graph/hub.py`** (`_generator_boundary_node`): Generator retry exhaustion now emits
  `AIMessage(content=GENERATOR_FAILURE_MESSAGE)` from the voice layer instead of the old generic
  string.

- **`api/chat.py`**: Error frame now emits `ErrorEvent(message=RECOVERY_ERROR_MESSAGE)` from the
  voice layer; the old `"Something went wrong — please try again."` is gone.

17 new tests in `tests/test_voice_layer.py` verify: non-empty constants, partnership markers,
absence of old generic strings, preamble composition in the coach prompt, voice-layer alignment for
both `decide_route` and `_clarify_node`, generator failure copy, and the chat error frame import.

### Chunk 2 — Frontend chrome + BRAND.md [x]

- **`ChatApp.tsx`**: Three microcopy strings updated:
  - Empty state: "What are we working on today? Ask a question, build a workout, or log a session."
    (replaces the transactional original; "we" carries the partnership voice)
  - Loading placeholder: "On it…" (replaces "Thinking…"; avoids robot-introspection phrasing)
  - SSE client-side error fallback: on-voice copy aligned with `RECOVERY_ERROR_MESSAGE` wording

- **`BRAND.md`**: Added a "Single source of voice copy (backend)" subsection documenting
  `app/voice.py` as the canonical location for backend user-facing strings, so future contributors
  know where to add copy rather than inlining new literals.

Generator and logger emit cards, not prose — their AC1 contribution is the preamble future-proofing
(the preamble sits at the top of every prompt slot they'd use) plus the failure/fallback copy for
the hub-level boundary nodes. Overall warmth/cohesion and the card-agents' prose are human-review
against BRAND.md.
