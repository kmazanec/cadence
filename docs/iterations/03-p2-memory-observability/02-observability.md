# Feature: Observability — structured tracing (P2)

**ID:** F-09 · **Iteration:** 03-p2-memory-observability · **Status:** Not started

## What this delivers (before → after)
**Before:** A request's internal path (route, model calls, tool calls) is opaque.
**After:** Every LLM call and tool invocation is recorded in structured logs so that, for any user
message, the route taken and each tool call with its outcome can be reconstructed — with secrets
redacted. An optional vendor tracer can be enabled by env.

## How it fits the roadmap
Second feature of iteration 03 (P2 depth); independent of F-08 within the iteration (both extend
iteration-01 features, neither consumes the other). Underpins the README's evaluation story.

## Requirements traced (from the PRD)
Reqs 24 (evaluation story), 26; acceptance criterion 23.

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: the route taken is a core thing to log; instrumentation hooks attach
  at the router + tool nodes + model factory.
(Instruments the F-01 `get_model` factory and the F-04/F-05 tool nodes — contract-mediated, not hard
deps on those features' behavior.)

## Unblocks (what waits on this)
- Nothing downstream in M1.

## Contracts touched
- Conforms to the model-factory + tool-node instrumentation points (ADR-007/017). Introduces no shared
  data contract; the log shape is internal.

## Acceptance criteria (product behavior)
1. For a processed message, the structured log lets an operator reconstruct: the route taken, each LLM
   call (role, model, latency), each tool invocation (name, outcome/error), retry counts, total
   latency.
2. Secrets (API keys) never appear in logs (redacted).
3. A vendor tracer (LangSmith/Langfuse) is enabled only when its key is present; the app runs and
   tests fully without it.

## Testing requirements
- **Integration:** run a request and assert the emitted structured log contains the route + at least
  one tool/model event with outcome, and contains no secret value.

## Manual setup required
- Optional: a tracing-vendor key to demo the vendor path (not required to run/test).

## Implementation notes (filled in by the building agent)

<!-- BUILD-PLAN:kmaz-plan-iteration -->

## Build plan (kmaz-plan-iteration) — F-09

**Model tier:** `sonnet`

F-09 is greenfield structured-logging instrumentation woven around three existing seams: the single get_model(role) model factory (backend/app/models/factory.py:19), the router node (backend/app/graph/hub.py:_router_node), and the generator tool dispatch (backend/app/agents/generator/graph.py _execute_search/_execute_build_workout). The build adds a small stdlib-logging-based structured JSON emitter (no new required dependency), a request-scoped correlation context keyed on session_id, redaction of the OpenRouter API key, and an optional env-gated LangSmith tracer (langsmith is already a transitive dep) that no-ops unless its key is present. Per-LLM-call latency/role/model and per-tool-call name/outcome are timed by wrapping the model returned from get_model and by emitting events at the tool dispatch sites; route + total latency are logged at the request boundary in _stream_chat. The hard constraint is that none of this may break the schema-aware fake-model seam in tests/conftest.py — instrumentation must wrap INSIDE get_model (preserving the monkeypatch of app.models.factory.get_model) rather than replace the symbol.

### Reuse — already exists, do NOT rebuild

- Single model-construction seam get_model(role) — the one place to instrument every LLM call (router/coach/generator/logger all flow through it)  
  _backend/app/models/factory.py:19 def get_model(role: Role) -> BaseChatModel_
- langsmith is ALREADY available (transitive dep) — the optional vendor tracer needs no new dependency, just an env-gated import guard. The spec implies adding a vendor tracer; the package is present.  
  _backend/uv.lock entries: name = "langsmith" (0.8.8)_
- API_KEY_ENV constant ('OPENROUTER_API_KEY') and base_url already centralized — redaction has exactly one secret to scrub and one canonical name  
  _backend/app/models/config.py:20 API_KEY_ENV: str = "OPENROUTER_API_KEY"_
- Router node already captures routing_raw and routing_confidence into state — the 'route taken' is already observable from node output; F-09 just needs to LOG it (route + confidence), not derive it  
  _backend/app/graph/hub.py:78-87 result dict with route/routing_confidence/routing_raw_
- Request entry point already creates session_id and is the natural place for request-scoped correlation id + total-latency timing  
  _backend/app/api/chat.py:54 session_id = request.session_id or str(uuid.uuid4())_
- Tool dispatch sites are concrete and synchronous — _execute_search and _execute_build_workout return outcome strings/payloads, ideal hook points for per-tool-call name+outcome events  
  _backend/app/agents/generator/graph.py:162-179 tool_calls loop dispatching search_exercises/build_workout_
- Generator and logger consume the factory as `import app.models.factory as _factory; _factory.get_model(...)`, so they pick up monkeypatch of app.models.factory.get_model automatically — instrumentation that wraps inside get_model is transparently covered by the existing fake seam  
  _backend/app/agents/generator/graph.py:27 import app.models.factory as _factory; :131 _factory.get_model('generator'); backend/app/agents/logger/graph.py:99_
- Existing bare logger in chat.py — reuse logging config conventions; do not introduce a second logging framework that fights it  
  _backend/app/api/chat.py:31 logger = logging.getLogger(__name__)_
- Schema-aware fake-model seam that MUST keep passing — conftest monkeypatches three import sites of get_model  
  _backend/tests/conftest.py:137-143 monkeypatch.setattr app.models.factory.get_model / app.graph.hub.get_model / app.agents.coach.graph.get_model_

### Contrarian risks & mitigations

- **Risk:** Wrapping get_model by replacing the symbol (e.g. an @decorator reassigning app.models.factory.get_model) will silently defeat the test fake: conftest monkeypatches app.models.factory.get_model AND app.graph.hub.get_model. If the latency wrapper lives outside and hub.py imported the wrapped name, the monkeypatch replaces the whole thing and instrumentation is gone in tests AND the wrapper could swallow the fake in prod ordering.  
  **Mitigation:** Do the timing wrap INSIDE get_model's body: build the ChatModel, then return a thin latency-recording proxy. The monkeypatch replaces the entire get_model function in tests (returning the fake un-proxied), which is fine — instrumentation is exercised by a SEPARATE direct unit test on the proxy + an integration test that patches get_model to a fake that still routes through a real instrumented wrap. Do NOT add a module-load-time decorator that mutates the factory symbol.
- **Risk:** Timing an LLM via a Runnable proxy is fragile: langchain models are Runnables with ainvoke/astream/with_structured_output/bind_tools. The router calls .with_structured_output(...).ainvoke; generator calls .bind_tools(...).ainvoke; coach calls .ainvoke. A naive proxy that only wraps .ainvoke misses with_structured_output and bind_tools chains, so router/generator LLM calls go untimed.  
  **Mitigation:** Prefer the lighter-weight approach: emit the llm_call event at each CALL SITE (router node, coach node, generator node) using a small timing context manager from an instrumentation module, rather than proxying the BaseChatModel surface. This is fewer moving parts, dodges the Runnable-wrapping rabbit hole, and keeps the fake seam untouched. The spec's acceptance bar is 'role, model, latency' per call — all available at the call site from the role arg + MODEL_CONFIG[role].
- **Risk:** Per-request correlation: stdlib logging has no implicit request context. If you stuff session_id into every event via function args you thread it through router/tool/coach nodes that today take only state — but session_id IS already on HubState (state['session_id']) at the hub level, while subgraph nodes (coach/generator) do NOT receive session_id (isolated-state contract). So tool/LLM events emitted inside the generator subgraph cannot see session_id.  
  **Mitigation:** Use a contextvars.ContextVar set once in _stream_chat (api/chat.py) with the session_id; the instrumentation module reads it. contextvars propagate across await boundaries within the same task, covering subgraph nodes without violating the isolated-state contract. Document this as the correlation mechanism. Add a fallback of 'unknown' when unset (e.g. direct subgraph tests).
- **Risk:** The integration test 'contains no secret value' is only meaningful if a secret is actually present in the environment during the test. With OPENROUTER_API_KEY unset (offline CI default per ADR-018), the assertion is vacuously true and proves nothing.  
  **Mitigation:** The redaction test must set a sentinel OPENROUTER_API_KEY (monkeypatch.setenv) to a known fake value, exercise a path that could log it, then assert that value is absent from captured log output AND assert the redaction placeholder (e.g. '***REDACTED***') is what appears if/where the key would surface. Test redaction at the function level too (a redact() helper unit test), not only end-to-end.
- **Risk:** Spec/ADR-017 lists 'token usage if available' — OpenRouter via ChatOpenAI may not surface usage, and chasing it risks coupling to response.usage_metadata shapes that differ. Over-scoping.  
  **Mitigation:** Treat token usage as strictly optional/best-effort: log it only if present on the response, never assert on it, never fail without it (ADR-017 tradeoff explicitly allows absence). Keep it out of the critical-path test.
- **Risk:** structlog vs stdlib logging decision: adding structlog is a new required dependency for a CUT-ABLE P2 feature, contradicting ADR-017's 'zero required dependency' rationale and the clean-clone-run goal.  
  **Mitigation:** Use stdlib logging with a JSON formatter (json.dumps of an event dict) — no new dependency. This honors ADR-017 ('structured JSON logging ... zero required dependency') and keeps clean-clone trivial.
- **Risk:** langsmith is a TRANSITIVE dep today; importing it directly at module top-level couples F-09 to a package not declared in [project].dependencies, which could break if the transitive pin is dropped. Also LangSmith auto-traces via env vars (LANGCHAIN_TRACING_V2) without code — writing custom tracer glue may duplicate/fight that.  
  **Mitigation:** Gate the vendor path behind an env check (e.g. LANGSMITH_API_KEY / LANGCHAIN_API_KEY present) and import langsmith lazily inside that branch with a try/except ImportError that no-ops. Prefer simply honoring LangChain's native env-var tracing (set/leave LANGCHAIN_TRACING_V2) over bespoke client code — minimal surface, and the app/tests run fully when the key is absent. Do not add langsmith to required deps.
- **Risk:** Retry counts: the spec wants 'retry counts' logged, but generator retries live in GeneratorState.retry_count inside the isolated subgraph and are not visible to the hub/request boundary; the router's retry/safe-net is in F-06. Threading retry count out is non-trivial.  
  **Mitigation:** Log retry as a per-attempt event from inside the generate/gate loop (emit a 'retry' event when gate increments retry_count in _make_gate_node), so the count is reconstructable by counting events rather than threading an aggregate out. Acceptance criterion says 'retry counts' be reconstructable — event-per-retry satisfies it.

### Contract touchpoints

- **Model factory get_model(role) (ADR-007)** — No signature change. Instrumentation lives at CALL SITES (router/coach/generator/logger nodes) via a timing context manager, NOT inside get_model — preserving the fake-model monkeypatch seam. get_model stays the one-line factory.
- **Observability log shape (ADR-017)** — New, internal-only (ADR-017 'Contract: no'). Introduces backend/app/observability with a JSON event shape {event, session_id, ...}; no shared/cross-feature data contract, frontend unaffected.
- **Secrets redaction (ADR-015 → ADR-017)** — Implements the ADR-015 promise that 'the observability layer redacts secrets'. redact() scrubs os.environ[API_KEY_ENV] from any logged string. Already specified, now realized.
- **Optional vendor tracer (ADR-017)** — Env-gated enable_vendor_tracer() in observability/tracer.py, called from main.create_app(). langsmith stays a transitive dep (already in uv.lock); lazy import behind key presence; app+tests run fully without it.

### Build steps (checkbox)

- [ ] **1.** Create the instrumentation module: a stdlib-logging structured JSON emitter with a request-scoped correlation ContextVar and a redaction helper. Define event emitters: log_route(route, confidence), an llm_call timing context manager (role, model, latency_ms, optional usage), a tool_call emitter (name, outcome|error), a retry emitter, and a request-latency context manager. JSON-serialize each event via json.dumps over a dict that always carries session_id (from the ContextVar, default 'unknown') and event type. redact(text) scrubs any occurrence of os.environ[API_KEY_ENV] (when set) replacing with '***REDACTED***'.
  - Files: `backend/app/observability/__init__.py`, `backend/app/observability/logging.py`
  - Verify: Unit test test_redact_scrubs_api_key asserts redact(f'key={SECRET}') == 'key=***REDACTED***' when OPENROUTER_API_KEY=SECRET; test_event_is_json asserts emitted record is valid JSON with required keys (event,session_id).
- [ ] **2.** Write the redaction + event-shape unit tests FIRST (test-first) and confirm they fail before implementing, then make them pass with step 1.
  - Files: `backend/tests/unit/test_observability_logging.py`
  - Verify: uv run pytest tests/unit/test_observability_logging.py — test_redact_scrubs_api_key, test_redact_noop_when_key_unset, test_event_is_valid_json all pass.
- [ ] **3.** Set the correlation ContextVar in the request boundary: in _stream_chat (api/chat.py) set the session_id contextvar at the top, wrap the whole stream in the request-latency context manager, and emit nothing that leaks the key. Reset/restore the contextvar in a finally.
  - Files: `backend/app/api/chat.py`
  - Verify: Integration test asserts a request emits a request-level event carrying the session_id and a total_latency_ms field.
- [ ] **4.** Instrument the router: in _router_node (graph/hub.py) wrap the structured-output ainvoke in the llm_call context manager with role='router' and model=MODEL_CONFIG['router'], and call log_route(route, routing_confidence) after decide_route. Read session via contextvar (already set at boundary).
  - Files: `backend/app/graph/hub.py`
  - Verify: Integration test asserts captured logs contain a 'route' event with the committed route and an 'llm_call' event with role='router'.
- [ ] **5.** Instrument the coach and logger LLM call sites: wrap _answer_node's model.ainvoke (coach/graph.py) and the logger model calls (logger/graph.py:99, resolver.py:131) in the llm_call context manager with the matching role/model. Best-effort capture usage_metadata only if present.
  - Files: `backend/app/agents/coach/graph.py`, `backend/app/agents/logger/graph.py`, `backend/app/agents/logger/resolver.py`
  - Verify: Coach-route integration test shows an llm_call event role='coach'; existing coach/logger tests still pass (uv run pytest tests/graph tests/test_hub_logger_wiring.py).
- [ ] **6.** Instrument generator LLM + tool calls + retries: in _make_generate_node wrap each bound_model.ainvoke in llm_call(role='generator'); emit a tool_call event at each dispatch in the tool_calls loop (name=search_exercises/build_workout, outcome=ok|error derived from the result), redacting args summaries. In _make_gate_node emit a retry event when retry_count increments.
  - Files: `backend/app/agents/generator/graph.py`
  - Verify: Generator integration test asserts >=1 tool_call event with name and outcome; a forced-retry test asserts a retry event is emitted.
- [ ] **7.** Add the optional env-gated vendor tracer: an enable_vendor_tracer() helper called once at app startup (main.py create_app) that, only when LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) is present, lazily imports langsmith inside try/except ImportError and enables LangChain native tracing; otherwise no-ops. Never required to run.
  - Files: `backend/app/observability/tracer.py`, `backend/app/main.py`
  - Verify: test_vendor_tracer_noop_without_key asserts enable_vendor_tracer() returns False/None and does not raise when no key set; app import + full suite run with key absent.
- [ ] **8.** Write the critical-path integration test: drive a /chat request (via the fake_get_model seam) with OPENROUTER_API_KEY set to a sentinel, capture structured logs (caplog or a list handler), and assert the captured stream contains the route taken + at least one llm_call OR tool_call event with an outcome, AND the sentinel secret value never appears in any captured record.
  - Files: `backend/tests/integration/test_observability_request.py`
  - Verify: uv run pytest tests/integration/test_observability_request.py::test_request_log_reconstructable_and_redacted passes (this is the F-09 acceptance test).
- [ ] **9.** Run the full backend suite to confirm the schema-aware fake-model seam and all iteration-01/02 tests still pass with instrumentation in place.
  - Files: `backend/tests/conftest.py`
  - Verify: uv run pytest — full suite green; specifically tests/graph/test_hub_dispatch.py and test_router_node.py (the seam-sensitive router dispatch tests) pass unchanged.

### Test plan

| Test | Kind | Critical | Asserts |
|------|------|----------|---------|
| `test_request_log_reconstructable_and_redacted` | integration | ✅ **yes** | With OPENROUTER_API_KEY set to a sentinel and fake_get_model installed, a /chat (or direct hub.astream) request emits structured logs from which the route taken + at least one llm_call/tool_call event with an outcome can be reconstructed, and the sentinel secret never appears in any captured record. This is the spec's stated integration acceptance test. |
| `test_redact_scrubs_api_key` | unit | no | redact(s) replaces the configured OPENROUTER_API_KEY value with '***REDACTED***'; redact is a no-op when the env key is unset. |
| `test_event_is_valid_json` | unit | no | Each emitted log record is valid JSON containing at minimum event type and session_id (defaulting to 'unknown' when contextvar unset). |
| `test_llm_call_event_role_and_latency` | integration | no | Router/coach paths emit an llm_call event carrying role, model id, and a non-negative latency_ms. |
| `test_tool_call_event_name_and_outcome` | integration | no | A generator run emits >=1 tool_call event with name in {search_exercises,build_workout} and an outcome/error field. |
| `test_retry_event_emitted_on_gate_failure` | unit | no | When the gate increments retry_count, a retry event is emitted so retry count is reconstructable by counting events. |
| `test_vendor_tracer_noop_without_key` | unit | no | enable_vendor_tracer() does not raise and reports disabled when no LangSmith/LangChain key is present; no import error breaks app startup. |
| `test_router_dispatch_seam_unbroken` | integration | ✅ **yes** | Existing tests/graph/test_hub_dispatch.py and test_router_node.py still pass with instrumentation wired — the schema-aware fake-model seam is not broken. |
