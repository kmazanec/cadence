# ADR-009: Injury avoidance as a relation + hard-exclusion pre-filter (graduates to M2 graph traversal)

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

P1 injury avoidance: the Generator excludes exercises whose loaded joints include an injured joint
(PRD reqs 11, criterion 9). PRD §7.7b insists this be modeled as a **relationship** — "injury →
affected joint(s) → exercises that load that joint" — not an inline predicate, because that relation
**is** the M2 graph traversal in miniature. Research is emphatic on the *shape*: for safety-critical
contraindication, exclusion must be a **hard pre-filter** (compute the contraindicated set, then
`WHERE NOT IN`), never a soft re-ranking that could still surface a contraindicated exercise at rank 1
(TECHNOLOGY.md §safety-critical hard exclusion). The same set-then-exclude shape works whether the set
comes from a Python scan (M1) or a Cypher traversal (M2).

Serves: PRD reqs 11, criterion 9; §7.7b (relation-shaped injury); §10 M2/M5 (graph contraindication).

## Options considered

- **Inline filter in `build_workout`.** A list comprehension over `joints_loaded` inside the tool.
  Works for M1, but it's the inline predicate §7.7b explicitly forbids; M2 rips it out. Rejected.
- **Soft re-ranking (down-weight contraindicated).** Matches a naive "hybrid score" instinct but
  research shows it can still surface a contraindicated exercise — unacceptable for a safety
  invariant. Rejected.
- **Explicit joint→exercise relation + hard-exclusion set (chosen).**

## Decision

Injury avoidance is computed as a **set-then-exclude**: `ExerciseRepository.contraindicated_ids(injuries)`
returns the set of exercise IDs whose `joints_loaded` intersects the injured joints (via an explicit
joint→exercise-IDs relation built at load time). The Generator computes this set **first**, then
applies it as a **hard exclusion** (`WHERE id NOT IN contraindicated`) before/around search and build —
no contraindicated exercise can appear in any result regardless of other ranking. In M2,
`contraindicated_ids` is re-implemented as a bounded, typed Cypher traversal returning the same set,
to the same method signature.

## Rationale

This satisfies the P1 requirement, mirrors the research's safety-critical pattern exactly (hard
pre-filter, not soft rank), and makes the M1→M2 graduation a body-swap behind one method. Modeling it
as a relation + exclusion set — rather than an inline comprehension — is what §7.7b asks for, and it's
*essentially free*: the M1 body is a dozen lines, but its shape and signature are M2-ready. It also
centralizes the safety invariant at one enforceable point, complementing the output-validation gate
(ADR-010).

## Tradeoffs & risks

- **Joint-name normalization** between user language ("knee") and dataset joints. Mitigation: a small
  explicit synonym/normalization map in M1 (the seed of M2's ontology/SNOMED question, §10 M2); the
  injured-joint constraint is matched against normalized joint names.
- **Over-exclusion can leave few/no valid exercises** (the thin-result risk, §8.4). Mitigation: the
  resilience path (ADR-006) recovers gracefully — recommend alternatives or explain the gap, never
  pad with contraindicated or irrelevant exercises.

## Consequences for the build

- **Policy:** contraindication is a **hard pre-filter** computed as an exclusion set, never a soft
  re-rank. A contraindicated exercise must never appear in output (enforced again by ADR-010).
- **Policy:** the joint→exercise relation and joint-name normalization live behind the repository
  (ADR-008), not inline in the generator tool.
- Sets up M2's `Member → has-injury → Joint → joints-loaded-by → Exercise` traversal as the same
  method with a graph body.
