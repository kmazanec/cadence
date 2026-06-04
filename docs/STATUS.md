# Status — Cadence (Milestone 1)

**Updated:** 2026-06-04 · **Roadmap:** [ROADMAP.md](./ROADMAP.md)

## Now

Iteration 04 (stretch) **assembled and shipped to an MR**: all three features (F-10 eval harness,
F-11 "why these?" panel, F-12 coach voice) cherry-picked onto `integration/04-stretch` with linear
history (zero merge commits) and pushed for review. Full integrated suite green: backend
286 passed / 5 skipped, frontend 51 passed, typecheck clean. The predicted F-11/F-12 convergence in
`chat.py` and `ChatApp.tsx` auto-merged (disjoint regions). With iteration 04 this completes the
roadmap's committed work (M1 + the three stretch items).

Iterations 02 (P1) and 03 (P2) both **shipped** and landed on `main` via fast-forward
(linear, no merge commits): iteration 02 (F-07) merged first, then iteration 03 (F-08 + F-09)
rebased onto it and merged. Both built concurrently in isolated worktrees off the same base.

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
| 02 | P1 (injury avoidance + bilateral pairing) | **Shipped — merged** | F-07 shipped: all 4 AC met, 233 passed / 4 skipped. Landed on `main` via FF (PR #3). |
| 03 | P2 (multi-turn memory + observability) | **Shipped — merged** | F-08 (multi-turn memory) and F-09 (structured observability) both shipped. 7 session-memory tests + 18 observability tests passed. Rebased onto 02, landed on `main` via FF (PR #2). |
| 04 | Stretch (eval harness + "why these?" panel + coach voice) | **Shipped — MR open** | F-10, F-11, F-12 all shipped on `integration/04-stretch`; full suite green (backend 286/5, frontend 51, typecheck clean). Awaiting human merge of the MR. |

## What's next

1. **Merge the iteration 04 MR** (`integration/04-stretch`) into `main` via fast-forward (linear,
   no merge commit), then tear down the stretch worktrees/branches.
2. **Human voice review** of F-12 against BRAND.md (AC 1/3 are subjective: overall warmth/cohesion
   and card-agent prose); reconcile the frontend client-side recovery fallback wording with the
   backend `RECOVERY_ERROR_MESSAGE` if a single canonical phrasing is wanted.
3. All roadmap-committed work is now built. Post-merge: eyedropper-confirm the `#00C2A8`-family teal
   against live future.co — see BRAND.md UNCONFIRMED note; not a build gate.
4. Optional: run the eval harness and the 4 live LLM smoke tests with model API keys set to confirm
   real-model routing/coach paths (they skip offline by design — ADR-018).
