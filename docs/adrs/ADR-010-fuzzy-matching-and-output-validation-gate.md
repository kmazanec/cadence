# ADR-010: Logger fuzzy-matching (RapidFuzz WRatio) + a dataset-bounded output-validation gate

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The Logger must resolve a spoken exercise name ("bench press") to a real dataset exercise ("Barbell
Flat Bench Press") via fuzzy matching, and **explicitly flag as unmatched** anything it can't confidently
resolve — never substituting an invented exercise (PRD reqs 13–14, criteria 11–12). Separately, the
system-wide invariant is that **no user-facing response references an exercise not in the dataset**
(req 18, criterion 14). Research: a hybrid RapidFuzz-narrows-then-LLM-verifies approach improves
accuracy up to 50pp while cutting cost; `WRatio` is the recommended scorer with `score_cutoff` ≈ 80
for exercise names (TECHNOLOGY.md §entity matching).

Serves: PRD reqs 13–14, 18; criteria 11–12, 14.

## Options considered

- **LLM-only name resolution.** Higher cost/latency and weaker precision than the hybrid; can
  hallucinate a plausible-but-wrong match. Rejected as primary.
- **Pure RapidFuzz, no LLM verify.** Cheap and deterministic; fine as a baseline but can mis-bind
  short ambiguous inputs. Used as the narrowing stage.
- **RapidFuzz `WRatio` (cutoff 80) narrows → optional LLM verify on the shortlist (chosen)**, with a
  hard **output-validation gate** as the final backstop.

## Decision

The Logger resolves each parsed exercise name with RapidFuzz `WRatio`, `score_cutoff=80`, against the
repository's exercise names. A confident single match resolves to that exercise's ID; an ambiguous
shortlist may be disambiguated by a lightweight LLM verify; **no confident match → the entry is
returned explicitly flagged `unmatched`**, never coerced to an arbitrary exercise. Independently, a
**output-validation gate** runs before any response leaves the graph: every exercise ID referenced in
a workout or log payload is checked to exist in the repository; an unknown ID is caught (triggering
the ADR-006 recovery), so a hallucinated exercise can never reach the user.

## Rationale

The hybrid is the research-backed sweet spot for accuracy and cost, and `WRatio`+cutoff-80 is the
documented default for exactly this exercise-name task. Flagging unmatched rather than guessing
satisfies criterion 12 and the no-invention invariant. The separate output-validation gate is the
belt-and-suspenders backstop that makes req 18 a *structural* guarantee rather than a hope — even if
the LLM emits a bogus ID, it's caught at the boundary. Both the matcher and the gate go through the
`ExerciseRepository` (ADR-008), so they share one source of truth for what exists.

## Tradeoffs & risks

- **Cutoff 80 may reject a valid loose match or accept a wrong-but-close one.** Mitigation: cutoff is
  a named constant tunable against criteria 11–12; the unmatched-flag path is the safe default when
  uncertain.
- **LLM verify adds a call.** Mitigation: only on the ambiguous shortlist, not every entry; can be
  disabled for a pure-deterministic mode in tests.

## Consequences for the build

- **Policy:** unmatched exercises are flagged, never coerced to an arbitrary dataset entry.
- **Policy:** an output-validation gate verifies every referenced exercise ID against the repository
  before any response leaves the graph; unknown IDs trigger recovery (ADR-006). This is the structural
  enforcement of req 18.
- **Policy:** matcher and gate use `ExerciseRepository` as the single source of valid exercises.
