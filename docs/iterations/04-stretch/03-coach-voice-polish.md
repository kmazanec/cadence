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

## Build plan (planned 2026-06-03 · kmaz-plan-iteration)

**Status:** Planned — pending human approval (see `BUILD-PLAN-04-stretch.md`).
**Contract verdict:** **No typed shared-contract change** (SSE/state/schemas untouched).
EXTENDS the ADR-013 **voice guideline** (a copy/prompt contract) by centralizing voice into a new
internal `app.voice` module. Contract-safe; builds independently of F-10/F-11.

### Grounding — where voice lives vs. is missing today
| Location | File:line | State today |
|---|---|---|
| Coach prompt (gold standard) | `coach/graph.py:21` `COACH_SYSTEM_PROMPT` | Strong, on-brand — the reference bar |
| Generator prompt | `generator/graph.py:47` `_SYSTEM_PROMPT` | Functional; emits a **card**, not prose |
| Generator-failure copy | `graph/hub.py:300` `_generator_boundary_node` | Hardcoded generic |
| Logger extraction prompt | `logger/graph.py:53` `_EXTRACTION_SYSTEM_PROMPT` | Functional parser; emits a **card** |
| Logger resolver prompt | `logger/resolver.py:120` | Internal number-picker; never user-facing |
| Clarify fallback (hub) | `graph/hub.py:390` `_clarify_node` | Hardcoded generic Q+options |
| Clarify fallback (routing) | `graph/routing.py:101` `decide_route` | **Duplicate** hardcoded generic Q+options |
| Router clarification prompt | `graph/routing.py:31` `ROUTER_SYSTEM_PROMPT` | Asks for options, **no voice guidance** |
| Recovery/error frame | `api/chat.py:163` | Hardcoded generic "Something went wrong…" |
| FE chrome microcopy | `chrome/AppHeader.tsx`, `chat/ChatApp.tsx`, `chrome/QuickActions.tsx` | Mostly **already on-voice** |

### Lens: Architect
- **The seam — one backend module `backend/app/voice.py`** as the single source of truth:
  - **`VOICE_PREAMBLE`** — the core personality directive distilled from `COACH_SYSTEM_PROMPT` +
    BRAND.md "## Voice" (conversational/direct, confident, partnership "let's/we/you've got this",
    results-focused; never clinical/hedged/robotic). Every agent prompt composes from it.
  - **Microcopy** currently hardcoded: `clarification_fallback()` (the *single* definition both
    `_clarify_node` and `decide_route` import — collapses today's duplication), enriched to be
    on-voice; `GENERATOR_FAILURE_MESSAGE`; `RECOVERY_ERROR_MESSAGE`.
- **Compose, don't duplicate:** Coach = `VOICE_PREAMBLE` + task tail (it's the preamble's origin).
  Generator/Logger prepend the preamble — **honest caveat:** both emit *cards*, so the preamble has
  near-zero happy-path surface; their real user-visible voice is the **fallback/empty copy**.
  **Do NOT touch `resolver.py`** (internal, never user-facing — voice there is pure risk).
- **Wire consumers to the module:** `_clarify_node` + `decide_route` → `clarification_fallback()`;
  `_generator_boundary_node` → `GENERATOR_FAILURE_MESSAGE` (optionally warm the summary line);
  `chat.py` error frame → `RECOVERY_ERROR_MESSAGE`. Add **one voice sentence** to
  `ROUTER_SYSTEM_PROMPT` (model-generated clarifications are steerable only by prompt).
- **Frontend:** chrome copy is already on-voice — **audit + light polish in place**, no parallel
  microcopy framework for ~4 strings (optional `frontend/src/brand/copy.ts` only if it reads
  cleaner; `src/brand/` already exists).

### Lens: Reuse
Reuse `COACH_SYSTEM_PROMPT` as the source text for `VOICE_PREAMBLE` (extract the shared spine —
don't write new voice prose); reuse BRAND.md "## Voice" as the spec of record; **collapse the
clarification fallback's two copies (`hub.py:390` + `routing.py:101`) into one
`clarification_fallback()`**. New: `app.voice` + a voice-marker test helper. Voice text appears
**once** (the preamble), never re-typed per prompt.

### Lens: Contrarian
The AC is **partly subjective**. Cheapest honest win: centralize microcopy + compose prompts from
one preamble (mechanical/objective), plus a few **objective** tests — clarification/recovery copy
is non-empty, **sourced from `app.voice`** (assert consumers return the module constant, not an
inline literal), contains partnership markers, and is **not** the bare old generic string.
**Refuse (YAGNI):** templating/i18n, an LLM-rewrites-all-copy layer, a runtime "voice linter," a
full FE microcopy framework. **Explicitly NOT objectively testable** (→ human-review checklist,
which the spec permits): whether model outputs *feel* warm, overall cohesion, subjective copy
quality. **Risk — prompt-perturbation:** editing the four system prompts can ripple into
prompt-sensitive tests (router classification, generator tool-loop, logger extraction).
**Mitigation: ADD voice only, never reword functional directives; run the FULL suite.**
Router-generated clarifications carry voice only via prompt guidance (only partly controllable).

### Decision
Create `backend/app/voice.py` holding `VOICE_PREAMBLE` (distilled from the coach prompt + BRAND.md)
and the centralized on-voice microcopy (`clarification_fallback()`, `GENERATOR_FAILURE_MESSAGE`,
`RECOVERY_ERROR_MESSAGE`). Refactor coach to `VOICE_PREAMBLE` + task tail; prepend the preamble to
the generator + logger extraction prompts (ADD only, never reword), leaving `resolver.py` untouched;
add one voice sentence to the router prompt. Rewire `_clarify_node`, `decide_route`,
`_generator_boundary_node`, and `chat.py`'s error frame to pull from `voice.py`. Frontend chrome is
audit-and-polish, no new framework. Tests assert relocated copy is non-empty, sourced from the
voice layer, carries partnership markers, and differs from the old generic string; the rest is a
human-review checklist.

### Contract touchpoints
- **Typed shared contracts (SSE / HubState / schemas): NO CHANGE.** Only the *string values*
  flowing through `ClarificationPrompt`/`ErrorEvent` move into `voice.py`; the `>= 2 options`
  invariant of `ClarificationPrompt` is preserved.
- **EXTENDS ADR-013 voice guideline** (copy/prompt contract): centralizes the voice preamble +
  clarification fallback + generator-failure + recovery message under `app.voice`; adds a voice
  sentence to the router prompt.
- **No frozen-signature change.** `decide_route(...) -> (Route|None, ClarificationPrompt|None)` and
  all node signatures unchanged. Only new symbol: the internal, **non-shared** `app.voice` module.
- **Reconciliation verdict: contract-safe; builds independently of F-10/F-11.**

> Coordination note: F-12 edits `routing.py` (`decide_route` copy + a voice sentence in
> `ROUTER_SYSTEM_PROMPT`); F-10 also edits `routing.py` (adds `classify`, refactors the router
> node). **Adjacent, non-conflicting** — F-10 leaves prompt text intact; F-12 only adds voice copy.
> Build in either order; trivial same-file merge if concurrent.

### Build checklist
- [ ] **Create `backend/app/voice.py`**: `VOICE_PREAMBLE` (from `COACH_SYSTEM_PROMPT` + BRAND.md DO/DON'T); `clarification_fallback() -> ClarificationPrompt` (Q + ≥2 options, on-voice); `GENERATOR_FAILURE_MESSAGE`; `RECOVERY_ERROR_MESSAGE`. *(Watch import cycle with `routing.ClarificationPrompt` — one-directional import, or return a `(question, options)` tuple callers wrap.)* — AC2, AC3, testing req
- [ ] **Coach** (`coach/graph.py`): `COACH_SYSTEM_PROMPT = VOICE_PREAMBLE + <coach task tail>`; behaviour identical. — AC1
- [ ] **Generator** (`generator/graph.py`): prepend `VOICE_PREAMBLE` to `_SYSTEM_PROMPT`; do NOT reword tool-loop directives. — AC1 (limited: card output)
- [ ] **Logger** (`logger/graph.py`): prepend `VOICE_PREAMBLE` to `_EXTRACTION_SYSTEM_PROMPT`; leave `resolver.py` untouched. — AC1 (limited)
- [ ] **Router prompt** (`routing.py`): one voice sentence steering model-generated clarifications; keep classification directives intact. — AC2 (partial, model-side)
- [ ] **Rewire `_clarify_node`** (`hub.py:386`) → `voice.clarification_fallback()`. — AC2
- [ ] **Rewire `decide_route`** (`routing.py:101`) → `voice.clarification_fallback()` (collapses duplication). — AC2
- [ ] **Rewire `_generator_boundary_node`** (`hub.py:300`) → `voice.GENERATOR_FAILURE_MESSAGE`; optionally warm summary line (`hub.py:320`). — AC2 (empty/recovery)
- [ ] **Rewire `chat.py` error frame** (`chat.py:163`) → `voice.RECOVERY_ERROR_MESSAGE`. — AC2 (recovery)
- [ ] **Audit + lightly polish FE chrome** (`AppHeader.tsx`, `ChatApp.tsx`, `QuickActions.tsx`) vs BRAND.md; change only what reads generic. Optional `frontend/src/brand/copy.ts`. — AC1, AC3 (human-review-led)
- [ ] **Backend tests** (`tests/voice/`): clarification_fallback non-empty + ≥2 options + partnership markers + ≠ old generic; `_clarify_node`/`decide_route` copy equals the module constant (sourced, not inline); `GENERATOR_FAILURE_MESSAGE`/`RECOVERY_ERROR_MESSAGE` non-empty + markers + ≠ old generic; `_generator_boundary_node` (workout=None) emits `GENERATOR_FAILURE_MESSAGE`. Add the shared voice-marker helper. — testing req, AC2, AC3
- [ ] **Update BRAND.md "## Voice"** if personality is sharpened; note prompts/microcopy now source from `app.voice`. — AC3
- [ ] **Run FULL suites** (prompt edits can ripple): `cd backend && python -m pytest` · `cd frontend && npm test` · `cd frontend && npm run typecheck`.

**AC coverage:** AC1 → coach refactor + generator/logger preamble + FE polish (partly objective
for coach prose, **mostly human-review** for card agents); AC2 → clarify/decide_route/generator-
fallback/chat-error rewiring + tests (**objective**: sourced-from-voice + markers + non-generic;
router-generated clarifications **partly** controllable); AC3 → voice-marker tests (objective
floor) + human-review vs BRAND.md; Testing req → fully covered by the backend voice tests.

### Files
**CREATE:** `backend/app/voice.py`; `backend/tests/voice/test_voice_copy.py` (+ `_markers.py`
helper); *(optional)* `frontend/src/brand/copy.ts`.
**MODIFY:** `backend/app/agents/coach/graph.py`; `backend/app/agents/generator/graph.py`;
`backend/app/agents/logger/graph.py`; `backend/app/graph/routing.py`; `backend/app/graph/hub.py`;
`backend/app/api/chat.py`; `frontend/src/chat/ChatApp.tsx`; `frontend/src/chrome/AppHeader.tsx`;
`frontend/src/chrome/QuickActions.tsx`; `frontend/BRAND.md`.

### Risks / assumptions
- **Subjectivity (spec-acknowledged):** objective floor = sourced-from-voice + non-empty + markers
  + ≠ generic; the rest is a human-review pass against BRAND.md.
- **Prompt-perturbation:** ADD voice only, never reword functional directives; run the full backend
  suite (touches `test_router_node.py`, generator tool-loop, logger extraction).
- **Import-cycle risk** between `voice.py` and `routing.py` — resolve one-directionally or via a
  plain tuple return.
- **Generator/logger emit cards, not prose** — their AC1 warmth is fallback/preamble + future-
  proofing + human-review, not a testable behaviour change today (stated honestly).

## Implementation notes (filled in by the building agent)
