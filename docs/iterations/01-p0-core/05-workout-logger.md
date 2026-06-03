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

### Chunk 1 — Fuzzy-match resolver
`backend/app/agents/logger/resolver.py`. RapidFuzz `WRatio(cutoff=80)` scans the full
exercise catalogue via `ExerciseRepository.all()`. When `llm_verify=True` (default), the top
`_SHORTLIST_SIZE=5` candidates are passed to `get_model('logger').with_structured_output` for a
structured pick (ADR-018: test seam is `fake_get_model`). `llm_verify=False` bypasses the LLM
step for deterministic tests. Returns `(exercise_id, exercise_name)` on a match, `None` when
no candidate clears cutoff — no invented substitution. Case-insensitive matching via `.casefold()`.

**ADR-018 critical-path note:** the fuzzy-match path is tested without a live LLM;
`llm_verify=False` is the test mode. The test proves "bench press" → real exercise id, and
"zercher good-mornings" → `None`.

### Chunk 2 — Logger subgraph
`backend/app/agents/logger/graph.py`. Single function `run_logger(...)` (no LangGraph StateGraph
wrapper needed here — the hub owns the graph). LLM structured-output call via
`_extract_entries(user_message, model) -> list[ParsedEntry]` is the monkeypatch seam for tests.
`ParsedEntries.entries` default `[]` guards against extraction failures. Results persist via
`log_repo.append(entries, session_id)` before returning `WorkoutLogResult`. Entries without a
fuzzy match get `unmatched=True`, `exercise_id=None`.

### Chunk 3 — Hub wiring
`backend/app/graph/hub.py`. Added `_logger_boundary_node` and updated `_route_edge` to dispatch
`WORKOUT_LOG` → `"logger_boundary"` instead of falling through to `response_assembly`. The
`_get_log_repository_for_hub()` helper is isolated so tests can monkeypatch without touching the
production factory. Explanation reasons emitted: `claim='matched'` / `relation='name_match'` for
resolved entries; `claim='note'` / `relation='name_match'` for unmatched entries.

### Chunk 4 — Frontend log card
`frontend/src/render/LogCard.ts`. `renderLogEntry` produces `{displayName, detail, unmatched}`;
`renderLogCard` aggregates to `{entries, matchedCount, unmatchedCount, summary}`. The
`displayName` is always the `raw_name` (user's text) — the UI caller should display the resolved
catalogue name separately if needed. Unmatched entries surface the original text with the
`unmatched` flag; never an invented name.

### QA note
The `_extract_entries` function (Chunk 2) requires a real LLM call to exercise end-to-end.
The tests stub this step. The hub integration test (`test_workout_log_route_dispatches_to_logger`)
patches both `_router_node` and `_extract_entries` for a deterministic full-graph run.
