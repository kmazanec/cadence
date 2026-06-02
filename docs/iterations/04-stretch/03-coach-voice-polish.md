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
