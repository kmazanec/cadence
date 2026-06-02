# ADR-019: Committed stretch features — model-eval harness, visible explanation panel, coach voice

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** yes · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

Beyond the PRD's M1 scope (and the already-promoted streaming + dual-path Postgres), the architecture
stage proposed research-grounded features that impress *this* evaluator (an AI-engineering grader at a
Future-style company), deepen the domain/stack, and fit the product trajectory. Three were committed;
they fold back into the PRD as a new version.

Serves (and extends): PRD req 24 (eval story), §7.7c/ADR-012 (explanation), reqs 19–20/ADR-013
(brand voice); seeds §10 cross-cutting eval pipeline + M5 explainability.

## Options considered

Four were proposed (eval harness, explanation panel, token/cost observability panel, coach-voice
polish). The token/cost panel was **not** committed (kept as a possible inclusion in the observability
log summary, ADR-017, but not a standalone feature) to protect the time budget. The other three were
committed.

## Decision

Commit three stretch features for M1:

1. **Tiny model-eval harness (routing split-test).** A runnable script scoring ~10–15 labeled routing
   cases across ≥2 configured models, reporting routing accuracy + latency per model. Turns req 24's
   "how I'd evaluate" from prose into runnable proof and demonstrates the model abstraction's
   split-test promise (ADR-007). Seeds the M-cross-cutting eval pipeline (§10).
2. **Visible "why these?" explanation panel.** Surface the relation-shaped explanation payload
   (ADR-012) as a clean, expandable panel on generated workouts ("avoided knee · paired both sides ·
   matched chest"). Previews M5's headline explainability and the knowledge-graph contraindication
   whitespace the market research found unshipped (MARKET.md). Mostly UI — the payload already exists.
3. **Coach voice/personality polish.** A subtle coach-personality system prompt + warm microcopy
   across all states (responses, clarifications, empty/recovery), extending the brand voice contract
   (ADR-013) into a cohesive personality. Plays to Future's human-coach brand.

## Rationale

(1) and (2) are the highest signal-per-hour: (1) makes the most-rewarded README section *provable* and
shows the model abstraction earning its keep; (2) makes the M5 differentiator **visible now** at low
cost because the payload is already designed — and it targets a market whitespace (no shipping consumer
product does KG-traceable injury contraindication). (3) is cheap brand polish that suits the company.
None require new infrastructure; all reuse decisions already made (ADR-007, ADR-012, ADR-013), which is
why they fit the 2–3h budget on top of core.

## Tradeoffs & risks

- **Stretch features compete with core for the time budget.** Mitigation: all three sit *below* P0/P1
  core in build order; the eval harness and voice polish are cuttable; the explanation panel is mostly
  reusing built payload. The PRD tiering governs cut-order.
- **The eval harness could over-grow** into a full framework. Mitigation: scope-capped at ~10–15 cases
  × 2 models, a single script — explicitly a seed, not the M-cross-cutting pipeline.

## Consequences for the build

- **Policy:** these are built after P0+P1 core; cut before any core if the budget tightens.
- **PRD:** reflected back into the PRD as a new version (committed stretch features), so the WHAT stays
  the source of truth.
- Reuses ADR-007 (per-role models → eval), ADR-012 (explanation payload → panel), ADR-013 (brand voice
  → personality). No new infrastructure.
