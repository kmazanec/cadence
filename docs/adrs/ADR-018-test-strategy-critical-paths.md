# ADR-018: Test strategy — four designated critical paths, prioritized, with fake-model seams

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The brief requires **at least 2 critical-path tests, each with a written rationale for why it was
chosen** (PRD req/criteria 18) — and the *choice + rationale* is itself graded. The system also has
LLM nondeterminism that tests must tame. The user designated four critical paths; this ADR records
them, their priority (cut-line), and how they're made deterministic.

Serves: PRD req/criteria 18, and the criteria each path asserts (1–6, 9, 11–12, 14–15).

## Options considered

- **Write only the minimum two.** Meets the letter; the user chose to over-deliver to four. Recorded
  with a priority order so the cut-line is explicit if time runs short.
- **End-to-end-only vs. unit-level.** Pure end-to-end tests are flaky under LLM nondeterminism;
  pure-unit misses the graph wiring. Chosen: a mix — deterministic unit/integration tests on the
  safety/data invariants (no live LLM), plus graph-level tests that can stub the model.

## Decision

Four designated critical paths, **in priority order** (the cut-line is bottom-up; the top two are the
"if you only write two" pair):

1. **Routing correctness + low-confidence clarify** (criteria 1–6). *Rationale:* routing is the hub's
   entire thesis and the ambiguity-handling is the explicit graded differentiator — the system's
   spine. Tested with a **fake/stubbed router model** returning controlled `RoutingDecision`s
   (including below-threshold) so the *graph's* dispatch/clarify logic is asserted deterministically,
   independent of LLM variance; plus a small live-or-recorded check on the three canonical messages.
2. **Injury-aware hard exclusion** (criterion 9). *Rationale:* safety is the load-bearing invariant
   and the seed of M5's headline guarantee — the highest-stakes correctness path. Tested **without an
   LLM**: given a knee injury, assert `contraindicated_ids` + the generator's hard-exclusion produce a
   workout with zero knee-loading exercises. Deterministic by construction.
3. **No-hallucination output gate + empty-result recovery** (criteria 12, 14, 15). *Rationale:*
   "never invent exercises" is the system's trust invariant and resilience is explicitly graded.
   Tested by feeding the output gate a bogus exercise ID (caught) and an empty/thin search (graceful
   recovery, no fabricated exercise). Deterministic.
4. **Logger fuzzy-match resolve-or-flag** (criteria 11–12). *Rationale:* structured extraction +
   no-invention is the logger's whole contract. Tested via RapidFuzz on known inputs ("bench press" →
   real ID; an unmatchable name → flagged unmatched), no live LLM needed.

## Rationale

The priority order makes the brief's "at least 2" concrete: paths 1–2 are the spine and the
safety-critical guarantee, so they ship first; 3–4 deepen coverage of the trust invariant and the
logger contract. Designing the tests around **fake-model seams** (the `get_model(role)` factory,
ADR-007, makes injecting a stub trivial) is what makes graph-level behavior assertable despite LLM
nondeterminism — the safety/data tests need no LLM at all because the invariants are enforced in
deterministic Python (hard exclusion, output gate, fuzzy match). This is the honest way to test an
LLM system: assert the deterministic guarantees hard, and the LLM-dependent routing with controlled
stubs + a thin live check.

## Tradeoffs & risks

- **Live LLM checks can be flaky/cost tokens.** Mitigation: keep them minimal (the three canonical
  routing messages); the bulk of assertions use stubs/no-LLM. A recorded-response mode is an option.
- **Four tests is more than required and costs time.** Mitigation: the explicit priority order is the
  cut-line — paths 1–2 are non-negotiable, 3–4 are cut first if the budget tightens.

## Consequences for the build

- **Policy:** the `get_model(role)` factory must support injecting a fake/stub model for tests (no
  network). Safety/data invariants (hard exclusion, output gate, fuzzy match) are tested without an
  LLM.
- **Policy:** each test file states its rationale (the brief grades the *why*), mirroring this ADR.
- **Build order:** paths 1–2 are P0-critical and ship first; 3–4 follow; cut bottom-up.
