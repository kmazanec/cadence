# Cadence backend

FastAPI + LangGraph backend for the Cadence fitness chat coach.

## Setup (clean clone)

```bash
# 1. Install dependencies (no network beyond PyPI)
uv sync

# 2. Create .env with your OpenRouter key (only needed for live model calls)
cp .env.example .env   # fill in OPENROUTER_API_KEY

# 3. Run the deterministic test suite (offline — no API key required)
uv run pytest

# 4. Start the server
uv run uvicorn app.main:app --reload
```

The deterministic suite (`pytest`) uses fake models injected via the
`get_model` seam — it runs entirely offline. The critical-path tests live
under `tests/critical/` and run as part of the default suite.

## Models (role → model map)

Every agent role obtains its model through the single `get_model(role)` factory
(`app/models/factory.py`); no node constructs a client directly. The role →
model mapping lives in `app/models/config.py` and is overridable per role:

| Role        | Default model        | Structured output required |
| ----------- | -------------------- | -------------------------- |
| `router`    | `openai/gpt-4o-mini` | yes                        |
| `coach`     | `openai/gpt-4o-mini` | no                         |
| `generator` | `openai/gpt-4o-mini` | yes                        |
| `logger`    | `openai/gpt-4o-mini` | yes (name-match verify)    |

`validate_model_config()` runs at startup and fails fast if any
structured-output role maps to a model that is unknown to the capability
registry (`app/models/registry.py`) or lacks structured-output support. To
split-test a role, point its entry in `config.py` at another registered model
id — no code change required.

## How I would evaluate this system in production

### Routing accuracy

**Metric:** The fraction of turns where the router dispatches to the correct
subgraph, measured by sampling a held-out set of labelled messages (ground
truth from human annotation or replay logs). A practical target is ≥ 95 %
exact-match accuracy on unambiguous turns.

**Signals to watch:**
- Clarification rate: the fraction of turns that hit the below-threshold
  branch. Too high (> 15 %) suggests the router model is under-confident;
  too low (< 1 %) may mean it is over-confident and misfiring on genuinely
  ambiguous messages.
- Misroute rate: turns that reach the wrong subgraph, detectable by logging
  the `route` field on `HubState` and comparing to human-reviewed session
  replays.
- Fallback-to-coach rate: turns that were WORKOUT_GENERATE or WORKOUT_LOG
  but got routed to COACH, diluting the specialist agents.

**Tooling:** emit `routing_confidence` and `route` as structured log fields
on every turn. A weekly histogram of confidence scores exposes model drift
early. A/B test a second router model (swap via `MODEL_CONFIG` — no code
change) and compare misroute rates.

### No-hallucination rate

**Metric:** The fraction of generated workouts where every exercise_id in the
payload resolves in the dataset. The output gate (`validate_workout`) already
enforces this at the graph boundary; the production metric is how often the
gate fires (retry_count > 0) and whether the retry budget is ever exhausted.

**Signals to watch:**
- Gate-trigger rate: exercises per workout that fail the gate on the first
  try. Persistent high rates signal the model is drifting toward inventing IDs.
- Retry-ceiling hits: turns where `retry_count == RETRY_CEILING` and the
  final workout is `None` (graceful degrade). Track these as missed generations.
- Unknown-ID log: every unknown exercise_id caught by the gate should be
  logged; a recurring unknown ID may indicate a dataset gap worth filling.

**Tooling:** the gate's `GateResult.unknown_ids` is already structured; route
it to a log sink and alert if any ID appears more than once per 100 turns.

### Clarification rate and correctness signals

**Metric:** The clarification rate (turns that go to the clarify node) is a
leading indicator of routing quality and also a UX friction metric. Accepted
clarifications (user responds with a more specific follow-up) vs. abandoned
turns (session ends after clarification) measure whether the fallback is
actually helping.

**Signals to watch:**
- Clarification-to-resolution rate: fraction of clarification turns that
  produce a successful downstream dispatch on the follow-up.
- Option selection distribution: which of the three clarification options
  users pick. A heavily skewed distribution may indicate confusing phrasing.
- Logger fuzzy-match score distribution: the RapidFuzz WRatio score at which
  entries are matched. Scores clustered near 80 (the cutoff) flag exercises
  that are being matched speculatively; lower the cutoff or add catalogue
  entries for the most frequent near-misses.

### Model split-testing story

The `get_model(role)` factory is the single injection point for every model
used in the system. Swapping a role to a different model requires only a one-
line change to `MODEL_CONFIG` in `app/models/config.py` — or, for a production
canary, an env-var override read at startup with no restart. The capability
registry (`REGISTRY` in `app/models/registry.py`) validates the swap at
startup so a misconfigured model never reaches a live turn.

A practical A/B test: route 10 % of traffic through a canary `MODEL_CONFIG`
pointing the `router` role at `openai/gpt-4o` while the control uses
`openai/gpt-4o-mini`. Measure misroute rate, clarification rate, and latency
separately for each cohort. The routing tests in `tests/critical/` run
identically against both configurations (as proven by `test_model_swap_routing.py`),
so the test suite is the baseline for correctness under any swap.

A more systematic eval at scale: build a replay harness that replays a
labelled message corpus against the live system and logs `route`,
`routing_confidence`, and `subgraph_result.kind`. Compute precision/recall
per route arm. This is deliberately deferred to a later iteration — the
machinery above (structured state, observable route field, offline test suite)
is the foundation it runs on.
