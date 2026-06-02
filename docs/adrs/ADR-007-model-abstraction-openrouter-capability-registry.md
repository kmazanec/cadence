# ADR-007: Model abstraction over OpenRouter — ChatOpenAI factory, per-role config, static capability registry

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The LLM must be **swappable via config without changing agent logic**, ship one sensible default, and
**make explicit which configured models support structured output / tool calling** — because routing
(ADR-005) and the Generator's tool calls require that capability (PRD reqs 22–24, §8.3). Research:
OpenRouter is OpenAI-API-compatible (so LangChain's `ChatOpenAI` with a `base_url` override works
directly), and structured-output support **varies by underlying model**, reliable on OpenAI/Anthropic
and flaky/absent on some open-weight models (TECHNOLOGY.md §structured output; PRD §8.3).

Serves: PRD reqs 22–24 (model abstraction & evaluation), criterion 21 (swap model, routing tests
still pass), §8.3 (capability variance risk).

## Options considered

**Implementation:**
- **Custom HTTP wrapper.** Most control, but reinvents `ChatOpenAI` and risks losing LangChain's
  structured-output/tool plumbing. Rejected for a take-home.
- **`init_chat_model('provider:model')`.** Provider-agnostic by config string; slightly more
  indirection. Viable, kept as a fallback path.
- **`ChatOpenAI` + `base_url` → OpenRouter, behind a thin `get_model(role)` factory (chosen).**
  Idiomatic, minimal, `with_structured_output` works out of the box.

**Capability representation:**
- **Runtime probe.** Live-accurate but adds startup latency/token cost and is flaky in CI/offline.
  Rejected — over-engineered for M1.
- **No registry, trust the id.** Violates req 23 and turns a config typo into a runtime crash.
  Rejected.
- **Static checked-in registry + fail-fast startup validation (chosen).**

**Per-role assignment:**
- **Single model everywhere.** Simplest, but loses the per-role split-test narrative (req 24).
- **Per-role config with shared default (chosen).**

## Decision

A thin **`get_model(role)` factory** returns a LangChain `ChatOpenAI` configured against OpenRouter's
OpenAI-compatible `base_url`, with the API key from env. Config maps each **role** —
`router | coach | generator | logger` — to a model id, all defaulting to one capable model but
individually overridable. A checked-in **capability registry** maps `model_id → { supports_structured_output,
supports_tools, context_window, notes }`. On startup, the app **validates** that the models assigned
to roles requiring structured output (router, generator; logger if LLM-extraction is used) are flagged
capable, and **fails fast with a clear message** otherwise.

## Rationale

`ChatOpenAI` + `base_url` is the least-code, most-idiomatic way to get OpenRouter swappability with
working structured output — no custom client to maintain. The static registry makes capability
**explicit and testable in-repo** (req 23) and converts a whole class of "model can't do structured
output" runtime failures into a clear startup error. Per-role config is near-zero extra code and
directly enables the README's split-testing story (req 24) and natural cost/latency tuning (cheap-fast
router, stronger generator). Swapping the default to another capable model is config-only, satisfying
criterion 21.

## Tradeoffs & risks

- **The static registry can drift** from OpenRouter's actual, changing capabilities. Mitigation: the
  registry has a `notes`/`last_verified` field; it's documented as a curated allow-list, not a live
  truth; unknown models default to "unverified" and are rejected for structured-output roles unless
  explicitly flagged. A user can add an entry deliberately.
- **OpenRouter as a single dependency / point of failure.** Accepted for M1; `init_chat_model` remains
  an escape hatch to target a native provider by config if needed.
- **Per-role models can mask a weak default** in testing. Mitigation: default all roles to the same
  model so the out-of-box path is uniform; overrides are opt-in.

## Consequences for the build

- **Contract (model config + capability registry).** Shared shape the eval/split-test story (req 24)
  and M6 both build on.
  - **Source of truth:** `backend/app/models/registry.py` (capability registry) +
    `backend/app/models/factory.py` (`get_model(role)`) + `config` (role→model map, env for keys).
  - **Shape (initial):** `Role = router | coach | generator | logger`; registry entry
    `{ supports_structured_output: bool, supports_tools: bool, context_window: int, notes: str }`;
    config `{ role: model_id }` with a single default model id.
  - **Exhaustive consumers:** every node that instantiates a model goes through `get_model(role)`
    (never constructs a client directly); startup validation; the README eval section. Adding a role
    means adding it to the enum, the config map, and the validation.
- **Policy:** no agent node constructs an LLM client directly — all model access is via
  `get_model(role)`. API keys come from env/config only (ADR-011), never hardcoded.
- **Policy:** models for structured-output roles must be registry-flagged capable; startup fails fast
  otherwise.
