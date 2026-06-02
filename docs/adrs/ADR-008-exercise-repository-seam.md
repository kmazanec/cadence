# ADR-008: ExerciseRepository interface — JSON-backed in M1, graph-backed in M2 (same signatures)

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

PRD §7.7a wants exercise/data access behind a **seam** so the JSON-backed M1 source can later be
swapped for a graph-backed M2 source — *without* leaking graph concepts into M1 or gold-plating
(§8.8). The dataset is the sole source of exercises; agents must never reference an exercise outside
it (reqs 8–14, 18). M2 re-implements this seam against Neo4j (§10 M2).

Serves: PRD reqs 8–14, 18; §7.7a (data seam); §8.8 (no over-engineering); §10 M2.

## Options considered

- **Direct JSON access, no interface.** Simplest now; M2 rewrites every call site. Violates §7.7a.
  Rejected.
- **Generic repository + query-spec abstraction.** Composable arbitrary filters; this is the
  gold-plating §8.8 warns against — abstraction M1 doesn't need. Rejected.
- **Single `ExerciseRepository` Protocol with the methods agents actually need, JSON impl (chosen).**

## Decision

One `ExerciseRepository` Protocol/ABC exposing exactly the operations the agents need:
`search(muscle_groups?, equipment?, movement_patterns?) -> list[Exercise]`,
`get_by_id(id) -> Exercise | None`,
`contraindicated_ids(injuries) -> set[str]` (ADR-009),
`bilateral_pair(id) -> Exercise | None`,
and `all() -> list[Exercise]`. M1 ships `JsonExerciseRepository` loading `data/exercises.json` into
typed `Exercise` Pydantic models at startup. M2 will add a `GraphExerciseRepository` with **identical
signatures**, changing only the bodies (JSON scan → Cypher).

## Rationale

This is the exact §7.7a seam at the cheapest defensible thickness: a handful of intent-named methods,
not a generic query DSL. It keeps **all** dataset access in one place (so the no-hallucinated-exercise
invariant, req 18, is enforceable at one boundary), makes the agents trivially testable against a fake
repo, and makes M2 a body-swap rather than a call-site rewrite. No graph concept appears in M1 — the
signatures are framed in domain terms (muscle groups, equipment, injuries), which are stack-neutral.

## Tradeoffs & risks

- **An interface for a single impl can look like premature abstraction.** Defense: it's justified by
  (a) the single-boundary enforcement of req 18, (b) testability via a fake, and (c) the *named,
  funded* M2 graduation — not speculative. The method set is minimal and intent-revealing; if a method
  isn't used by an agent, it isn't added.
- **`priority_tier` is dead in this dataset** (all `2`) — the repo must not expose ranking by it
  (PRD §7.2). Mitigation: no `priority_tier` parameter on `search`; documented.

## Consequences for the build

- **Contract (ExerciseRepository).** Shared interface; M2 implements it against the graph.
  - **Source of truth:** `backend/app/data/repository.py` (`ExerciseRepository` Protocol + `Exercise`
    Pydantic model) + `backend/app/data/json_repository.py` (M1 impl).
  - **Shape (initial):** the five methods above; `Exercise` mirrors the dataset fields
    (`id, name, muscle_groups, joints_loaded, movement_patterns, equipment_required, is_bilateral,
    bilateral_pair_id, is_reps, is_duration, supports_weight, ...`).
  - **Exhaustive consumers:** the Generator's tools (`search_exercises`, `build_workout`), the
    Logger's fuzzy matcher, and the output-validation gate (ADR-010). All dataset access goes through
    this interface — no agent reads the JSON directly.
- **Policy:** all exercise data access is via `ExerciseRepository`; no direct `exercises.json` reads
  in agent/tool code. `priority_tier` is never used for selection or ranking.
