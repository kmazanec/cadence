# Feature: Resilience hardening + critical-path tests + demo/README

**ID:** F-06 · **Iteration:** 01-p0-core · **Status:** Not started

## What this delivers (before → after)
**Before:** The three agents work on the happy path; failures may crash or be ungraceful; no committed
tests/transcript/README.
**After:** Empty/thin searches and invalid tool calls recover gracefully (no crash, no hallucination);
the designated critical-path tests pass; a committed transcript + a README (with the "how I'd evaluate
in production" section) ship — the repo runs end-to-end from a clean clone.

## How it fits the roadmap
The closing feature of iteration 01 — it makes the must-ship milestone actually shippable and gradeable.
Hard-depends on the router + generator + logger being real.

## Requirements traced (from the PRD)
Reqs 16–18 (resilience), 5/24 (route observable, evaluation README); acceptance criteria 14–15
(recovery, invalid tool call), 18 (≥2 critical-path tests + rationale), 19 (clean-clone run +
transcript), 20 (evaluation README section), 21 (model-swap routing tests pass).

## Dependencies (must exist before this starts)
- **F-02 (router)** — HARD dep: tests the routing/clarify critical path; needs real classification.
- **F-04 (generator)** — HARD dep: hardens empty/thin/invalid-tool-call recovery and tests the output
  gate + injury-safety-adjacent paths.
- **F-05 (logger)** — HARD dep: tests resolve-or-flag.
(F-03 coach is exercised but not a hard dep — the critical tests target routing, generation-safety,
output-gate, and logger per ADR-018.)

## Unblocks (what waits on this)
- Nothing in iteration 01; it's the milestone closer. (Later iterations build on the merged P0 core.)

## Contracts touched
- Conforms to all iteration-01 contracts; introduces none. Exercises the error path of the SSE
  envelope (`error` event) and the resilience policy (ADR-006).

## Acceptance criteria (product behavior)
1. A generation request for equipment absent from the dataset (e.g. "only a sled") returns a graceful
   recovery (acknowledge gap / clarify), raises no unhandled exception, and names no non-dataset
   exercise.
2. A simulated invalid tool call (unknown exercise ID / schema-invalid args) is caught and answered
   meaningfully; no stack trace crosses the API boundary.
3. At least two automated critical-path tests pass from a clean clone, each with a written rationale
   (priority order per ADR-018: routing+clarify, injury/output-gate safety, no-hallucination+recovery,
   logger resolve-or-flag).
4. A committed transcript shows the three routes, the clarifying-question path, and a resilience
   recovery.
5. The README documents clean-clone setup and contains a "How I would evaluate this system in
   production" section (metrics, failure modes, correctness signals, model split-testing story).
6. Swapping the default model via config (no code change) keeps the routing tests passing.

## Testing requirements
- The designated critical-path tests (ADR-018) implemented and passing, each test file stating its
  rationale (graded). Bounded retries + error-feedback-in-state asserted. Empty/thin and invalid-tool
  recovery asserted without an unhandled exception.
- Tests run from a clean clone with the fake model (no network) for the deterministic suite.

## Manual setup required
- Record/curate the demo transcript (human-run interaction captured to a file).
- Author the README "how I'd evaluate" section (human-reviewed prose).

## Build plan (approved)

- [ ] **Contract reconciliation + boundary-level error catch (no stack trace crosses API)** delivers the /chat FastAPI boundary catches any exception escaping the graph and emits a structured SSE `error` event with a meaningful message and zero traceback text; a regression test proves no stack trace crosses the trust boundary. Also reconciles the actual built field names (HubState.error, GeneratorState.retry_count, recovery shape) from F-01/F-04/F-05 code before any further chunk, so later tests assert real contract shapes. Satisfies AC-2 (invalid/unknown handled; no stack trace crosses the API boundary). Tests: backend/tests/test_api_error_boundary.py (integration): force a node to raise inside the graph (via injected fake model that throws), drive a /chat request, assert the SSE stream terminates with `{type:'error', message:...}`, that message contains no 'Traceback'/'File \"'/exception class repr, and that the HTTP response does not 500 with a raw stack. Contract: SSE event envelope (ADR-002) — `error` event.

- [ ] **Generator empty/thin-search graceful recovery (no hallucination)** delivers a generation request for equipment/criteria absent from the dataset (e.g. 'only a sled') returns a graceful recovery — acknowledge the gap or clarify — raises no unhandled exception, and names no non-dataset exercise. Implemented as an explicit branch in the generator subgraph: when ExerciseRepository.search returns empty/thin, take the dataset-bounded recovery path instead of fabricating. Satisfies AC-1 (absent-equipment request -> graceful recovery, no unhandled exception, no non-dataset exercise). Tests: backend/tests/critical/test_recovery_no_hallucination.py (deterministic, no live LLM — this is ADR-018 critical path #3, rationale docstring at top): feed an empty/thin search through the generator subgraph (stub model scripted to request absent equipment), assert the returned assistant text references zero exercise IDs outside the repository, no exception propagates, and the `error`/recovery state is set with recovered=true. Contract: Resilience policy (ADR-006) — error-feedback-in-state + bounded retry.

- [ ] **Invalid tool call -> error-feedback-in-state + bounded retry (max 2), then graceful degrade** delivers a simulated invalid tool call (unknown exercise ID / schema-invalid args) is caught via explicit try/except (NOT RetryPolicy), the validation error is appended to state as a ToolMessage, the subgraph loops to self-correct up to a state-tracked ceiling of 2 retries, then degrades to a dataset-bounded graceful recovery. The output-validation gate catches a bogus exercise ID before it leaves the graph. Satisfies AC-2 (invalid tool call caught + answered meaningfully), AC-3 (critical-path #3: output-gate + recovery, with rationale). Tests: backend/tests/critical/test_recovery_no_hallucination.py (same critical file #3, additional cases): (a) stub model emits a tool call with a bogus/unknown exercise ID -> assert ToolMessage with validation text appended, retry_count increments, capped at 2, terminal graceful recovery emitted, gate rejects the bogus ID; (b) assert RetryPolicy is NOT used on the tool node (the node has explicit try/except so ValidationError is actually caught). Contract: Resilience policy (ADR-006) — error-feedback-in-state + bounded retry.

- [ ] **Critical-path #1: routing dispatch + low-confidence clarify (deterministic, stubbed router)** delivers the top-priority ADR-018 test: with a fake router model returning controlled RoutingDecisions, the hub dispatches to the matching subgraph at/above 0.7 and to the clarification node below 0.7 (naming >=2 interpretations) — never a silent below-threshold dispatch. Proves the system's spine deterministically, independent of LLM variance. Satisfies AC-3 (>=2 critical-path tests pass with rationale; routing+clarify is priority #1), AC-6 partial (provides the routing test the model-swap chunk reruns). Tests: backend/tests/critical/test_routing_clarify.py (deterministic, ADR-018 critical path #1, rationale docstring): inject fake router model -> COACH/WORKOUT_GENERATE/WORKOUT_LOG each dispatch to the right subgraph node; confidence=0.5 -> clarification node with a question + >=2 options; assert route is observable in HubState. Contract: Route enum + RoutingDecision (ADR-005).

- [ ] **Critical-path #2 (injury hard-exclusion) + #4 (logger resolve-or-flag), no LLM** delivers the remaining two ADR-018 designated paths so all four ship: #2 injury-aware hard exclusion (given a knee injury, contraindicated_ids + generator hard-exclusion produce a workout with zero knee-loading exercises) and #4 logger fuzzy-match (RapidFuzz WRatio cutoff 80 resolves 'bench press' -> real ID; an unmatchable name is flagged unmatched, never invented). Both deterministic by construction, no live LLM. (If injury hard-exclusion is an F-07/iteration-02 capability not present in iteration-01 code, this chunk asserts the F-04 output-gate + F-05 resolve-or-flag pair instead — reconciled in chunk 1; see risks.) Satisfies AC-3 (all four critical paths pass, each with recorded rationale). Tests: backend/tests/critical/test_logger_resolve_or_flag.py (ADR-018 #4, no LLM, rationale docstring): RapidFuzz WRatio cutoff 80, 'bench press' -> real dataset ID, 'zercher good-mornings' -> unmatched flag, persisted entry retrievable via LogRepository.for_session against SQLite. backend/tests/critical/test_injury_hard_exclusion.py (ADR-018 #2) ONLY if the iteration-01 generator exposes injury exclusion; otherwise this path's coverage folds into test_recovery_no_hallucination.py's output-gate assertions and the file is omitted (decision recorded in test docstring). Contract: Model config + capability registry / get_model(role) fake-model seam (ADR-007).

- [ ] **Model-swap config-only routing test (criterion 6)** delivers swapping the default model via config (no code change) keeps the routing tests passing — a parametrized/duplicated run of the routing-dispatch assertions under a swapped default model id, proving the get_model(role) abstraction and capability registry hold the swap. Satisfies AC-6 (config-only model swap keeps routing tests passing). Tests: backend/tests/critical/test_model_swap_routing.py (deterministic): set the config default model id to a second registry-capable id (env/config override, no code edit), inject the same fake router seam, assert the routing-dispatch + clarify behavior from chunk 4 still holds; assert startup validation still passes for the swapped capable model. Contract: Model config + capability registry / get_model(role) fake-model seam (ADR-007).

- [ ] **Clean-clone run, committed transcript, and evaluation README (milestone closer)** delivers the repo runs end-to-end from a clean clone with the fake model (no network) and the deterministic suite passes; a committed transcript shows the three routes + the clarifying-question path + a resilience recovery; the README documents clean-clone setup and contains the graded "How I would evaluate this system in production" section (metrics: routing accuracy + clarification rate + no-hallucination rate; failure modes; correctness signals; model split-testing story tied to ADR-007/req 24). Satisfies AC-4 (committed transcript: three routes + clarify + resilience recovery), AC-5 (README clean-clone setup + 'how I'd evaluate in production' section), AC-3 (tests pass from a clean clone). Tests: Verification (not a unit test file, but the gating proof): from a fresh `git clone`, run the documented setup command, then `pytest backend/tests/critical/` with the fake model (no OPENROUTER_API_KEY set) — the full critical suite goes green offline. The transcript file (docs/demo/transcript.md or transcripts/) and README sections are human-curated artifacts checked by reading; the clean-clone-offline pytest run is the automatable gate. The transcript-curation and README-prose are flagged manualSetup.

### Test strategy

Mix is dominated by deterministic unit/integration tests per ADR-018, with NO live LLM in the committed suite (the get_model(role) fake-model seam from F-01 makes the model injectable; safety/data invariants — hard exclusion, output gate, RapidFuzz match — are pure Python and need no model). Four designated critical-path test files live under backend/tests/critical/, each opening with a rationale docstring mirroring ADR-018 (the brief grades the *why*): #1 routing+clarify (stubbed router), #2 injury hard-exclusion (no LLM, conditional on iteration-01 code exposing it), #3 no-hallucination output-gate + empty/thin + invalid-tool recovery (the resilience core), #4 logger resolve-or-flag (RapidFuzz, no LLM). One boundary test (test_api_error_boundary.py) proves no stack trace crosses the SSE/API trust boundary. One model-swap test (test_model_swap_routing.py) proves criterion 6. The architecture-named risks the tests must pin: (a) bounded-retry ceiling actually enforced and RetryPolicy NOT relied on (so Pydantic ValidationError is genuinely caught) — asserted by counting ToolMessage appends and confirming the cap at 2; (b) recovery never names a non-dataset exercise — asserted by cross-checking every emitted exercise ID against ExerciseRepository; (c) the no-message-stream-corruption policy — structured/tool content read from state (already covered by F-01/F-04 emitter tests, not re-done here). All critical tests MUST run offline from a clean clone (no OPENROUTER_API_KEY) — that clean-clone-offline pytest run is the milestone's automatable gate. A minimal live-or-recorded smoke for the three canonical routing messages is optional and explicitly cut-able under time pressure (kept out of the deterministic suite so CI stays network-free). No on-device/deployed-URL tests required for F-06.

### Contract touchpoints

| Contract | Action | Frozen signature |
|----------|--------|------------------|
| Resilience policy (ADR-006) — error-feedback-in-state + bounded retry | consumes | GeneratorState gains (or already has, from F-01/F-04) a state-tracked retry counter and an `error` recovery field: `retry_count: int` (default 0, hard ceiling 2) and the HubState `error: RecoveryInfo \| None` field already enumerated in ADR-004 state.py. F-06 does NOT add new fields if F-01/F-04 already froze them; it only asserts/populates them. Frozen additive shape it depends on: `error` on HubState is `{message: str, recovered: bool}`-shaped (nullable), and the generator's tool node appends `ToolMessage(content=<validation error text>, tool_call_id=...)` to state.messages on a caught invalid tool call, looping until retry_count == 2 then emitting a dataset-bounded graceful-recovery assistant message. No new contract field is introduced by F-06. |
| SSE event envelope (ADR-002) — `error` event | consumes | Backend SSE emitter in backend/app/api/streaming.py emits `{type: 'error', message: str}` (the shape ALREADY frozen by F-01) when an exception escapes the graph at the /chat boundary. F-06 freezes that this terminal event carries a human-meaningful message and NO stack trace/traceback string. Frontend mirror frontend/src/types/api.ts already has this variant; F-06 adds no new event type. |
| Model config + capability registry / get_model(role) fake-model seam (ADR-007) | consumes | Tests inject a fake model via the existing get_model(role) injection seam frozen by F-01 — `get_model(role: Role)` resolved through a test override (e.g. a fixture that monkeypatches the factory or a registered fake returning a scripted ChatModel). The model-swap test consumes the config role->model_id map: swapping the default model id in config (no code change) and re-running the routing dispatch test (with stub) must stay green. No additive signature; F-06 only exercises the seam. |
| Route enum + RoutingDecision (ADR-005) | consumes | Routing critical-path test constructs controlled `RoutingDecision = {route: Route, confidence: float, rationale: str, clarification: ClarificationPrompt \| None}` instances (incl. confidence < 0.7) and asserts the hub dispatches to the matching subgraph at/above 0.7 and to the clarification node below it. Consumes the closed `Route = COACH \| WORKOUT_GENERATE \| WORKOUT_LOG` enum and `ClarificationPrompt = {question: str, options: list[str]}`. No new members. |

### Manual setup

- Record/curate the demo transcript: a human runs an end-to-end interaction (three routes + the clarifying-question path + a resilience recovery) and captures it to a committed file (docs/demo/transcript.md or transcripts/).
- Author and human-review the README "How I would evaluate this system in production" prose: metrics (routing accuracy, clarification rate, no-hallucination rate), failure modes, correctness signals, and the model split-testing story tied to ADR-007/req 24.
- Confirm a second registry-capable model id exists in the capability registry for the model-swap routing test to swap to (config-only); if only one is registered, add a deliberate registry entry.

### Risks

- **Contract drift between this plan's assumed field names and what F-02/F-04/F-05 actually froze.** F-06 introduces no contracts but its tests assert on HubState.error, GeneratorState.retry_count, the recovery/ToolMessage shape, ClarificationPrompt {question, options}, and the SSE `error` event. The build code did not exist when this plan was drafted (repo is docs-only). MITIGATION: chunk 1 front-loads a read of the actual built code and reconciles real names before any test is written; if a field differs, the test asserts the real shape — F-06 adds no new field.

- **Injury hard-exclusion (ADR-018 critical path #2) may not be present in iteration-01 code.** ADR-009/injury avoidance is iteration-02 (F-07) per ROADMAP; iteration-01 F-04 is the output gate, not injury filtering. F-06's spec dependency note even says F-03 coach is exercised but the critical tests target routing/generation-safety/output-gate/logger — it does NOT list injury. AMBIGUITY: ADR-018 lists injury as path #2 but it may be an iteration-02 capability. MITIGATION: chunk 5 makes test_injury_hard_exclusion.py CONDITIONAL — only written if the iteration-01 generator exposes contraindicated_ids/hard-exclusion; otherwise the #2 slot's intent (safety-critical determinism) is satisfied by the output-gate assertions in #3, and the omission/substitution is recorded in the test docstring. The brief requires >=2 critical tests; paths #1, #3, #4 alone exceed that, so the milestone is safe regardless.

- **AC-4 (transcript) and AC-5 (README evaluation prose) are human-curated and not machine-verifiable — they are graded subjectively.** UNTESTABLE by automation. MITIGATION: flagged as manualSetup; the automatable proxy is the clean-clone offline pytest run and a read-check that the transcript shows all three routes + clarify + a recovery, and that the README has the named section with the four required sub-points (metrics, failure modes, correctness signals, split-testing story).

- **'Empty/thin' search threshold is undefined — what counts as 'thin'?** The spec says empty OR thin triggers recovery but never defines thin. MITIGATION: treat thin as a named constant (e.g. fewer than the minimum needed to fill warmup/main/cooldown) decided against the actual build's build_workout requirements, asserted in test #3; keep it a single tunable constant, no config knob (simplicity — the spec doesn't ask for one).

- **RetryPolicy footgun is silent:** if the builder of F-04 used LangGraph RetryPolicy on the tool node, retries would silently NOT happen on Pydantic ValidationError, and a naive test could still pass on a single-shot apology. MITIGATION: chunk 3's test asserts the retry path positively — it counts ToolMessage appends and confirms self-correction actually loops before the cap, which fails if RetryPolicy swallowed the ValidationError. This catches the regression structurally rather than trusting the node's construction.

- **Scope creep risk:** the "how I'd evaluate" section invites building the model-eval harness (F-10, iteration-04 stretch) now. The spec only requires PROSE plus a config-only model-swap routing test. MITIGATION: chunk 6 ships prose only; chunk 7's model-swap test is the minimal runnable evidence — the runnable eval harness stays cut to iteration 04, no harness framework built here.

## Implementation notes (filled in by the building agent)
