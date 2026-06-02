# Feature: Workout Generator sub-agent + output gate

**ID:** F-04 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** No workout generation exists.
**After:** A generation-routed message produces a structured warmup/main/cooldown workout where every
exercise is a real dataset entry with sets, reps (or duration), and rest — and no response can ever
reference an exercise outside the dataset (output-validation gate).

## How it fits the roadmap
Iteration 01; builds concurrently with F-03/F-05 once F-01's contracts are frozen. The
output-validation gate it introduces is the structural enforcement of the no-hallucination invariant —
the safety half of ADR-018's non-negotiable critical-path pair. Hard-depends only on F-01.

## Requirements traced (from the PRD)
Reqs 8–10, 18; acceptance criteria 7–8, 14 (no exercise outside dataset), 16 (workout renders
structured).

## Dependencies (must exist before this starts)
- **F-01 (walking skeleton)** — HARD dep: uses the frozen `GeneratorState`, boundary adapter,
  `get_model('generator')`, and the `ExerciseRepository` (`search`, `get_by_id`).

## Unblocks (what waits on this)
- F-06 (resilience/tests), F-07 (injury+bilateral extend the generator), F-08 (memory "adjust it"
  references a prior workout), F-11 (explanation panel renders generator reasons), F-12 (voice polish).

## Contracts touched
- **ExerciseRepository** (ADR-008) — consumes `search` and `get_by_id`; all exercise access via the
  interface (no direct JSON reads).
- **Reason/explanation payload** (ADR-012) — **introduces** the generator's relation-shaped reasons
  (`included`/`matches_target`, `equipment_match`) and the closed `relation` vocabulary's
  first members.
- **SSE envelope** (ADR-002) — emits the `structured` workout payload (read from state).
- **Pydantic tool schemas** (PRD §7.1) — `search_exercises` and `build_workout` tools with
  field-described Pydantic input schemas.

## Acceptance criteria (product behavior)
1. An upper-body dumbbell request yields exactly three named blocks (warmup, main, cooldown); every
   exercise has sets, a reps-or-duration value, a rest value, and an ID matching a real
   `data/exercises.json` entry.
2. A request specifying dataset-present equipment returns only exercises satisfiable by that equipment.
3. The output-validation gate rejects any workout referencing an unknown exercise ID before it leaves
   the graph (a bogus ID triggers recovery, not a user-facing bad exercise).
4. The workout renders in the UI as a readable structured card, not raw JSON.
5. The two tools have Pydantic input schemas with field descriptions.

## Testing requirements
- **Integration (deterministic, no LLM):** feed selected exercise IDs through `build_workout` and
  assert three blocks + complete prescriptions + all IDs real. Feed a bogus ID through the output gate
  and assert it's caught.
- **Unit:** `search` returns only equipment-satisfiable, dataset-real exercises.
- This is a designated critical path (ADR-018 #3 output-gate); test rationale recorded in the test
  file.

## Manual setup required
None beyond F-01.

## Implementation notes (filled in by the building agent)
