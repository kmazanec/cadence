# Status — Cadence (Milestone 1)

**Updated:** 2026-06-02 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Nothing built yet — planning complete (PRD v2, ARCHITECTURE + 19 ADRs, ROADMAP). Next up is
iteration 01 (P0 core).

## Iterations

| # | Iteration | Status | Notes |
|---|-----------|--------|-------|
| 01 | P0 core (skeleton + router + 3 agents + resilience/tests) | Not started | Must-ship. F-01 freezes contracts; F-02/03/04/05 then build concurrently; F-06 waits on router+gen+logger. |
| 02 | P1 (injury avoidance + bilateral pairing) | Not started | Extends F-04. Independent of iteration 03 — can build concurrently once 01 is merged. |
| 03 | P2 (multi-turn memory + observability) | Not started | Extends iteration-01 features. Independent of iteration 02. |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | Not started | Cut first under time pressure. F-11 needs F-07 (iteration 02). |

## What's next

Run `kmaz-plan-iteration` on `docs/iterations/01-p0-core/` to produce the reviewable BUILD-PLAN for
iteration 01, then `kmaz-build-iteration` once approved.
