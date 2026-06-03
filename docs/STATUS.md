# Status — Cadence (Milestone 1)

**Updated:** 2026-06-02 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iterations 02 (P1) and 03 (P2) are **planned and approved** (build plans frozen via
`kmaz-plan-iteration`, 2026-06-02) and **building concurrently** via `kmaz-build-iteration`, each
isolated in its own `.claude/worktrees/<slug>/`.

Iteration 01 (P0 core) **SHIPPED** — all six features (F-01..F-06) landed on `main` via a
fast-forward (linear, no merge commit) through PR #1. F-06's value (resilience hardening, the
critical-path test suite, the eval README, and the demo transcript) was salvaged onto the same
integration branch — its parallel hub re-wiring dropped in favor of the already-integrated
versions, and a real SSE-error-boundary bug (`chat.py` re-raised after yielding the error frame,
so Starlette dropped it) was fixed in the process. Full suite green: backend 159 passed /
4 live-skipped (offline), frontend 15 passed.

## Iterations

| # | Iteration | Status | Notes |
|---|-----------|--------|-------|
| 01 | P0 core (skeleton + router + 3 agents + resilience/tests) | **Shipped** | All six features (F-01..F-06) merged to `main` via FF through PR #1. Backend 159 passed / 4 live-skipped, frontend 15 passed. |
| 02 | P1 (injury avoidance + bilateral pairing) | **Approved — building** | Build plan in [BUILD-PLAN-02-p1-injury-bilateral.md](./iterations/02-p1-injury-bilateral/BUILD-PLAN-02-p1-injury-bilateral.md). F-07 is wiring + reasons + tests (repo seam already shipped). Dangling `bilateral_pair_id` resolved → **synthetic-fixture** approach (dataset untouched). |
| 03 | P2 (multi-turn memory + observability) | **Approved — building** | Build plan in [BUILD-PLAN-03-p2-memory-observability.md](./iterations/03-p2-memory-observability/BUILD-PLAN-03-p2-memory-observability.md). F-08: empirically NO accumulator doubling on pinned langgraph — real work is 3 behaviour fixes incl. a verified live coach double-append bug. F-09: greenfield stdlib structured logging around the `get_model` seam. |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | Not started | Cut first under time pressure. F-11 needs F-07 (iteration 02). |

## What's next

1. **Approve the iteration 02 + 03 build plans** (both `kmaz-plan-iteration` outputs are written and
   pending approval). One pre-build decision gates iteration 02: the dangling `bilateral_pair_id`
   dataset issue (synthetic fixture vs. dataset patch). Once approved, both iterations can build
   concurrently via `kmaz-build-iteration` (each in its own `.claude/worktrees/<slug>/`).
2. Post-build human pass on the brand accent (eyedropper-confirm the `#00C2A8`-family teal against
   live future.co — see BRAND.md UNCONFIRMED note; not a build gate).
3. Optional: run the 4 live LLM smoke tests with `OPENROUTER_API_KEY` set to confirm the real-model
   routing/coach paths (they skip offline by design — ADR-018).
