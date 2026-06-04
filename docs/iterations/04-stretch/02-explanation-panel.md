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

## Implementation notes

### Transport
`chat.py` emits `ExplanationEvent(reasons=response.explanation)` immediately after `StructuredEvent`,
gated on `if response.explanation`. The gate means coach and log turns emit nothing — graceful
degradation at the source, not the receiver. `assemble_response` already set `explanation` from
`state["explanation"]`; no hub change needed.

### Humanizer (`explanationLines.ts`)
Groups by `(claim, relation)`, collects distinct `object` values per group, emits one line per
group in priority order: excluded/loads_joint → added/bilateral_pair_of → included/matches_target
→ included/equipment_match. `note` reasons are silently skipped (coach-internal). Reasons with
`object: null` are also skipped. The dedupe step prevents the per-muscle/per-equipment explosion
(30+ triples for a 6-exercise workout) from flooding the panel.

### Panel (`ExplanationPanel.tsx`)
Native `<details>/<summary>` — zero JS state, correct semantic disclosure. `not open` by default
per spec. Returns `null` when `explanationLines` is empty, hiding the panel on non-workout turns.
Brand tokens: `bg-surface-sunken`, `text-accent-deep`, `font-subheading`, `rounded-button`,
`border-border`.

### Wiring
`ChatState.explanation: Reason[]` (default `[]`) accumulates the payload. `reduceSSE`
`case "explanation"` stores it. `ChatApp` threads it onto `Message.explanation`, passes it to
`WorkoutCardView` as the `reasons` prop. `WorkoutCardView.reasons` defaults to `[]` so existing
callers are unaffected.

### Tests
- 3 backend SSE transport tests (`test_explanation_stream.py`): event emitted on workout turn with
  reasons, not emitted on coach turn, appears before `done`.
- 9 humanizer unit tests (`explanationLines.test.ts`): empty, note-only, each claim type,
  many-to-one collapse, cross-type, null-object safety.
- 8 panel component tests (`ExplanationPanel.test.tsx`): renders nothing when empty/note-only,
  `<details>` collapsed by default, each reason type, `<summary>` with "Why these?".
- Dispatch tests updated: `explanation` event handled, `initialChatState` has `[]`.
- 2 ChatApp integration tests: explanation panel appears on workout turn; absent on coach turn.

### Build outcome

- **Shippable:** yes. Cherry-picked clean onto `integration/04-stretch`. Shares `chat.py` and
  `ChatApp.tsx` with F-12; the predicted textual convergence auto-merged (disjoint regions) with no
  manual resolution needed.
- **Acceptance:** met. PRD req 17 (committed stretch, previews M5 explainability) traced; AC 1-3
  satisfied — expandable on-brand panel collapsed by default, lists human-readable reasons, hidden
  when there are none.
- **Unresolved gating:** none.
- **Deferred:** none.
- **QA evidence:** frontend "51 passed (7 files)" incl. `ExplanationPanel.test.tsx` 8 + ChatApp
  integration; backend `test_explanation_stream.py` confirms the `ExplanationEvent` frames before
  `done`. Live SSE stack returns the centralized error copy on the failure path, confirming wiring.
