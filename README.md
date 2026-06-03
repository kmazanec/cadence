# Cadence

**A multi-agent fitness coach.** A LangGraph hub routes each chat message to one
of three specialist sub-agents — answer a question, generate a workout, or log a
session — and streams the reply back over SSE into a branded React chat UI.

This repo is the take-home for the Fitness Coaching Multi-Agent System brief; the
section [Mapping to the brief](#mapping-to-the-brief) shows where each requirement
lives.

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
cp backend/.env.example backend/.env      # then add your OPENROUTER_API_KEY
docker compose up
```

Open **http://localhost:5173**. (Backend serves on `:8000`.)

## Local development (no Docker)

Backend — Python 3.12 + [uv](https://docs.astral.sh/uv/):

```bash
cd backend
uv sync
cp .env.example .env                       # add OPENROUTER_API_KEY
uv run uvicorn app.main:app --reload       # http://localhost:8000
```

Frontend — Node 20:

```bash
cd frontend
npm install
npm run dev                                # http://localhost:5173, proxies /chat → :8000
```

## Running tests

The backend suite runs **fully offline** — it injects fake models through the
`get_model` seam, so **no API key is required**:

```bash
cd backend && uv run pytest                # 258 passed, 4 skipped (live-only, skip offline)
cd frontend && npm test
```

## What's built

The three brief routes plus a confidence-gated clarify fallback, all three
sub-agents, resilience hardening, and **every stretch goal**:

| Capability | Notes |
|---|---|
| **Router** | LLM `with_structured_output()` → `Route` enum + confidence; low confidence asks a clarifying question instead of misrouting |
| **Coach** | Fitness Q&A in a consistent coach voice |
| **Workout Generator** | Tool-calling agent (`search_exercises`, `build_workout`) over the 50-exercise dataset, with an output-validation gate that rejects hallucinated IDs |
| **Workout Logger** | Parses sets/reps/weight from natural language, fuzzy-matches the exercise (RapidFuzz, resolve-or-flag) |
| **Resilience** | Empty/invalid searches and bad tool calls recover gracefully — never crash, never invent exercises |
| **Streaming** (stretch) | Token + structured-payload SSE events |
| **Multi-turn memory** (stretch) | Per-session checkpointer thread; "make it shorter" resolves against the prior workout |
| **Injury avoidance** (stretch) | Hard pre-filter + output gate exclude any exercise loading an injured joint (`joints_loaded`) |
| **Bilateral pairing** (stretch) | A selected unilateral exercise auto-includes its opposite side |
| **Observability** (stretch) | Structured JSON logs for every route, LLM call, and tool call (secrets redacted); optional LangSmith tracer via env |

A full worked **[demo transcript](docs/demo/transcript.md)** captures all three
routes, the clarify path, and a resilience recovery from a running instance.

The design history lives in [`docs/`](docs/) — [PRD](docs/PRD.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [ADRs](docs/adrs/), and the iteration plans.

## Model configuration

Every agent role resolves its model through the single `get_model(role)` factory
in `backend/app/models/factory.py`. The role→model map is in
`backend/app/models/config.py` — point any role at a different model id with no
code change. `validate_model_config()` runs at startup and refuses to boot if a
structured-output role maps to an unknown or incapable model.

| Role | Default | Structured output |
|------|---------|-------------------|
| `router` | `openai/gpt-4o-mini` | required |
| `coach` | `openai/gpt-4o-mini` | — |
| `generator` | `openai/gpt-4o-mini` | required |
| `logger` | `openai/gpt-4o-mini` | required (name-match verify) |

## Critical-path tests (and why these)

The brief asks for the paths *that matter most*. The suite designates five under
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

## Mapping to the brief

| Brief requirement | Where |
|---|---|
| Hub is a LangGraph `StateGraph`, typed state, explicit edges | `backend/app/graph/hub.py`, `state.py` |
| Sub-agents are separate graphs composed into the hub | `backend/app/agents/{coach,generator,logger}/graph.py` |
| Routing via LLM structured output + confidence/fallback | `backend/app/graph/routing.py`; clarify on low confidence |
| Tools have Pydantic input schemas with field descriptions | `backend/app/agents/generator/tools.py` |
| Resilience (no results / invalid tool call recovers) | output gate + bounded retry; `tests/critical/test_recovery_no_hallucination.py` |
| ≥ 2 critical-path tests + rationale | [Critical-path tests](#critical-path-tests-and-why-these), `tests/critical/` |
| Runnable demo / transcript | [`docs/demo/transcript.md`](docs/demo/transcript.md) + the live UI |
| "How I'd evaluate in production" README section | [below](#how-i-would-evaluate-this-system-in-production) |
| Stretch: streaming, memory, injury avoidance, bilateral pairing, observability | all shipped — see [What's built](#whats-built) |

## How I would evaluate this system in production

A short version below; the **full writeup** (per-metric targets, signals,
tooling) is in [`backend/README.md`](backend/README.md#how-i-would-evaluate-this-system-in-production).

- **Routing accuracy.** Sample labelled turns and measure correct-dispatch rate
  (target ≥ 95% on unambiguous messages). Every turn already logs `route` and
  `routing_confidence` — watch the **misroute rate**, the **clarification rate**
  (too high ⇒ under-confident router; too low ⇒ over-confident and misfiring),
  and confidence-histogram drift week over week.
- **No-hallucination rate.** The output gate (`validate_workout`) enforces that
  every exercise id resolves; the production metric is how often it *fires*
  (`retry_count > 0`) and whether the retry budget is ever exhausted (a missed
  generation). The gate's `unknown_ids` are structured — alert if any id recurs.
- **Logger match quality.** Watch the RapidFuzz match-score distribution; scores
  clustered at the cutoff (80) mean speculative matches — lower the cutoff or add
  catalogue entries for the frequent near-misses.
- **Failure modes to monitor.** Silent misroute, hallucinated exercise escaping
  the gate, injury-exclusion bypass, retry-ceiling exhaustion, and SSE stream
  errors. The structured-logging layer (route + every LLM/tool call, secrets
  redacted) is what makes each of these reconstructable from a single turn.
- **Model split-testing.** `get_model(role)` is the one injection point —
  canary a role onto a stronger model via `MODEL_CONFIG` (or an env override) and
  compare misroute/clarification/latency per cohort. The critical-path tests run
  identically under any swap, so the suite is the correctness baseline.

## Design tokens

All UI colors, fonts, and spacing come from `frontend/tailwind.config.js`. The
`accent` token (`#00C2A8`, teal family) is a default pending an eyedropper
confirmation against the live brand reference — see `frontend/BRAND.md`.
