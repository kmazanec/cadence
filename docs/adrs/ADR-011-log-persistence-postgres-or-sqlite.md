# ADR-011: LogRepository — Postgres when DATABASE_URL set, else SQLite fallback

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** yes (durable persistence promoted) · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The Logger must persist resolved entries to a "local store for the session" and return them (PRD req
15, criterion 13). The PRD deferred *durable, multi-session* persistence (§4 Deferred #1). During
architecture the user elected **Postgres** for production credibility and M3/M6 graduation, then
refined to a **dual path** so the clean-clone run story stays one-command. This promotes durable
persistence into M1 scope — reflected back into the PRD as a new version.

Serves: PRD req 15, criterion 13; §4 Deferred #1 (now promoted); §10 M3 (history edges) / M6
(Dockerized stack).

## Options considered

- **In-memory only.** Simplest; weakest match to "persist to a local store" (implies durability).
  Rejected.
- **Append-only JSONL.** Zero deps, trivially inspectable; less queryable, not a "real DB" signal.
  Viable but minimal.
- **SQLite only.** File-based real SQL, durable, zero service. Strong default but no Postgres signal.
- **Postgres only.** Most production-credible; but forces a service into the clean-clone demo/tests —
  friction against criterion 19 at M1 scale where it's not load-justified.
- **Postgres when `DATABASE_URL` set, else SQLite (chosen).** Best of both.

## Decision

A `LogRepository` interface (mirroring the ExerciseRepository seam, ADR-008) with two impls behind one
factory: if `DATABASE_URL` is set, use the **Postgres** impl; otherwise fall back to **SQLite** at a
default file path. Both expose the same methods (`append(entries, session_id)`,
`for_session(session_id)`). The schema is identical across both (SQLAlchemy or equivalent), so the
choice is config + connection, not a redesign. `docker compose` includes a Postgres service the
Postgres path can use; the default `make dev`/test path uses SQLite and needs no service.

## Rationale

The dual path keeps `git clone → run → demo` trivial (SQLite, in-process, no provisioning) — directly
protecting criterion 19 and the critical-path tests — while **demonstrating** the production Postgres
path a CTO wants to see and that M3's history-edge ingestion + M6's Dockerized stack will build on.
Postgres isn't load-justified at M1 scale (a handful of rows/session); its value here is forward
graduation and signal, which the dual path captures without taxing the default run. One interface, one
schema, two connections — the seam is the same pattern as the exercise repo, so it reads as consistent
architecture rather than two ad-hoc stores.

## Tradeoffs & risks

- **Two impls to keep in sync.** Mitigation: shared schema + a shared SQL layer (SQLAlchemy) means the
  impls differ only in connection/dialect; tests run against SQLite, with a documented optional
  Postgres test.
- **SQL dialect drift (e.g. JSON columns, upserts).** Mitigation: stick to portable column types for
  M1's simple log schema; avoid Postgres-only features until M3 genuinely needs them.
- **A CTO may ask "why Postgres at all for M1?"** Honest answer recorded: it's a forward-investment for
  M3/M6, not an M1 need; the SQLite fallback is the actual M1 default.

## Consequences for the build

- **Contract (LogRepository + log entry schema).** Shared shape M3 ingests into history edges.
  - **Source of truth:** `backend/app/data/log_repository.py` (interface + `LogEntry` Pydantic model)
    + `sqlite_log_repository.py` / `postgres_log_repository.py` + a factory keyed on `DATABASE_URL`.
  - **Shape (initial):** `LogEntry = { session_id, exercise_id | None, raw_name, sets?, reps?,
    weight?, unmatched: bool, logged_at }`; methods `append`, `for_session`.
  - **Exhaustive consumers:** the Logger subgraph (writer), any "show my log" read path, and M3's
    future history-edge ingester.
- **Policy:** persistence goes through `LogRepository`; impl is selected by config (`DATABASE_URL`),
  never hardcoded. Default (no env) is SQLite so the clean-clone path needs no service.
