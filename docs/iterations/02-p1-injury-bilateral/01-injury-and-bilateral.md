# Feature: Injury avoidance + bilateral pairing (P1)

**ID:** F-07 · **Iteration:** 02-p1-injury-bilateral · **Status:** Not started

## What this delivers (before → after)
**Before:** The generator ignores injuries and trains only one side of unilateral exercises.
**After:** The generator excludes any exercise loading an injured joint (hard pre-filter) and, when it
selects a single-side exercise with a dataset pair, auto-includes the opposite side.

## How it fits the roadmap
The whole of iteration 02 (P1 differentiators). Both are small `build_workout` extensions sharing the
generator code path, cut together. Iteration 02 is independent of iteration 03 (can build
concurrently once iteration 01 is merged).

## Requirements traced (from the PRD)
Reqs 11–12; acceptance criteria 9–10.

## Dependencies (must exist before this starts)
- **F-04 (workout generator)** — HARD dep: extends the generator's selection/build path with the
  contraindication exclusion set and the bilateral-pair inclusion.
- (Builds on F-01's `ExerciseRepository`, extended with `contraindicated_ids` + `bilateral_pair`.)

## Unblocks (what waits on this)
- F-11 ("why these?" panel) — renders the exclusion/pairing reasons this feature emits.

## Contracts touched
- **ExerciseRepository** (ADR-008) — extends with `contraindicated_ids(injuries)` (the injury→joint→
  exercise relation + hard-exclusion set) and `bilateral_pair(id)`.
- **Reason/explanation payload** (ADR-012) — extends with `excluded`/`loads_joint` and
  `added`/`bilateral_pair_of` reasons.
- **Injury-as-relationship policy** (ADR-009) — hard pre-filter (exclude, never soft re-rank).

## Acceptance criteria (product behavior)
1. A request to avoid loading the knee yields a workout with **zero** exercises listing "knee" in
   their loaded joints (hard exclusion, regardless of other ranking).
2. When the generator selects a unilateral exercise that has a `bilateral_pair_id` in the dataset, the
   paired opposite-side exercise also appears in the result.
3. Over-exclusion leaving few/no valid exercises recovers gracefully (alternatives or honest gap), per
   the resilience policy — never padding with contraindicated or irrelevant exercises.
4. The exclusion and pairing decisions are emitted as structured explanation reasons.

## Testing requirements
- **Integration (deterministic, no LLM):** given a knee injury, assert the built workout contains no
  knee-loading exercise (designated critical path ADR-018 #2 — safety; rationale recorded).
- **Unit:** `contraindicated_ids({knee})` returns exactly the knee-loading IDs; `bilateral_pair`
  returns the partner; a unilateral selection pulls in its pair.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)
