# ADR-013: Brand & voice design contract — Future-inspired tokens for the React/Tailwind UI

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The branded chat UI is P0 and graded on reading as a premium Future experience, demonstrably distinct
from a default chatbot (PRD reqs 19–21, criterion 17). The PRD flagged (§8.7) that concrete brand
tokens were owed before styling, and the build stage expects a **binding brand/voice design contract**.
The stack is React + Vite + Tailwind (ADR-001). This ADR captures the tokens (from a direct read of
future.co + MARKET.md) so "on-brand" is a checklist, not an opinion (§8.6).

Serves: PRD reqs 19–21, criterion 17; §8.6 (brand fidelity), §8.7 (brand-token capture owed).

## Options considered

Not a stack choice (settled in ADR-001) — this records the *brand contract*. The alternative was to
leave brand "intent" vague and decide at build; rejected because §8.6/§8.7 require concrete tokens so
fidelity is verifiable, not subjective.

## Decision

The UI implements the following **design contract** as Tailwind theme tokens. Where a value could not
be read exactly from the live site, it is flagged and a defensible default is given (to be confirmed
against the live site during build — §8.7 brand pass continues into build).

**Color**
- `background`: `#FFFFFF` / near-white `#FAFAFA` (generous white space).
- `text-primary`: dark charcoal `#1A1A1A`; `text-secondary`: mid-gray `#6B7280`.
- `accent` (CTAs, active states): **teal/cyan-green** — *exact hex not exposed in site HTML (low
  confidence)*; default `#00C2A8`-family, **confirm against live site during build**.
- `border`/dividers: subtle grays (`#E5E7EB`).
- Optional subtle background gradients in hero/section areas.

**Typography**
- Modern sans-serif system/`Inter`-style stack. Headings weight **600–700**; body **400**.
- Sizes: hero ~48–56px, section ~32–40px, body ~16–18px. Generous line-height.

**Shape & spacing**
- Rounded-rectangular buttons, generous padding, **solid accent fill**, high contrast on white.
- Cards with rounded corners for structured content (workout/log); breathing room between sections;
  not cramped. Single-column, responsive, hero-focused.

**Voice (coach copy)**
- Conversational, confident, partnership-oriented, results-focused — never clinical or robotic.
- Real Future phrasings to echo (sourced): *"train for what's next"*, *"Never train alone — your
  coach checks in, monitors your progress, and holds you accountable"*, and the assistant's own coach
  voice in the spirit of *"Nice lift — you recovered quickly between sets."*
- Apply to: assistant responses, clarifying questions ("Want me to log that, or adjust your plan?"),
  empty/recovery states ("I don't have sled exercises in your kit — want to go dumbbell instead?").

## Tradeoffs & risks

- **Exact accent hex is low-confidence** (not in site HTML). Mitigation: flagged; build does a final
  eyedropper pass against the live site before locking the token. Using a teal-family default keeps
  the design coherent meanwhile.
- **Brand fidelity is partly subjective.** Mitigation: these tokens convert it to a checklist
  (criterion 17 validated against this contract); a build-stage design pass (and optional
  design-auditor) checks against them.
- **No dedicated COMPANY.md brand pass was run** (§8.7). Mitigation: this ADR *is* the brand contract
  the build consumes; if a fuller COMPANY.md is later produced, its brand section must stay consistent
  with this ADR.

## Consequences for the build

- **Contract (brand/voice design tokens).** The binding design contract for all UI/copy.
  - **Source of truth:** `frontend/tailwind.config.js` (theme tokens) + a short
    `frontend/BRAND.md` (voice guidelines) derived from this ADR.
  - **Shape (initial):** the color/type/shape/voice tokens above as Tailwind `theme.extend` entries +
    voice do/don't examples.
  - **Exhaustive consumers:** every UI component (message bubbles, workout card, log card,
    clarification prompt, empty/error states) and all assistant/clarification copy.
- **Policy:** all UI styling uses theme tokens, not ad-hoc values; all assistant-facing copy follows
  the voice guidelines. The accent hex is confirmed against the live site before final styling.
- **Policy:** structured content (workouts, logs) renders as branded cards, never raw JSON
  (req 21, criterion 16).
