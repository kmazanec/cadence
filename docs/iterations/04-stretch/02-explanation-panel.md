# Feature: "Why these?" explanation panel — stretch

**ID:** F-11 · **Iteration:** 04-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** The relation-shaped explanation payload is carried but not surfaced.
**After:** Generated workouts show a clean, expandable "why these?" panel ("avoided knee · paired both
sides · matched chest"), previewing M5's headline explainability.

## How it fits the roadmap
Iteration 04 (stretch). Mostly UI — the payload already exists (ADR-012). Cut first under pressure.

## Requirements traced (from the PRD)
Req 17 (committed stretch); previews §10 M5 explainability.

## Dependencies (must exist before this starts)
- **F-04 (generator)** — HARD dep: renders the generator's `included`/`matches_target` reasons.
- **F-07 (injury+bilateral)** — HARD dep: renders the `excluded`/`loads_joint` and
  `added`/`bilateral_pair_of` reasons (the most compelling "why" content). This makes F-11 cross
  iteration 02 → only buildable after F-07 ships.

## Unblocks (what waits on this)
- Nothing.

## Contracts touched
- **Reason/explanation payload** (ADR-012) — consumes the structured reasons for rendering.
- **SSE envelope** (ADR-002) — the explanation arrives in the `structured` payload.
- **Brand tokens** (ADR-013) — the panel follows the brand styling.

## Acceptance criteria (product behavior)
1. A generated workout (especially with an injury constraint) shows an expandable panel listing the
   structured reasons in human-readable form (exclusions, pairings, target matches).
2. The panel is styled on-brand and collapsed by default (subtle affordance).
3. With no notable reasons, the panel degrades gracefully (hidden or minimal).

## Testing requirements
- **Component/integration:** given a workout payload with reasons, the panel renders the expected
  human-readable lines; an injury-excluded workout shows the exclusion reason.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)
