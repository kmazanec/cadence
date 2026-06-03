# Status — Cadence (Milestone 1)

**Updated:** 2026-06-02 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iteration 01 (P0 core) **built and assembled** — F-01..F-05 shipped on `integration/01-p0-core`
behind one open MR (full suite green: 139 passed / 4 live-skipped, offline). F-06
(resilience + critical-path tests + demo/README) was **left out of this MR** (its branch/worktree
preserved) and is the immediate next build once the MR lands.

## Iterations

| # | Iteration | Status | Notes |
|---|-----------|--------|-------|
| 01 | P0 core (skeleton + router + 3 agents + resilience/tests) | In review | F-01..F-05 shipped on `integration/01-p0-core` (MR open). F-06 not yet shipped — build it next, after the MR merges (it depends on F-02/F-04/F-05, all now landed). |
| 02 | P1 (injury avoidance + bilateral pairing) | Not started | Extends F-04. Independent of iteration 03 — can build concurrently once 01 is merged. |
| 03 | P2 (multi-turn memory + observability) | Not started | Extends iteration-01 features. Independent of iteration 02. |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | Not started | Cut first under time pressure. F-11 needs F-07 (iteration 02). |

## What's next

1. Review + merge the `integration/01-p0-core` MR (manual-review hotspots: the cherry-pick convergence
   in `backend/app/graph/hub.py`, and the schema-aware fake-model seam in `backend/tests/conftest.py`).
2. Build **F-06** (resilience hardening + critical-path tests + demo/README) — its deps (F-02/F-04/F-05)
   are now all on the integration branch.
3. After 01 fully lands, iterations 02 (P1) and 03 (P2) can be planned/built concurrently.
