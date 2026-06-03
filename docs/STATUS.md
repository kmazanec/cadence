# Status — Cadence (Milestone 1)

**Updated:** 2026-06-02 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iteration 02 (P1) MR is **open** on `integration/02-p1-injury-bilateral` — F-07 shipped, pending
merge to `main`. Iteration 03 (P2) is still building concurrently in its own worktree.

Iteration 01 (P0 core) **SHIPPED** — all six features (F-01..F-06) landed on `main` via a
fast-forward (linear, no merge commit) through PR #1. F-06's value (resilience hardening, the
critical-path test suite, the eval README, and the demo transcript) was salvaged onto the same
integration branch — its parallel hub re-wiring dropped in favor of the already-integrated
versions, and a real SSE-error-boundary bug (`chat.py` re-raised after yielding the error frame,
so Starlette dropped it) was fixed in the process. Full suite green: backend 159 passed /
4 live-skipped (offline), frontend 15 passed.

Note: all 18 `bilateral_pair_id` values in `data/exercises.json` are dangling (no resolvable
partner). Bilateral auto-pairing (AC10) is verified against an in-memory reciprocal fixture; the
dataset is intentionally untouched. A future graph-backed dataset will need real reciprocal pairs
to exercise pairing on live data.

## Iterations

| # | Iteration | Status | Notes |
|---|-----------|--------|-------|
| 01 | P0 core (skeleton + router + 3 agents + resilience/tests) | **Shipped** | All six features (F-01..F-06) merged to `main` via FF through PR #1. Backend 159 passed / 4 live-skipped, frontend 15 passed. |
| 02 | P1 (injury avoidance + bilateral pairing) | **Shipped — MR open** | F-07 shipped: all 4 AC met, 233 passed / 4 skipped. MR on `integration/02-p1-injury-bilateral`. |
| 03 | P2 (multi-turn memory + observability) | **Approved — building** | Build plan in [BUILD-PLAN-03-p2-memory-observability.md](./iterations/03-p2-memory-observability/BUILD-PLAN-03-p2-memory-observability.md). F-08: empirically NO accumulator doubling on pinned langgraph — real work is 3 behaviour fixes incl. a verified live coach double-append bug. F-09: greenfield stdlib structured logging around the `get_model` seam. |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | Not started | Cut first under time pressure. F-11 needs F-07 (iteration 02). |

## What's next

1. **Merge iteration 02 MR** (`integration/02-p1-injury-bilateral`) to `main` via fast-forward.
   Iteration 03 (P2) can continue building concurrently — it does not depend on iteration 02.
2. Post-merge: plan and build iteration 04 (stretch features). F-11 ("why these?" panel) is now
   unblocked by the shipped F-07.
3. Post-build human pass on the brand accent (eyedropper-confirm the `#00C2A8`-family teal against
   live future.co — see BRAND.md UNCONFIRMED note; not a build gate).
4. Optional: run the 4 live LLM smoke tests with `OPENROUTER_API_KEY` set to confirm the real-model
   routing/coach paths (they skip offline by design — ADR-018).
