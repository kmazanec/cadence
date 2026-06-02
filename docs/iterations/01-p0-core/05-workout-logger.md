# Feature: Workout Logger sub-agent + persistence

**ID:** F-05 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** No workout logging exists.
**After:** A log-routed message ("I just did 3x10 bench press at 185 lbs") is parsed into structured
entries, each fuzzy-matched to a real dataset exercise or explicitly flagged unmatched (never
invented), persisted to a local store, and confirmed back in the UI.

## How it fits the roadmap
Iteration 01; builds concurrently with F-03/F-04 once F-01's contracts are frozen. Hard-depends only
on F-01. Introduces the `LogRepository` contract (the one contract not in the skeleton).

## Requirements traced (from the PRD)
Reqs 13–15, 18; acceptance criteria 11–13.

## Dependencies (must exist before this starts)
- **F-01 (walking skeleton)** — HARD dep: uses the frozen `LoggerState`, boundary adapter,
  `get_model('logger')`, and `ExerciseRepository` (for the name pool to fuzzy-match against).

## Unblocks (what waits on this)
- F-06 (resilience/tests), F-08 (memory references logged history), F-12 (voice polish).

## Contracts touched
- **LogRepository + log entry schema** (ADR-011) — **introduces** the interface + `LogEntry` model +
  the Postgres-if-`DATABASE_URL`-else-SQLite factory (default SQLite, no service needed).
- **ExerciseRepository** (ADR-008) — consumes the exercise name pool for RapidFuzz matching.
- **Reason/explanation payload** (ADR-012) — emits `matched`/`substituted` reasons.
- **SSE envelope** (ADR-002) — emits the `structured` log payload.

## Acceptance criteria (product behavior)
1. "I just did 3x10 bench press at 185 lbs" → one entry with sets=3, reps=10, weight=185, resolved to
   a real dataset exercise whose name contains "Bench Press".
2. An unmatchable name (e.g. "3x10 zercher good-mornings") → that entry returned explicitly flagged
   `unmatched`, with no invented/arbitrary substitution.
3. Resolved entries persist to the local store (readable back for the session); default run uses
   SQLite with no external service; if `DATABASE_URL` is set, Postgres is used.
4. The log confirmation renders in the UI as readable structured content, not raw JSON.

## Testing requirements
- **Unit/integration (deterministic):** RapidFuzz `WRatio` cutoff 80 resolves "bench press" → real ID;
  an unmatchable name is flagged unmatched (designated critical path ADR-018 #4 — rationale recorded).
- **Integration:** an appended entry is retrievable via `LogRepository.for_session` (against SQLite).
- The fuzzy-match path is tested without a live LLM; the optional LLM-verify step can be toggled off
  for determinism.

## Manual setup required
- None for the default SQLite path. Postgres path (optional) requires `DATABASE_URL` + a running
  Postgres (documented; `docker compose` provides one).

## Implementation notes (filled in by the building agent)
