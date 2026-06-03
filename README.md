# Cadence

**A multi-agent fitness coach.** A LangGraph hub routes each chat message to one
of three specialist sub-agents — answer a question, generate a workout, or log a
session — and streams the reply back over SSE into a branded React chat UI.

```
                      ┌──────────── hub StateGraph (LangGraph) ────────────┐
  React chat UI       │  router ──► COACH ───────► coach subgraph          │
  (Vite + Tailwind)   │  (LLM      WORKOUT_GENERATE ► generator subgraph   │
        │  POST /chat │   structured  WORKOUT_LOG ──► logger subgraph      │
        └──SSE stream─┤   output)  └► clarify (low-confidence fallback)    │
                      │  response assembly ──► ChatResponse / SSE events   │
                      └────────────────────────────────────────────────────┘
```

Each sub-agent is its **own** `StateGraph` composed into the hub through a
boundary-adapter node — the hub and a sub-agent never share a mutable state key.

## Quick start (Docker)

**Prerequisites:** Docker + Docker Compose. You need an
[OpenRouter](https://openrouter.ai) API key (any LLM provider works — the model
layer is provider-agnostic; OpenRouter is the default).

```bash
git clone <repo-url> && cd cadence
cp .env.example .env                      # then add your OPENROUTER_API_KEY
docker compose up
```

Open **http://localhost:8000** — the frontend serves the UI and reverse-proxies
the API to the backend, so everything runs through this one port.

## Local development (no Docker)

Backend — Python 3.12 + [uv](https://docs.astral.sh/uv/):

```bash
cp .env.example .env                       # at repo root; add OPENROUTER_API_KEY
cd backend
uv sync
uv run uvicorn app.main:app --reload       # http://localhost:8000
```

The backend loads `.env` from the repo root regardless of where you run it from.

Frontend — Node 20:

```bash
cd frontend
npm install
npm run dev                                # http://localhost:8001, proxies /chat → :8000
```

## Running tests

The backend suite runs **fully offline** — it injects fake models through the
`get_model` seam, so **no API key is required**. The critical-path tests live
under `backend/tests/critical/` and run as part of the default suite:

```bash
cd backend && uv run pytest                # 258 passed, 4 skipped (live-only, skip offline)
cd frontend && npm test
```

## What's built

All three routes plus a confidence-gated clarify fallback, the three sub-agents,
resilience hardening, and streaming, multi-turn memory, injury avoidance,
bilateral pairing, and observability:

| Capability | Notes |
|---|---|
| **Router** | LLM `with_structured_output()` → `Route` enum + confidence; low confidence asks a clarifying question instead of misrouting |
| **Coach** | Fitness Q&A in a consistent coach voice |
| **Workout Generator** | Tool-calling agent (`search_exercises`, `build_workout`) over the 50-exercise dataset, with an output-validation gate that rejects hallucinated IDs |
| **Workout Logger** | Parses sets/reps/weight from natural language, fuzzy-matches the exercise (RapidFuzz, resolve-or-flag) |
| **Resilience** | Empty/invalid searches and bad tool calls recover gracefully — never crash, never invent exercises |
| **Streaming** | Token + structured-payload SSE events |
| **Multi-turn memory** | Per-session checkpointer thread; "make it shorter" resolves against the prior workout |
| **Injury avoidance** | Hard pre-filter + output gate exclude any exercise loading an injured joint (`joints_loaded`) |
| **Bilateral pairing** | A selected unilateral exercise auto-includes its opposite side |
| **Observability** | Structured JSON logs for every route, LLM call, and tool call (secrets redacted); optional LangSmith tracer via env |

A full worked **[demo transcript](docs/demo/transcript.md)** captures all three
routes, the clarify path, and a resilience recovery from a running instance.

The design history lives in [`docs/`](docs/) — [PRD](docs/PRD.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [ADRs](docs/adrs/), and the iteration plans.

## Model configuration

Every agent role resolves its model through the single `get_model(role)` factory
in `backend/app/models/factory.py` — no node constructs a client directly. The
role→model map lives in `backend/app/models/config.py`; point any role at a
different model id with no code change (this is also the split-test seam).

| Role | Default | Structured output |
|------|---------|-------------------|
| `router` | `openai/gpt-4o-mini` | required |
| `coach` | `openai/gpt-4o-mini` | — |
| `generator` | `openai/gpt-4o-mini` | required |
| `logger` | `openai/gpt-4o-mini` | required (name-match verify) |

`validate_model_config()` runs at startup and **fails fast** if any
structured-output role maps to a model that is unknown to the capability registry
(`backend/app/models/registry.py`) or lacks structured-output support — a
misconfigured swap never reaches a live turn.

## Critical-path tests (and why these)

Five critical-path tests live under
[`backend/tests/critical/`](backend/tests/critical/); the two highest-stakes are:

1. **No-hallucination / output gate** (`test_recovery_no_hallucination.py`,
   `test_output_gate.py`) — every `exercise_id` leaving the generator must
   resolve in the dataset. An invented exercise presented as a real
   recommendation is the worst failure this system can produce, so it's gated at
   the graph boundary and tested directly (empty-search recovery + bad tool-call
   recovery + the gate itself).
2. **Injury hard-exclusion** (`test_injury_hard_exclusion.py`) — a workout built
   under a knee injury must contain **zero** knee-loading exercises. This is a
   physical-safety invariant, not a preference, so it's enforced as a hard
   pre-filter *and* re-checked at the gate.

The other three lock routing under a config-only model swap
(`test_model_swap_routing.py`), the logger's deterministic resolve-or-flag
(`test_logger_resolve_or_flag.py`), and the output gate in isolation.

## How I would evaluate this system in production

Offline tests prove correctness invariants; production tells you whether the
coach is actually *good*. The three signals that matter most:

### 1. Acceptance rate of proposed workouts

The headline product metric: of the workouts the generator proposes, what
fraction does the user actually accept — start, save, or log having done — rather
than discard, immediately re-ask ("make it shorter / different"), or abandon?

- **Measure:** `workouts_accepted / workouts_proposed`, where *accepted* is an
  explicit downstream signal (the user saves it, or later logs a session matching
  it). An immediate adjustment request on the same session ("make it easier") is a
  soft-reject — track that re-prompt rate as the leading indicator.
- **Slice it:** by route confidence, by whether an injury filter or bilateral
  pairing fired, by target muscle group, and by whether the output gate had to
  retry. A pairing or exclusion that tanks acceptance is a product bug even though
  every correctness test stays green.
- **Why it's the north star:** the no-hallucination gate and injury exclusion
  guarantee a workout is *safe and valid*; acceptance is the only thing that tells
  you it's *wanted*. A 100%-valid workout nobody starts is a failure the test
  suite can't see.

### 2. Split-testing: models and prompt variations

`get_model(role)` is the single injection point for every LLM in the system, and
each agent's prompt is a swappable unit — so both model and prompt are A/B-able
per role without touching graph code.

- **Model swaps:** canary a role onto a different model via `MODEL_CONFIG` (or an
  env override read at startup) — e.g. route 10% of router traffic through a
  stronger model — and compare **acceptance rate, misroute rate, clarification
  rate, and latency/cost** per cohort. The capability registry validates the swap
  at startup so a misconfigured model never reaches a live turn, and the
  critical-path tests run identically under any swap (proven by
  `test_model_swap_routing.py`), so the suite is the correctness baseline for both
  arms.
- **Prompt variations:** version each agent's system prompt and run the same
  cohort split — does a more directive generator prompt raise acceptance? does a
  warmer coach voice raise return rate? Hold the model fixed, vary the prompt, and
  read the same downstream metrics.
- **Scaling it up:** a replay harness that runs a labelled message corpus through
  both arms and logs `route`, `routing_confidence`, and the accepted/rejected
  outcome gives per-arm precision/recall plus acceptance lift — the offline analog
  of the live experiment.

### 3. User stickiness and retention

Whether people *come back* to the agent is the truest measure that the
recommendations are worth anything.

- **Return rate:** of users who engaged the recommendation system, what fraction
  return within 7 / 30 days and engage again? Cohort by first-touch route (did the
  people who got a workout come back more than those who only asked a question?).
- **Save / reuse:** do users **save** proposed workouts, and do they **re-run or
  log** a saved workout later? A saved-but-never-reused workout and a
  saved-and-repeated one are very different signals — the log repository already
  captures completed sessions, so saved-vs-done is directly measurable.
- **Engagement depth:** sessions per returning user, multi-turn refinement depth
  (the memory feature exists to support "adjust it" — is it actually used?), and
  the share of returning users who log a workout vs. only browse. Falling depth on
  a stable acceptance rate is an early churn signal worth alerting on.

**What makes all three observable:** the structured-logging layer records the
route, every LLM and tool call, confidence, and gate outcome for each turn
(secrets redacted), and the log repository persists accepted/logged sessions — so
acceptance, experiment cohorts, and return behaviour are all reconstructable from
data the system already emits.

## Design tokens

All UI colors, fonts, and spacing come from `frontend/tailwind.config.js`. The
`accent` token (`#00C2A8`, teal family) is a default pending an eyedropper
confirmation against the live brand reference — see `frontend/BRAND.md`.
