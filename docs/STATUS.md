# Status — Cadence (Milestone 1)

**Updated:** 2026-06-02 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

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
| 02 | P1 (injury avoidance + bilateral pairing) | Not started | Extends F-04. Independent of iteration 03 — can build concurrently once 01 is merged. |
| 03 | P2 (multi-turn memory + observability) | Not started | Extends iteration-01 features. Independent of iteration 02. |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | Not started | Cut first under time pressure. F-11 needs F-07 (iteration 02). |

## What's next

1. Plan + build iterations 02 (P1: injury avoidance + bilateral pairing) and 03 (P2: multi-turn
   memory + observability) — independent of each other, can build concurrently now that 01 is landed.
2. Post-build human pass on the brand accent (eyedropper-confirm the `#00C2A8`-family teal against
   live future.co — see BRAND.md UNCONFIRMED note; not a build gate).
3. Optional: run the 4 live LLM smoke tests with `OPENROUTER_API_KEY` set to confirm the real-model
   routing/coach paths (they skip offline by design — ADR-018).
