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

## Build plan (planned 2026-06-03 · kmaz-plan-iteration)

**Status:** Planned — pending human approval (see `BUILD-PLAN-04-stretch.md`).
**Contract verdict:** Owns the **only** iteration-04 frozen-contract change — one **additive**
SSE variant (`ExplanationEvent`), mirrored backend + frontend. The Reason payload (ADR-012)
shape is UNCHANGED — it is merely transported over SSE for the first time.

### The gap this feature closes
The reasons are **already built** in `hub._generator_boundary_node` (lines ~235–294:
`included·matches_target`/`equipment_match`, `added·bilateral_pair_of`, `excluded·loads_joint`)
and flow into `state["explanation"]`, which `assemble_response` already returns as
`ChatResponse.explanation` (`response_assembly.py:47`). **But explanation reaches only the
non-streaming envelope — the SSE stream never carries it, and the live UI consumes SSE only.**
So this feature is **transport + render only**; `hub.py` is untouched (no reason-building work).

### Lens: Architect
- **Data path (target):** `state["explanation"]` → (post-stream)
  `assemble_response(snapshot.values).explanation` → **new `ExplanationEvent` on SSE** →
  `sseClient` → `reduceSSE` → **new `ChatState.explanation: Reason[]`** → `ChatApp` carries it
  onto the `Message` → `WorkoutCardView` renders `<ExplanationPanel>` via the pure
  `explanationLines()` humanizer.
- **SSE shape — a NEW `explanation` event variant, NOT folded into `structured`.**
  `StructuredEvent.payload` is a deliberately closed `WorkoutPayload | LogPayload` union; folding
  in couples two concerns and forces log turns to carry an unused field. `route` and
  `clarification` are already separate events read from committed state — explanation is the same
  kind of thing. A separate event keeps the structured union pure and is the idiomatic match.
- **Emit point:** in `chat.py`, right after the existing post-stream `StructuredEvent` emit, from
  the **same** `assemble_response(snapshot.values)` object, gated on truthiness:
  `if response.explanation: yield encode_sse(ExplanationEvent(reasons=response.explanation))`.
  Gating means coach/log turns emit nothing → graceful degradation at the source.
- **Humanizer — pure `frontend/src/render/explanationLines.ts`,**
  `explanationLines(reasons): string[]`, with **mandatory dedupe/summarize** (the generator emits
  one reason *per muscle group* AND *per equipment item*, so a 6-exercise workout yields 30+
  triples). Group by `(claim, relation)`, collapse to distinct `object` values, one summary line
  per group: `excluded·loads_joint`→"avoided knee"; `added·bilateral_pair_of`→"paired both sides";
  `included·matches_target`→"matched chest, back"; `equipment_match`→"used dumbbell" (optional/
  lower priority); `note` (coach triple) → ignored.
- **Panel `frontend/src/render/ExplanationPanel.tsx`:** native `<details>` disclosure, **collapsed
  by default**, on-brand tokens (`bg-surface-sunken`, `text-accent-deep`, `font-subheading`,
  `rounded-button`, `border-border` — never hardcoded). Returns `null` when `explanationLines` is
  empty (hidden). Renders inside `WorkoutCardView` → **workout turns only** (matches spec).

### Lens: Reuse
Reuse (no new shape): `Reason`/`Claim`/`Relation` (already mirrored both sides), the
exhaustive-switch + `assertNever` pattern in `dispatch.ts`, the `encode_sse` exhaustive match,
brand token classes from `WorkoutCardView`, the post-stream `assemble_response` read in `chat.py`,
vitest test conventions. New (small): `explanationLines.ts`, `ExplanationPanel.tsx`,
`ExplanationEvent`/`{type:"explanation"}` variant, `ChatState.explanation`. **No backend
reason-building** — `hub.py` is untouched.

### Lens: Contrarian
A separate `ExplanationEvent` is the cheapest *correct* path (~10 lines backend, ~6 frontend) and
avoids structured-union pollution. **Graceful degradation (AC3):** hide on empty
`explanationLines` (covers no-reasons turns AND `note`-only coach triples) — the component returns
`null`. **The `included·matches_target` explosion is real (`hub.py:260–278`) → summarization is
load-bearing, not cosmetic**; an un-summarized panel fails AC2. Workout turns only (spec).
**YAGNI:** no per-reason icons/animation/expand-persistence — a plain `<details>` is enough.
The `assert_never`/`assertNever` exhaustiveness will fail the build if a variant arm is forgotten
— that's the safety net, budget for adding both arms.

### Decision
Add an additive **`ExplanationEvent`** to the closed SSE union on both sides, emitted once
post-stream in `chat.py` from the same `assemble_response` object that emits `structured`, gated
on non-empty `explanation`. Reduce it into a new `ChatState.explanation: Reason[]`, thread it
through `ChatApp` onto the message, and render it inside `WorkoutCardView` as a collapsed on-brand
`<details>` panel whose lines come from a new pure `explanationLines()` humanizer that
dedupes/summarizes. ADR-012 Reason shape unchanged — only transported; ADR-002 SSE gets one
backward-compatible new variant.

### Contract touchpoints
**READ (unchanged):** ADR-012 `Reason`/`Claim`/`Relation` (rendered, shape unchanged);
ADR-013 brand tokens.
**EXTEND — the one frozen-contract change (ADR-002 SSE, additive):**
- Backend `streaming.py`:
  `class ExplanationEvent(BaseModel): type: Literal["explanation"] = "explanation"; reasons: list[Reason]`
  — import `Reason` from `..graph.explanation`; add `| ExplanationEvent` to `SSEEvent`; add
  `| ExplanationEvent()` to the `encode_sse` match (exhaustive).
- Frontend `types/api.ts`: add `| { type: "explanation"; reasons: Reason[] }` to `SSEEvent`.
- Frontend `dispatch.ts`: add `explanation: Reason[]` to `ChatState` (default `[]` in
  `initialChatState`) + `case "explanation": return { ...state, explanation: event.reasons };`.

**This signature must land identically on both sides before per-side work** (see
`BUILD-PLAN-04-stretch.md` frozen contracts). Purely additive, backward compatible (unknown
`type` is ignored; emitted only on workout turns with reasons).

### Build checklist (ordered, test-first where it fits)
**Backend — SSE transport**
- [ ] Add `ExplanationEvent` to `streaming.py` (import `Reason`); extend `SSEEvent` union + `encode_sse` match (keep exhaustive).
- [ ] In `chat.py`, after the `StructuredEvent` emit, add gated `if response.explanation: yield encode_sse(ExplanationEvent(reasons=response.explanation))`; import `ExplanationEvent`.
- [ ] Backend test: drive a workout-with-injury request through the stream; assert an `{"type":"explanation","reasons":[...]}` frame appears with an `excluded`/`loads_joint` reason; assert a coach/log turn emits NO explanation frame.

**Frontend — type mirror + reducer**
- [ ] Mirror the variant in `types/api.ts` `SSEEvent`.
- [ ] Add `explanation: Reason[]` to `ChatState` + `initialChatState` default `[]`; add `case "explanation"` to `reduceSSE`; import `Reason`. Update `dispatch.test.ts`.

**Frontend — humanizer (pure, test-first)**
- [ ] Write `explanationLines.test.ts` first: the three example lines; many `included·matches_target` collapse to one line of distinct muscle groups; `[]`→`[]`; `note`-only→`[]`.
- [ ] Implement `explanationLines.ts` (group by `(claim, relation)`, collapse distinct objects, summary phrasing).

**Frontend — panel (component test)**
- [ ] Write `ExplanationPanel.test.tsx`: renders expected lines; injury-excluded workout shows the exclusion line; collapsed by default (`<details>` not `open`); empty → renders nothing.
- [ ] Implement `ExplanationPanel.tsx` (collapsed `<details>` "Why these?", on-brand, `null` when empty).

**Frontend — wiring**
- [ ] Render `<ExplanationPanel reasons={...} />` inside `WorkoutCardView` (add `reasons?: Reason[]` prop, default `[]`).
- [ ] Thread `explanation` through `ChatApp`: add to `Message` type, copy `explanation: chatState.explanation` in `handleEvent`, pass to `WorkoutCardView`. Update `ChatApp.test.tsx`.

**Validation**
- [ ] `cd backend && python -m pytest`
- [ ] `cd frontend && npm test`
- [ ] `cd frontend && npm run typecheck`

**AC coverage:** AC1 → ExplanationPanel + explanationLines (+ `ChatApp.test.tsx` integration);
AC2 → brand tokens + `<details>` not `open` (collapsed assertion); AC3 → empty/`note`-only → `[]`
→ panel `null` + chat.py emit gated; Testing req → `explanationLines.test.ts` +
`ExplanationPanel.test.tsx` + backend stream test.

### Files
**CREATE:** `frontend/src/render/explanationLines.ts` (+ `.test.ts`);
`frontend/src/render/ExplanationPanel.tsx` (+ `.test.tsx`);
backend stream test (`backend/tests/.../test_chat_stream_explanation.py` or extend an existing
chat-stream test module).
**MODIFY:** `backend/app/api/streaming.py`; `backend/app/api/chat.py`;
`frontend/src/types/api.ts`; `frontend/src/render/dispatch.ts` (+ `dispatch.test.ts`);
`frontend/src/render/WorkoutCardView.tsx`; `frontend/src/chat/ChatApp.tsx` (+ `ChatApp.test.tsx`).

### Risks / assumptions
- **Only iteration-04 feature with a real frozen-contract change** — the `ExplanationEvent`
  signature must match on both sides before per-side work; purely additive + backward compatible.
- **Summarization is load-bearing** (per-muscle/per-equipment explosion); the humanizer dedupe is
  the crux of UI quality and AC2.
- Exhaustiveness (`assert_never`/`assertNever`) fails the build if an arm is forgotten — intended.
- No `hub.py` reason-building work. Phrasing ("avoided" vs "skipped") and whether to show
  `equipment_match` are isolated copy decisions in `explanationLines.ts`.

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
