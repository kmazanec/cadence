# ADR-012: Relation-shaped explanation payload on responses (M1 populates trivially, M5 enriches)

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

PRD §7.7c: agent responses should carry a structured "why"/explanation payload — even if M1 populates
it trivially — so M5's **first-class explainability** has a place to live. M5's hard requirement is
that the "why" be **traceable to relationships** ("skipped barbell squat: knee injury → loads knee"),
explicitly **not** a vague LLM rationalization (PRD §10 M5; research §GraphRAG — every inclusion/
exclusion must trace to graph relationships, not LLM rationale). The risk is symmetric: over-build and
it's gold-plating (§8.8); under-build and M5's headline feature forces a contract change.

Serves: PRD §7.7c (explanation seam); §10 M5 (explainability); §8.8 (no over-engineering).

## Options considered

- **Defer entirely, add in M5.** Changes the response envelope, frontend rendering, and API contract
  later — the rework §7.7c exists to prevent. Rejected.
- **Free-text rationale string.** Trivial in M1, but it *is* the "vague LLM rationalization" M5 must
  avoid — M5 would replace it, and it models the wrong thing. Rejected.
- **Structured, relation-shaped reason list (chosen).** A small list of edge-shaped reasons the M1
  generator/filter already produce as decisions.

## Decision

Every agent response carries `explanation: list[Reason]`, where
`Reason = { claim: Literal["included","excluded","added","matched","substituted","note"], subject:
str, relation: str, object: str | None, detail: str | None }`. M1 populates it from decisions the
Generator and injury filter **already make**: e.g. `{claim:"excluded", subject:"Barbell Back Squat",
relation:"loads_joint", object:"knee"}`, `{claim:"added", subject:"Left-side X", relation:
"bilateral_pair_of", object:"Right-side X"}`, `{claim:"included", subject:"DB Bench", relation:
"matches_target", object:"chest"}`. M5 populates the **same shape** from graph edges. The Coach/Logger
populate it lightly (e.g. `matched`/`note`). The M1 UI surfaces it as a subtle "why these?" affordance
on generated workouts.

## Rationale

A relation-shaped list is the form M5's graph traversal naturally emits, so M1→M5 is *enrichment of
the same field*, not a reshape — the API envelope and frontend rendering never change. Crucially, M1
gets this **for free**: the generator already decides what to include/exclude/pair; we capture those
decisions as structured reasons instead of discarding them. Surfacing it lightly in M1 proves the seam
works end-to-end and previews M5's differentiator to the grader — turning a forward-compat seam into a
visible M1 feature at minimal cost. Modeling reasons as `subject—relation—object` triples (not prose)
is what keeps M5 honest: explanations point at relationships, never at LLM hand-waving.

## Tradeoffs & risks

- **Risk of over-populating in M1** (gold-plating). Mitigation: M1 only emits reasons for decisions it
  *actually* makes (target match, contraindication exclusion, bilateral pairing); it does not
  manufacture reasons. Coach/Logger reasons are minimal.
- **The `relation` vocabulary could sprawl.** Mitigation: M1 ships a small closed set
  (`loads_joint`, `matches_target`, `bilateral_pair_of`, `equipment_match`, `name_match`); M5 extends
  it deliberately as graph edge types are introduced. Documented as a controlled vocabulary.

## Consequences for the build

- **Contract (Reason / explanation payload).** Shared response shape M5 enriches.
  - **Source of truth:** `backend/app/graph/explanation.py` (`Reason` model + the closed `relation`
    vocabulary). Carried on `HubState.explanation` (ADR-004) and the API/SSE response (ADR-001/002).
  - **Shape (initial):** `Reason` as above; initial `relation` vocab = `loads_joint | matches_target
    | bilateral_pair_of | equipment_match | name_match`.
  - **Exhaustive consumers:** the Generator (emits include/exclude/add reasons), the injury filter
    (emits exclusion reasons), the Logger (emits match/substitution reasons), the response assembler,
    the API serializer, and the frontend "why these?" renderer. M5 adds graph-edge-derived reasons to
    the same list and the same renderer.
- **Policy:** explanations are structured `subject—relation—object` reasons, never free-text LLM
  rationalization. M1 emits only reasons for decisions actually taken.
