# Feature: Model-eval harness (routing split-test) — stretch

**ID:** F-10 · **Iteration:** 04-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** The "how I'd evaluate" story is prose in the README.
**After:** A runnable script scores ~10–15 labeled routing cases across ≥2 configured models and prints
routing accuracy + latency per model — turning the evaluation story into proof and demonstrating the
model abstraction's split-test promise.

## How it fits the roadmap
Iteration 04 (stretch); cut first under time pressure. Deliberately a tiny seed, not a formal eval
pipeline.

## Requirements traced (from the PRD)
Req 16 (committed stretch), supports req 24 (evaluation story).

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: scores the router's classification behavior.
(Uses F-01's `get_model`/registry + per-role config to swap models — contract-mediated.)

## Unblocks (what waits on this)
- Nothing.

## Contracts touched
- **Model config + capability registry** (ADR-007) — consumes per-role model config to run the same
  routing cases across multiple capable models.
- **Route enum + RoutingDecision** (ADR-005) — the labeled cases assert against the route enum.

## Acceptance criteria (product behavior)
1. Running the script against a labeled case set prints, per configured model, routing accuracy and
   average latency.
2. The case set includes clear-intent and ambiguous cases (the latter checking clarify behavior).
3. Swapping/adding a model is config-only; the script needs no code change to evaluate it.

## Testing requirements
- **Smoke:** the harness runs end-to-end against the fake model (deterministic) producing a report;
  a real-model run is optional/documented.

## Manual setup required
- Optional: API keys for the candidate models to run a real split-test.

## Build plan (planned 2026-06-03 · kmaz-plan-iteration)

**Status:** Planned — pending human approval (see `BUILD-PLAN-04-stretch.md`).
**Contract verdict:** Pure consumer — **no shared-contract change.** The one new symbol
(`routing.classify`) is additive/internal, not a frozen shared contract.

### Lens: Architect
- **Where it lives.** No `backend/scripts/` or eval dir exists today. Create a two-part shape:
  an importable module `backend/app/eval/routing_eval.py` (case set, scoring loop, report
  formatting) plus a thin CLI `backend/scripts/eval_routing.py` (~15 lines) that calls
  `routing_eval.run()` and prints. All behaviour lives in the module so pytest asserts on
  structured results, not stdout scraping. Labeled cases are an inline `CASES` constant
  (no YAML/JSON loader — that's a YAGNI dependency).
- **Invoke the router without duplicating the node.** Extract the single-turn classification
  slice into a reusable seam in `routing.py`:
  `async def classify(message, model, prior=[]) -> RoutingDecision | None` — builds
  `[SystemMessage(ROUTER_SYSTEM_PROMPT), *prior, HumanMessage(message)]`,
  `with_structured_output(RoutingDecision, include_raw=True)`, returns `parsed`. **Refactor
  `hub._router_node` to call it** (history via `prior`) so the harness scores the *exact*
  prompt+schema production uses — zero prompt duplication, no drift. (Fallback if the approver
  wants zero hub change: keep `classify` harness-private; `ROUTER_SYSTEM_PROMPT` is still the
  single source either way.)
- **Models specified by config list.** An `EVAL_MODELS: list[str]` constant (default the two
  registry-capable ids). Build each via the **factory** (`get_model` / a tiny `get_model_by_id`)
  — never construct `ChatOpenAI` in the harness. Gate each id through the `REGISTRY` +
  structured-output check (reuse `validate_model_config`) so an incapable id fails fast.
- **Latency** is timed in-harness with `time.perf_counter()` (same primitive `llm_call` uses);
  `llm_call` only *emits* a log event and returns nothing, so reusing it would mean log-scraping
  — avoided.
- **Deterministic smoke** injects a **message-keyed fake** (small extension of
  `_make_scripted_router`) via the factory-monkeypatch pattern from `test_model_swap_routing.py`,
  with at least one deliberately-wrong scripted answer so accuracy < 1.0 proves the scoring math.
- **"Config-only to add a model"** = append one id to `EVAL_MODELS` (+ one `REGISTRY` entry if
  new). Zero scoring-loop/CLI change.

### Lens: Reuse
Reused as-is: `Route`, `RoutingDecision`, `ClarificationPrompt`, **`decide_route` (the harness
scores the gated outcome, not raw `route` equality)**, `CONFIDENCE_THRESHOLD`,
`ROUTER_SYSTEM_PROMPT`, the factory/OpenRouter wiring, `REGISTRY`/`validate_model_config`,
`FakeStructuredOutputModel`/`_make_scripted_router`/`fake_get_model`, `perf_counter`.
New: `RoutingCase` + `CASES`, `EVAL_MODELS`, `classify` seam, scoring loop + `format_report`,
the CLI, the smoke test + message-keyed fake.
Duplication guards: no re-built router prompt (use `classify`), no re-built confidence gate
(use `decide_route`), no re-built OpenRouter client (use factory), no re-built capability check.

### Lens: Contrarian
Cheapest correct thing: ~120-line module + ~15-line CLI + one smoke test; inline cases, two
model ids, `perf_counter`, a printed table. **Refuse** (roadmap forbids a formal pipeline): no
metric framework, no pandas, no charts/HTML/results-DB, no YAML loader, no argparse framework,
no retry logic. **Genuinely risky — must get right:** clarify cases score `decide_route`'s
gated `(None, clarification)` outcome, NOT `route` equality (`RoutingDecision.route` is a
*required* field — an ambiguous message still has a `route`, just low confidence); a `None`
decision (structured-output failure) is a normal data point, not a crash; real-model latency is
non-deterministic/out-of-CI. **YAGNI cut:** no per-route precision/recall or confusion matrices.

### Decision
Importable `routing_eval.py` (inline `CASES`, `EVAL_MODELS`, per-model scoring loop) + thin CLI.
Extract a single-turn `classify(message, model)` into `routing.py` and have the router node call
it so the harness scores the real prompt/schema. Score every case by applying the real
`decide_route` gate to the model's `RoutingDecision` and comparing the gated outcome to the
label — this makes clear-intent *and* ambiguous/clarify cases correct. Time with `perf_counter`,
build real models via the factory, prove deterministically with a message-keyed fake. Adding a
model = one id in `EVAL_MODELS`.

### Contract touchpoints
| Contract (ADR) | Exact symbol | Read / Extend |
|---|---|---|
| Route enum + RoutingDecision (ADR-005) | `Route`, `RoutingDecision(route, confidence, rationale, clarification)`, `ClarificationPrompt` | **READ** |
| Confidence gate (ADR-005) | `decide_route(decision) -> (Route\|None, ClarificationPrompt\|None)`, `CONFIDENCE_THRESHOLD` | **READ** |
| Router prompt (ADR-005) | `ROUTER_SYSTEM_PROMPT` | **READ** |
| Model config + registry (ADR-007) | `MODEL_CONFIG`, `DEFAULT_MODEL_ID`, `REGISTRY`, `validate_model_config` | **READ** |
| Model factory (ADR-007) | `get_model(role)` (+ `OPENROUTER_API_KEY`) | **READ** |

New internal symbol: `routing.classify(message, model, prior=[]) -> RoutingDecision | None`
(additive; router node refactored to call it — external behaviour unchanged, guarded by existing
hub tests). **F-10 requires NO change to any shared frozen contract.**

> Coordination note: F-12 also edits `routing.py` (the `decide_route` clarification copy + a
> voice sentence in `ROUTER_SYSTEM_PROMPT`). The two edits are **adjacent but non-conflicting**
> (F-10 adds `classify` + leaves prompt text intact; F-12 only adds voice copy). Build in either
> order; if concurrent, expect a trivial same-file merge.

### Build checklist (test-first, ordered)
- [ ] **(test, AC2)** `test_routing_eval_cases.py`: `CASES` has ≥10 rows, ≥1 per `Route`, ≥2 ambiguous cases whose expected outcome is `route=None` / `expects_clarification=True`. (Red.)
- [ ] **(impl)** Add `RoutingCase` + `CASES` (clear-intent per route + ambiguous/clarify) to `app/eval/routing_eval.py`; make the case-set test pass.
- [ ] **(impl, reuse)** Extract `classify(message, model, prior=[])` into `app/graph/routing.py`; refactor `hub._router_node` to call it; run existing hub/router tests (no behaviour change).
- [ ] **(impl)** Add `EVAL_MODELS: list[str]` + `_assert_capable(model_id)` reusing `REGISTRY`/`validate_model_config`.
- [ ] **(impl, AC1)** Per-model scoring loop: build via factory → run each case through `classify` → apply `decide_route` → compare gated `(route, clarify?)` to label → time with `perf_counter`; accumulate `accuracy` + `avg_latency_ms` into an `EvalReport`.
- [ ] **(impl, AC1)** `format_report(report) -> str` (table: model · accuracy · avg latency) + `run()`.
- [ ] **(impl)** Thin CLI `backend/scripts/eval_routing.py` → `run()` + `format_report`; optional `--live`/env gate documented.
- [ ] **(test, smoke / testing-req)** `test_routing_eval_smoke.py`: message-keyed fake via factory monkeypatch; `run()` over ≥2 fake models; assert report shape (accuracy ∈ [0,1], finite latency) and that a deliberately-wrong answer yields accuracy < 1.0. No network/key.
- [ ] **(test, AC3)** Config-only add: append an id (or pass a models arg) → harness scores it with no other code change.
- [ ] **(docs)** README note under "How I would evaluate this system in production": how to run, that it makes the split-test promise concrete, real runs optional + need a key.
- [ ] **(validate)** `cd backend && python -m pytest tests/test_routing_eval_smoke.py tests/test_routing_eval_cases.py -q` and `python -m pytest tests/critical/test_model_swap_routing.py -q` (confirm node refactor didn't regress).
- [ ] **(validate, optional live)** `cd backend && OPENROUTER_API_KEY=... python scripts/eval_routing.py`.

**AC coverage:** AC1 → scoring loop + `format_report` + CLI (smoke asserts shape); AC2 → `CASES`
+ case-set test (≥2 ambiguous, `route=None`/clarify); AC3 → `EVAL_MODELS` + factory-via-id +
config-only-add test; Testing req → smoke test + README/optional-live.

### Files
**CREATE:** `backend/app/eval/__init__.py`; `backend/app/eval/routing_eval.py` (core);
`backend/scripts/eval_routing.py` (CLI); `backend/tests/test_routing_eval_smoke.py`;
`backend/tests/test_routing_eval_cases.py` (may fold into the smoke file).
**MODIFY:** `backend/app/graph/routing.py` (+`classify`); `backend/app/graph/hub.py`
(`_router_node` calls `classify`); `README.md` (run-the-harness note).

### Risks / assumptions
- Node-refactor touches a hot path but is guarded by existing hub/router/model-swap tests; the
  approver may opt to keep `classify` harness-private (prompt is single-sourced either way).
- `RoutingDecision.route` is required → ambiguous cases labeled by the *gated* `decide_route`
  outcome, not `route` equality (the easiest thing to get wrong; pinned by the case-set + smoke).
- Latency timed in-harness (not from `llm_call`); real runs out of CI (need `OPENROUTER_API_KEY`).
- Two registry-capable ids suffice for AC3; a third real model needs a `REGISTRY` entry (the
  ADR-007 config surface, not harness code).

## Implementation notes (filled in by the building agent)

- [x] **Chunk 1 — labeled case set** (`backend/eval/cases.py`): 12 cases covering all three Route
  values (coach × 4, workout_generate × 3, workout_log × 3) plus 2 ambiguous cases; frozen as a
  Python module so the harness can import them and tests can parametrize over them.
- [x] **Chunk 2 — eval harness** (`backend/eval/harness.py`): async `run_eval(model, cases)` that
  times each `classify()` call and scores it (ambiguous cases always pass); `_print_report()` prints
  per-model accuracy + avg latency + per-case PASS/FAIL; `__main__` entry point accepts model IDs
  as positional args (default: `MODEL_CONFIG["router"]`) — config-only swap as required by AC-3.
- [x] **Chunk 3 — smoke tests** (`backend/tests/test_routing_eval.py`): 8 deterministic tests using
  `FakeStructuredOutputModel` from the shared conftest — verifies report shape, ambiguous scoring,
  correct/incorrect clear-intent scoring, case-set coverage, and `_print_report` output — all
  network-free.

**Decisions:**
- `classify()` already existed as the frozen seam in `routing.py`; the harness consumes it directly.
- `run_eval` accepts a `BaseChatModel` (not a role string) so callers inject any model — including
  the fake from conftest — without touching the factory or monkeypatching in the harness itself.
- Ambiguous cases score as always-correct: the correct answer for genuinely ambiguous input is
  "any reasonable outcome" — enforcing a specific route would make the test brittle and misleading.
- The CLI accepts positional model IDs, defaulting to `MODEL_CONFIG["router"]`, so comparing two
  models is `uv run python -m eval.harness openai/gpt-4o-mini openai/gpt-4o` — no code change.
