# Build plan — 01-p0-core

**Status:** Approved · **Approved:** 2026-06-02 by Keith · **Iteration goal:** After this iteration, a user can hold a real branded chat conversation that correctly routes to all three working sub-agents (or asks a clarifying question), with resilient no-hallucination behavior and passing critical-path tests. · **Iteration slug:** `01-p0-core`

## How to use this

1. A human reviews this index + the per-feature "Build plan (approved)" sections in each spec and approves it in conversation. The assistant flips Status to "Approved" and commits — the human does NOT edit this file.
2. When the human is ready, they run the build workflow: it implements + commits the frozen contracts first, then builds each feature in its own worktree (independent features concurrently, hard-dependent ones after their deps), reviews each, opens ONE MR, and records each feature's outcome back into its spec. Every artifact is scoped to the iteration slug above, so this iteration can build concurrently with others.

## Blockers — RESOLVED (2026-06-02, by Keith)

All three pre-build decisions are made and recorded. No blocker stands; the build runs unattended.

| # | Blocker | Decision (locked) |
|---|---------|-------------------|
| B-1 | **ACCENT HEX UNCONFIRMED (F-01 brand tokens)** | **(b) Ship the ADR-013 default** — use the `#00C2A8`-family teal as the locked Tailwind `accent` token now; the eyedropper confirmation against live future.co is a **post-build human review step**, not a build gate. The build agent does NOT block on it: it ships the default and leaves the BRAND.md UNCONFIRMED note + eyedropper instruction in place for the later human pass. |
| B-2 | **LOGGER LLM-VERIFY DEFAULT (F-05)** | **(a) ON by default — hybrid.** RapidFuzz `WRatio` (cutoff 80) narrows candidates, then the LLM verifies the shortlist (`get_model('logger')`). Therefore the logger IS a structured-output/LLM role and `validate_model_config()` must treat `logger` as requiring a capable model. Deterministic tests stub the LLM-verify step via the `get_model` fake seam; an opt-out flag (`logger_llm_verify=False`) exists for pure-RapidFuzz runs but defaults ON. |
| B-3 | **OPENROUTER API KEY (F-01 live-model path)** | **Already satisfied** — the user has created a `.env` containing a valid `OPENROUTER_API_KEY` (present in the repo root before build). Live-or-recorded smoke tests (F-02 three canonical messages; optional F-04 generator smoke) RUN against the real model. The deterministic fake-model suite remains the load-bearing coverage; the live smokes are the thin confirmation layer per ADR-018. The build must read the key from `.env` (never hardcode), keep `.env` gitignored, and ship a `.env.example` placeholder (ADR-015). |

**Consequence of B-2 for the frozen contract:** the Model-config contract's `validate_model_config()`
now treats `logger` as a structured-output-requiring role (hybrid verify is on), alongside `router`
and `generator`. The build implements it accordingly.

## Frozen contracts (implemented first, before any feature work)

These contracts are implemented as a single commit before any feature worktree starts. All features build against the frozen signatures; no feature reshapes a contract.

| Contract | Source of truth | Frozen signature summary | Per-feature extensions | Exhaustive consumers |
|----------|----------------|--------------------------|------------------------|----------------------|
| **HTTP chat API (request/response envelope)** | `backend/app/api/schemas.py` + `backend/app/api/routes.py` + `frontend/src/types/api.ts`. ADR-001. | `ChatRequest{message, session_id?}`. `ChatResponse` frozen WIDE — all five fields nullable: `{route, reply_text, structured, explanation, clarification}`. `structured` is the discriminated-union serialization of `HubState.subgraph_result`. F-01 introduces all five fields; only `route`+`reply_text` populated until later features. TS mirror must declare all five from day one. | F-01: full wide envelope, all nullable. F-02: populates `route`+`clarification`. F-04: populates `structured=WorkoutPayload`+`explanation`. F-05: populates `structured=LogPayload`+`explanation`. | `routes.py` serializer; `response_assembly.py` (exhaustive switch over SubgraphResult variant); `frontend/src/types/api.ts`; frontend reducer + per-route render branches. |
| **SSE event envelope (discriminated union on `type`)** | `backend/app/api/streaming.py` + `frontend/src/types/api.ts`. ADR-002. | Six variants, frozen up front: `{type:'route',route}` \| `{type:'token',text}` \| `{type:'structured',payload}` \| `{type:'clarification',question,options}` \| `{type:'done'}` \| `{type:'error',message}`. Token events ONLY from message-mode deltas filtered by `langgraph_node`; route/structured/clarification read from committed graph state (never from message deltas). Error carries no stack trace/secret. Frontend SSE reducer switch and TS mirror exhaustive over all six from day one. No feature adds a seventh variant. | F-01: all six variants; emits route/token/done/error. F-02: wires clarification+route emission from state. F-03: coach tokens flow as existing token/done. F-04: emits structured=WorkoutPayload from state. F-05: emits structured=LogPayload from state. F-06: asserts error carries no traceback. | `streaming.py` SSE emitter; `frontend/src/types/api.ts` SSEEvent type; frontend SSE client reducer; frontend per-event render branches. |
| **Graph state schema (`HubState` + isolated subgraph states)** | `backend/app/graph/state.py` + per-subgraph `state.py` files. ADR-004 + ADR-003. | `HubState` TypedDict, all fields nullable from day one: `{session_id, messages, user_message, route, routing_confidence, routing_raw, subgraph_result, explanation, clarification, error}`. `SubgraphResult` = three-arm discriminated union frozen up front: `CoachResult{kind:'coach',answer}` \| `GeneratorResult{kind:'workout',workout,selected_exercise_ids}` \| `WorkoutLogResult{kind:'log',entries,session_id}`. `RecoveryInfo{message,recovered,retry_count}`. Per-subgraph isolated TypedDicts for Coach/Generator/Logger (no shared mutable key). Single-owner messages reducer; initial state ONLY on first invocation; in-memory checkpointer keyed per session. F-01 freezes ALL; later features only populate producers. | F-01: introduces full HubState, three-arm SubgraphResult, RecoveryInfo, all three subgraph TypedDicts. F-02: populates route/routing_confidence/routing_raw/clarification. F-03: coach adapter maps to CoachResult. F-04: generator adapter maps to GeneratorResult. F-05: logger adapter maps to WorkoutLogResult. F-06: asserts/populates retry_count + RecoveryInfo. | `response_assembly.py` (exhaustive SubgraphResult.kind switch); `routes.py` serializer; each boundary-adapter node; checkpointer config; router node. |
| **Route enum + `RoutingDecision`** | `backend/app/graph/routing.py`. ADR-005 + ADR-003. | `Route` closed enum `{COACH, WORKOUT_GENERATE, WORKOUT_LOG}`. `RoutingDecision{route,confidence,rationale,clarification?}`. `ClarificationPrompt{question,options}`. `CONFIDENCE_THRESHOLD=0.7` (single named constant). `decide_route(decision)` returns `(route,None)` when confidence≥0.7, else `(None,clarification)`. Hub conditional-edge map exhaustive over closed enum + clarify branch from day one. F-01 ships stub router returning fixed `RoutingDecision(route=COACH,confidence≥0.7)`. | F-01: introduces enum, RoutingDecision, ClarificationPrompt, threshold=0.7; stub router + exhaustive edge map. F-02: adds real structured-output router body + decide_route. F-06: constructs controlled RoutingDecision instances for tests. | `routing.py` decide_route; hub conditional-edge map; `response_assembly.py`; SSE route emitter; frontend route-render switch. |
| **Model config + capability registry (`get_model(role)`)** | `backend/app/models/registry.py` + `factory.py` + `config.py`. ADR-007 + ADR-018. | `Role=Literal['router','coach','generator','logger']`. `get_model(role)->BaseChatModel` via OpenRouter-compatible `ChatOpenAI` (NOT `init_chat_model`). Registry: `dict[model_id, ModelCapability{supports_structured_output,supports_tools,context_window,notes}]`. Config: `dict[Role,model_id]` with one shared capable default, each overridable. `validate_model_config()` fails fast at startup if any structured-output role maps to non-capable/unknown model. Test seam: `get_model` is the single injection point — fixture monkeypatches to return a deterministic multi-chunk `GenericFakeChatModel` stub with no network. No agent node constructs a model client directly. No feature adds a Role. | F-01: introduces Role, get_model, registry, validate_model_config, multi-chunk fake-model seam. F-02: router calls get_model('router').with_structured_output. F-03: coach calls get_model('coach'). F-04: generator uses get_model('generator').bind_tools. F-05: logger uses get_model('logger'). F-06: model-swap test changes config only. | validate_model_config; every agent node; test fixture; README eval section. |
| **`ExerciseRepository` interface + `Exercise` model** | `backend/app/data/repository.py` + `json_repository.py`. ADR-008 + ADR-009 + ADR-010. | `Exercise` (Pydantic v2, 14 fields load-as-is): `id,name,muscle_groups,joints_loaded,movement_patterns,equipment_required,is_bilateral,side,priority_tier,is_reps,is_duration,supports_weight,estimated_rep_duration,bilateral_pair_id`. `is_reps` and `is_duration` are independent booleans. `bilateral_pair_id` may be dangling (no integrity check). `ExerciseRepository(Protocol)`: `search(muscle_groups?,equipment?,movement_patterns?)->list[Exercise]`; `get_by_id(id)->Exercise|None`; `contraindicated_ids(injuries)->set[str]`; `bilateral_pair(id)->Exercise|None`; `all()->list[Exercise]`. `priority_tier` NEVER used for ranking. `JsonExerciseRepository` loads 50 typed models at startup. All dataset access goes through this interface. F-01 freezes full model + Protocol; F-04/F-05 only consume. | F-01: introduces Exercise (14 fields), 5-method Protocol, JsonExerciseRepository (50 models). F-04: consumes search + get_by_id in Generator tools + output-validation gate. F-05: consumes all() in Logger fuzzy-match resolver. | Generator tools; Logger fuzzy matcher; output-validation gate; JsonExerciseRepository; future GraphExerciseRepository (M2). |
| **`LogRepository` + `LogEntry` schema** | `backend/app/data/log_repository.py` + `sqlite_log_repository.py` + `postgres_log_repository.py`. ADR-011. | `LogEntry(BaseModel)`: `{session_id,exercise_id?,raw_name,sets?,reps?,weight?,unmatched,logged_at}`. `LogRepository(Protocol)`: `append(entries,session_id)->None`; `for_session(session_id)->list[LogEntry]`. Factory `get_log_repository()`: returns Postgres impl when `DATABASE_URL` set, else `SqliteLogRepository` at default path. One shared SQLAlchemy table with portable column types only. Introduced by F-05; additive only thereafter. | F-05: introduces LogEntry, LogRepository Protocol, factory, SQLite + Postgres impls. | Logger subgraph writer; get_log_repository factory; future 'show my log' read path; M3 history-edge ingester. |
| **`Reason` / explanation payload** | `backend/app/graph/explanation.py`. ADR-012. | `Reason(BaseModel)`: `claim: Literal['included','excluded','added','matched','substituted','note']`; `subject: str`; `relation: Literal['loads_joint','matches_target','bilateral_pair_of','equipment_match','name_match']`; `object?: str`; `detail?: str`. Carried as `HubState.explanation: list[Reason]` (default `[]`) and serialized onto `ChatResponse.explanation`. Both `claim` and `relation` vocabularies are CLOSED and frozen by F-01. Every M1 reason is an instance of frozen literals — no feature adds a member. Reasons are structured subject-relation-object triples, never free-text LLM rationalization. | F-01: introduces Reason model + closed claim set + closed 5-member relation vocab. F-03: emits claim='note' only. F-04: emits included/excluded/added instances (muscle_group/equipment/injury/bilateral reasons). F-05: emits matched/note instances. | `response_assembly.py`; `routes.py` serializer; frontend 'why these?' renderer. |
| **Brand & voice design tokens** | `frontend/tailwind.config.js` + `frontend/BRAND.md`. ADR-013. | Tailwind `theme.extend`: background #FFFFFF, surface #FAFAFA, text-primary #1A1A1A, text-secondary #6B7280, border #E5E7EB, accent = ONE token in #00C2A8-family (FLAGGED UNCONFIRMED — see Blocker B-1). Inter-style sans stack, headings 600-700, generous spacing/rounding. `BRAND.md`: voice do/don't (conversational, confident, partnership-oriented, results-focused; never clinical/robotic) + accent-hex UNCONFIRMED note + eyedropper-pass instruction. Policy: all UI consumes tokens only; structured content renders as branded cards, never raw JSON. F-01 freezes token set + BRAND.md. | F-01: introduces full token set + BRAND.md (accent flagged UNCONFIRMED). F-03: embeds BRAND.md voice directive into coach system prompt. F-04: workout card consumes card/spacing/accent tokens. F-05: log card consumes card/spacing tokens. F-06: empty/error/recovery states consume tokens + voice guidelines. | Every UI component; all assistant + clarification copy; `tailwind.config.js` (single token source). |
| **Generator tool input schemas (field-described Pydantic)** | `backend/app/agents/generator/tools.py` + WorkoutPayload models. PRD §7.1 / ADR-001 / ADR-008. | Two field-described Pydantic v2 input schemas (field descriptions MANDATORY per graded §7.1): `SearchExercisesInput{muscle_groups?,equipment?,movement_patterns?}` routes through `ExerciseRepository.search`. `BuildWorkoutInput{warmup_ids,main_ids,cooldown_ids,prescriptions[]}` returns `WorkoutPayload`. `WorkoutPayload={blocks: list[Block]}`; `Block={name: Literal['warmup','main','cooldown'], exercises: list[Prescription]}`; `Prescription={exercise_id,name,sets,reps?,duration_seconds?,rest_seconds,weight?}`. Bound via `get_model('generator').bind_tools`. Introduced by F-04. `WorkoutPayload` is the GeneratorResult arm of SubgraphResult and the structured payload for workouts. | F-04: introduces SearchExercisesInput, BuildWorkoutInput, WorkoutPayload/Block/Prescription; binds tools to generator model; output-validation gate checks every exercise_id. | Generator subgraph tool node; output-validation gate; boundary adapter; SSE structured emitter + ChatResponse serializer + frontend workout-card renderer. |

## Features & build order

| Feature | Spec | Build plan section | After |
|---------|------|--------------------|-------|
| F-01 | [01-walking-skeleton.md](01-walking-skeleton.md) | "Build plan (approved)" in spec | — (starts once contracts are frozen) |
| F-02 | [02-router-confidence-clarify.md](02-router-confidence-clarify.md) | "Build plan (approved)" in spec | F-01 |
| F-03 | [03-coach-subagent.md](03-coach-subagent.md) | "Build plan (approved)" in spec | F-01 |
| F-04 | [04-workout-generator.md](04-workout-generator.md) | "Build plan (approved)" in spec | F-01 |
| F-05 | [05-workout-logger.md](05-workout-logger.md) | "Build plan (approved)" in spec | F-01 |
| F-06 | [06-resilience-and-tests.md](06-resilience-and-tests.md) | "Build plan (approved)" in spec | F-02, F-04, F-05 |

F-02, F-03, F-04, F-05 are all independent of each other and can build concurrently once F-01 is merged. F-06 waits for F-02, F-04, and F-05.

```json
{
  "iterationName": "P0 Core",
  "iterationSlug": "01-p0-core",
  "buildBranch": "build/01-p0-core",
  "iterationGoal": "After this iteration, a user can hold a real branded chat conversation that correctly routes to all three working sub-agents (or asks a clarifying question), with resilient no-hallucination behavior and passing critical-path tests.",
  "blockers": [],
  "blockersResolved": [
    "B-1 ACCENT HEX: (b) ship ADR-013 default #00C2A8-family teal as the locked Tailwind accent token; eyedropper confirmation against future.co is a post-build human review step, NOT a build gate. Build does not block on it.",
    "B-2 LOGGER LLM-VERIFY: (a) ON by default — hybrid RapidFuzz WRatio(cutoff 80) narrows then LLM verifies the shortlist via get_model('logger'). Logger IS therefore a structured-output role: validate_model_config() must require a capable model for 'logger' too. Opt-out flag logger_llm_verify=False exists but defaults ON; deterministic tests stub the verify via the get_model fake seam.",
    "B-3 OPENROUTER API KEY: SATISFIED — user created a .env with a valid OPENROUTER_API_KEY in the repo root before build. Live smoke tests RUN against the real model; deterministic fake-model suite remains load-bearing. Build reads the key from .env (never hardcode), keeps .env gitignored, ships .env.example placeholder (ADR-015)."
  ],
  "frozenContracts": [
    {
      "name": "HTTP chat API (request/response envelope)",
      "sourceOfTruth": "backend/app/api/schemas.py (Pydantic v2) + backend/app/api/routes.py + frontend/src/types/api.ts (TS mirror). ADR-001.",
      "signature": "ChatRequest{message: str, session_id: str | None = None}. ChatResponse envelope frozen WIDE — every field present, all nullable: {route: Route | None, reply_text: str, structured: WorkoutPayload | LogPayload | None, explanation: list[Reason] (default []), clarification: ClarificationPrompt | None}. structured is the discriminated-union serialization of HubState.subgraph_result's producer arm (WorkoutPayload from GeneratorResult, LogPayload from WorkoutLogResult; CoachResult contributes reply_text only, structured stays None). This is the aggregated/non-streamed form (ADR-002 graceful-degradation); the SSE stream carries the same data field-for-field. F-01 produces only route + reply_text and freezes structured/explanation/clarification as nullable placeholders. The TS mirror in frontend/src/types/api.ts must declare all five fields from day one.",
      "extensions": [
        "F-01: introduces the full wide envelope (ChatRequest + ChatResponse) with all five fields nullable; only route + reply_text populated.",
        "F-02: populates route + clarification on the existing envelope via the router (no field added).",
        "F-04: populates structured = WorkoutPayload + explanation entries via the Generator (no field added; rides the structured union arm).",
        "F-05: populates structured = LogPayload + explanation entries via the Logger (no field added; rides the structured union arm)."
      ],
      "exhaustiveConsumers": [
        "backend/app/api/routes.py FastAPI serializer (assembles ChatResponse from HubState — must populate/serialize all five fields, structured switched on subgraph_result variant)",
        "backend/app/graph/response_assembly.py response-assembly node (maps HubState -> envelope fields; switch over subgraph_result union must be exhaustive: Coach/Generator/WorkoutLog arms)",
        "frontend/src/types/api.ts ChatResponse TS type (all five fields)",
        "frontend reducer + per-route render branches (coach text vs workout card vs log card vs clarification prompt — must handle route=null and structured=null)"
      ]
    },
    {
      "name": "SSE event envelope (discriminated union on type)",
      "sourceOfTruth": "backend/app/api/streaming.py (event types + emitter) + frontend/src/types/api.ts (TS mirror). ADR-002.",
      "signature": "Discriminated union on `type`, frozen with all SIX variants up front: {type:'route', route: Route} | {type:'token', text: str} | {type:'structured', payload: WorkoutPayload | LogPayload} | {type:'clarification', question: str, options: list[str]} | {type:'done'} | {type:'error', message: str}. FROZEN POLICY (ADR-002): token events come ONLY from messages-mode deltas filtered by metadata['langgraph_node'] == the active answer-producing node (coach node in M1); route/structured/clarification are read from committed graph state via stream_mode 'updates'/'values', NEVER from message deltas (avoids the documented tool-arg-corruption footgun). The 'error' event carries a human-meaningful message and NO stack trace / prompt / secret (ADR-006/014). F-01 emits route/token/done/error; the frontend SSE reducer switch and the TS mirror must be exhaustive over all six from day one. No feature adds a seventh variant.",
      "extensions": [
        "F-01: introduces all six variants; emits route/token/done/error.",
        "F-02: wires emission of {type:'route'} and {type:'clarification'} from committed graph state (no new variant).",
        "F-03: coach answer flows as existing {type:'token'} deltas then {type:'done'} (no new variant).",
        "F-04: emits existing {type:'structured', payload=WorkoutPayload} from graph state (no new variant).",
        "F-05: emits existing {type:'structured', payload=LogPayload} from graph state (no new variant).",
        "F-06: asserts {type:'error', message} carries no traceback when an exception escapes at /chat (no new variant)."
      ],
      "exhaustiveConsumers": [
        "backend/app/api/streaming.py SSE emitter (must be able to emit all six; sources structured/route/clarification from state not deltas)",
        "frontend/src/types/api.ts SSEEvent discriminated-union type (all six)",
        "frontend SSE client reducer (switch over type — exhaustive over all six)",
        "frontend per-event render branches (token append / route badge / structured card / clarification prompt / done / error)"
      ]
    },
    {
      "name": "Graph state schema (HubState + isolated subgraph states)",
      "sourceOfTruth": "backend/app/graph/state.py (HubState) + backend/app/agents/{coach,generator,logger}/state.py (per-subgraph TypedDicts). ADR-004 + ADR-003.",
      "signature": "HubState TypedDict, all fields present from day one (nullable where not yet produced): {session_id: str; messages: Annotated[list[BaseMessage], <single-owner reducer>]; user_message: str; route: Route | None; routing_confidence: float | None; routing_raw: dict | None; subgraph_result: SubgraphResult | None; explanation: list[Reason] (default []); clarification: ClarificationPrompt | None; error: RecoveryInfo | None}. SubgraphResult = discriminated union (tagged by `kind`) over THREE arms frozen up front: CoachResult{kind:'coach', answer: str} | GeneratorResult{kind:'workout', workout: WorkoutPayload, selected_exercise_ids: list[str]} | WorkoutLogResult{kind:'log', entries: list[LogEntry], session_id: str}. RecoveryInfo{message: str, recovered: bool, retry_count: int = 0} (nullable; ADR-006). Per-subgraph isolated states (each its own input/output TypedDict, NO shared mutable key across hub<->subgraph; crossed only via a boundary-adapter node): CoachState{in: user_message: str, messages: list[BaseMessage]; out: answer: str}. GeneratorState{in: user_message: str, injuries/targets context; out: workout: WorkoutPayload | None, selected_exercise_ids: list[str], retry_count: int = 0 (ceiling 2)}. LoggerState{in: user_message: str, messages: list[BaseMessage]; out: entries: list[LogEntry], retry_count: int = 0 (ceiling 2)}. FROZEN POLICIES: single-owner messages reducer (no parent/child reducer conflict); initial state passed ONLY on a thread's first invocation (no accumulator doubling); in-memory checkpointer keyed per session_id; store exercise IDs not full objects. F-01 freezes ALL of HubState including the three-arm SubgraphResult union and RecoveryInfo; later features only POPULATE producers — never reshape HubState, never add a HubState key.",
      "extensions": [
        "F-01: introduces full HubState, the three-arm SubgraphResult union (all arms declared), RecoveryInfo, and all three isolated subgraph TypedDicts.",
        "F-02: populates route/routing_confidence/routing_raw/clarification via the router node (no new field).",
        "F-03: coach node writes CoachState.answer; adapter maps it to subgraph_result=CoachResult + final assistant message (no new HubState key).",
        "F-04: Generator output adapter populates subgraph_result=GeneratorResult{workout, selected_exercise_ids} + explanation (no new HubState key).",
        "F-05: Logger output adapter populates subgraph_result=WorkoutLogResult{entries, session_id} + explanation (no new HubState key).",
        "F-06: asserts/populates GeneratorState.retry_count (ceiling 2) and HubState.error=RecoveryInfo on caught tool/validation errors (no new field; fields pre-frozen by F-01)."
      ],
      "exhaustiveConsumers": [
        "backend/app/graph/response_assembly.py response-assembly node (switch over SubgraphResult.kind — must handle coach/workout/log arms)",
        "backend/app/api/routes.py serializer (maps subgraph_result arm -> ChatResponse.structured)",
        "each subgraph boundary-adapter node (coach/generator/logger — the only hub<->subgraph crossing)",
        "the checkpointer config (session-keyed)",
        "the router node (writes route/routing_confidence/routing_raw/clarification)"
      ]
    },
    {
      "name": "Route enum + RoutingDecision",
      "sourceOfTruth": "backend/app/graph/routing.py (Route, RoutingDecision, ClarificationPrompt, CONFIDENCE_THRESHOLD, decide_route). ADR-005 + ADR-003.",
      "signature": "Route = closed enum {COACH, WORKOUT_GENERATE, WORKOUT_LOG}. RoutingDecision (Pydantic v2){route: Route, confidence: float, rationale: str, clarification: ClarificationPrompt | None = None}. ClarificationPrompt{question: str, options: list[str]}. CONFIDENCE_THRESHOLD: float = 0.7 (single named module constant; ADR-005 forbids scattered magic numbers). decide_route(decision: RoutingDecision | None) -> tuple[Route | None, ClarificationPrompt | None]: returns (route, None) when decision is present and confidence >= 0.7; (None, clarification) when confidence < 0.7 or structured output failed (decision is None). The hub conditional-edge map MUST be exhaustive over the closed Route enum PLUS the clarify branch from day one (ADR-003: exactly one subgraph per turn; non-COACH branches route to the response-assembly placeholder in F-01 so F-02/F-04/F-05 swap only node bodies). F-01 ships a stub router returning a fixed RoutingDecision(route=COACH, confidence>=0.7). Adding a Route member is a deliberate additive change requiring every consumer below to stay total — none is added by F-01..F-06.",
      "extensions": [
        "F-01: introduces Route closed enum, RoutingDecision, ClarificationPrompt, CONFIDENCE_THRESHOLD=0.7; stub router + exhaustive edge map incl. clarify branch.",
        "F-02: adds (additive) decide_route(decision) -> (Route|None, ClarificationPrompt|None) and the real structured-output router node body; reuses THRESHOLD constant; no Route member or RoutingDecision field added.",
        "F-06: constructs controlled RoutingDecision instances (incl. confidence<0.7) for the routing critical-path test; consumes the closed enum + threshold; adds no member."
      ],
      "exhaustiveConsumers": [
        "backend/app/graph/routing.py decide_route (must map every Route + the below-threshold/None case)",
        "the hub conditional-edge map in the hub StateGraph builder (one branch per Route + clarify branch)",
        "backend/app/graph/response_assembly.py response-assembly node (route-dependent assembly)",
        "the SSE {type:'route'} emitter",
        "frontend route-render switch in frontend/src/types/api.ts + render branches"
      ]
    },
    {
      "name": "Model config + capability registry (get_model(role))",
      "sourceOfTruth": "backend/app/models/registry.py (capability registry + validate_model_config) + backend/app/models/factory.py (get_model) + backend/app/models/config.py (role->model_id map, env keys). ADR-007 + ADR-018.",
      "signature": "Role = Literal['router','coach','generator','logger']. get_model(role: Role) -> BaseChatModel returning a langchain_openai.ChatOpenAI configured against OpenRouter's OpenAI-compatible base_url with the API key from env (NOT init_chat_model). Registry: dict[model_id, ModelCapability] where ModelCapability{supports_structured_output: bool, supports_tools: bool, context_window: int, notes: str}. Config: dict[Role, model_id] with one shared capable default model id, each role individually overridable. validate_model_config() runs at startup and FAILS FAST with a clear message if any structured-output role (router, generator; logger if LLM-extraction used) maps to a non-capable or unknown/unverified model. FROZEN TEST SEAM (ADR-018): get_model is the single injection point — a fixture monkeypatches the factory (or a registered override) to return a deterministic GenericFakeChatModel-based stub that emits MULTI-CHUNK token deltas and implements with_structured_output + bind_tools, with NO network. No agent node constructs a model client directly. No feature adds a Role; no feature adds a model-layer surface.",
      "extensions": [
        "F-01: introduces Role literal, get_model factory, ModelCapability registry, validate_model_config fail-fast, and the multi-chunk fake-model seam.",
        "F-02: router node calls get_model('router').with_structured_output(RoutingDecision, include_raw=True) (no surface added).",
        "F-03: coach node calls get_model('coach') (no surface added).",
        "F-04: generator binds tools via get_model('generator').bind_tools / with_structured_output (no surface added).",
        "F-05: logger uses get_model('logger') (no surface added).",
        "F-06: model-swap test changes config role->model_id default (config only, no code) and re-runs routing dispatch against the fake stub (exercises the seam only)."
      ],
      "exhaustiveConsumers": [
        "validate_model_config() (must validate every structured-output Role against the registry)",
        "every agent node that needs a model (router/coach/generator/logger nodes — all go through get_model, none construct a client)",
        "the test fixture that overrides get_model to inject the fake stub",
        "README eval/split-test section (documents the role->model map)"
      ]
    },
    {
      "name": "ExerciseRepository interface + Exercise model",
      "sourceOfTruth": "backend/app/data/repository.py (ExerciseRepository Protocol + Exercise Pydantic v2 model) + backend/app/data/json_repository.py (JsonExerciseRepository). ADR-008 + ADR-009 + ADR-010.",
      "signature": "Exercise (Pydantic v2) mirroring all 14 dataset fields load-as-is: id: str (UUID), name: str, muscle_groups: list[str], joints_loaded: list[str], movement_patterns: list[str], equipment_required: list[str], is_bilateral: bool, side: str | None, priority_tier: int, is_reps: bool, is_duration: bool (is_reps and is_duration are INDEPENDENT booleans — both may be true; confirmed in data), supports_weight: bool, estimated_rep_duration: float | None, bilateral_pair_id: str | None (may be a DANGLING ref — no cross-row integrity check). ExerciseRepository(Protocol): search(muscle_groups: list[str] | None = None, equipment: list[str] | None = None, movement_patterns: list[str] | None = None) -> list[Exercise] (NO priority_tier param — ADR-008: priority_tier is dead/all-2, never used for ranking/selection); get_by_id(id: str) -> Exercise | None; contraindicated_ids(injuries: list[str]) -> set[str] (ADR-009); bilateral_pair(id: str) -> Exercise | None (returns None for dangling refs); all() -> list[Exercise]. JsonExerciseRepository loads exactly 50 typed Exercise models from data/exercises.json at startup. POLICY: ALL dataset access goes through this interface — no agent/tool/gate reads exercises.json directly. F-01 freezes the full model + Protocol; F-04/F-05 only consume (no method added).",
      "extensions": [
        "F-01: introduces Exercise model (14 fields) + the 5-method ExerciseRepository Protocol + JsonExerciseRepository (50 models).",
        "F-04: consumes search() and get_by_id() in the Generator tools + output-validation gate (no method added; priority_tier unused).",
        "F-05: consumes all() (Exercise.id, Exercise.name) in the Logger fuzzy-match resolver; resolves to Exercise.id (no method added)."
      ],
      "exhaustiveConsumers": [
        "backend/app/agents/generator/tools.py search_exercises + build_workout tools",
        "backend/app/agents/logger fuzzy matcher (RapidFuzz WRatio over all() names, ADR-010)",
        "the output-validation gate (ADR-010 — verifies every referenced exercise_id exists via get_by_id/all)",
        "JsonExerciseRepository (the M1 impl) and any future GraphExerciseRepository (M2, identical signatures)"
      ]
    },
    {
      "name": "LogRepository + LogEntry schema",
      "sourceOfTruth": "backend/app/data/log_repository.py (LogRepository Protocol + LogEntry model + get_log_repository factory) + sqlite_log_repository.py + postgres_log_repository.py. ADR-011.",
      "signature": "LogEntry(BaseModel, Pydantic v2): session_id: str; exercise_id: str | None; raw_name: str; sets: int | None = None; reps: int | None = None; weight: float | None = None; unmatched: bool; logged_at: datetime. LogRepository(Protocol): append(self, entries: list[LogEntry], session_id: str) -> None; for_session(self, session_id: str) -> list[LogEntry]. Factory get_log_repository() -> LogRepository: returns the Postgres impl (postgres_log_repository.py) when os.environ.get('DATABASE_URL') is set, else SqliteLogRepository (sqlite_log_repository.py) at a default file path (clean-clone needs no service). ONE shared SQLAlchemy table, PORTABLE column types only (no Postgres-only features in M1). Selected by config (DATABASE_URL), never hardcoded. Introduced by F-05; FROZEN before any later (M3/M6) build — additive only thereafter.",
      "extensions": [
        "F-05: introduces LogEntry, LogRepository Protocol, get_log_repository factory, and both SQLite + Postgres impls behind the shared schema; the Logger subgraph is the writer."
      ],
      "exhaustiveConsumers": [
        "the Logger subgraph writer (calls append)",
        "get_log_repository factory (DATABASE_URL branch must return a same-schema impl)",
        "any future 'show my log' read path (for_session)",
        "M3 history-edge ingester (future consumer of the same schema)"
      ]
    },
    {
      "name": "Reason / explanation payload",
      "sourceOfTruth": "backend/app/graph/explanation.py (Reason model + closed relation vocabulary). Carried on HubState.explanation + the API/SSE response. ADR-012.",
      "signature": "Reason (Pydantic v2): claim: Literal['included','excluded','added','matched','substituted','note']; subject: str; relation: Literal['loads_joint','matches_target','bilateral_pair_of','equipment_match','name_match']; object: str | None = None; detail: str | None = None. Carried as HubState.explanation: list[Reason] (default []) and serialized onto ChatResponse.explanation. Both the `claim` set and the 5-member `relation` vocabulary are CLOSED and frozen by F-01 up front (ADR-012: controlled vocabulary; M5 extends deliberately later, NOT in M1). Every M1 reason is an INSTANCE of these frozen literals — no feature adds a claim or relation member. Explanations are structured subject-relation-object triples, never free-text LLM rationalization; emit only reasons for decisions actually taken.",
      "extensions": [
        "F-01: introduces Reason model + closed claim set + closed 5-member relation vocab; explanation is a wide nullable/[] field on HubState + ChatResponse (frozen WIDE).",
        "F-03: coach emits ONLY claim='note' reasons (and at most a note-permitted relation from the frozen vocab); no member added.",
        "F-04: Generator emits the first concrete instances — Reason(claim='included', relation='matches_target', object=<muscle_group>) and Reason(claim='included'|'note', relation='equipment_match', object=<equipment>); injury filter emits claim='excluded', relation='loads_joint'; bilateral pairing emits claim='added', relation='bilateral_pair_of'. All are instances of the frozen literals — NO new claim/relation/field.",
        "F-05: Logger emits claim='matched'/relation='name_match' for resolved entries and claim='note' for unmatched. Instances only — NO new member."
      ],
      "exhaustiveConsumers": [
        "backend/app/graph/response_assembly.py (appends/serializes explanation list)",
        "backend/app/api/routes.py serializer (ChatResponse.explanation)",
        "frontend 'why these?' renderer (iterates list, renders claim/subject/relation/object/detail — must handle every claim + relation literal)"
      ]
    },
    {
      "name": "Brand & voice design tokens",
      "sourceOfTruth": "frontend/tailwind.config.js (theme.extend tokens) + frontend/BRAND.md (voice do/don't). ADR-013.",
      "signature": "Tailwind theme.extend tokens: colors background #FFFFFF + surface/near-white #FAFAFA; text-primary #1A1A1A, text-secondary #6B7280; border #E5E7EB; accent = ONE named token in the #00C2A8 (teal/cyan-green) family, FLAGGED UNCONFIRMED (exact hex not exposed in site HTML — low confidence). Typography: Inter-style modern sans stack, headings weight 600-700, body 400, hero ~48-56px / section ~32-40px / body ~16-18px, generous line-height. Shape/spacing: rounded-rectangular buttons, solid accent fill, rounded-corner cards for structured content, generous spacing scale. BRAND.md: voice do/don't (conversational, confident, partnership-oriented, results-focused; never clinical/robotic) + the accent-hex UNCONFIRMED note + eyedropper-pass instruction. POLICY: all UI consumes tokens (no ad-hoc values); structured content renders as branded cards, never raw JSON. The eyedropper accent confirmation is a MANUAL human gate, NOT a build blocker. F-01 freezes the token set + BRAND.md; F-03/F-04/F-05/F-06 consume them.",
      "extensions": [
        "F-01: introduces the full token set in tailwind.config.js + BRAND.md (accent flagged UNCONFIRMED, eyedropper note).",
        "F-03: embeds BRAND.md voice directive into the coach system prompt (consume only; no token added).",
        "F-04: workout card consumes card/spacing/accent tokens (consume only).",
        "F-05: log card consumes card/spacing tokens (consume only).",
        "F-06: empty/error/recovery states consume tokens + voice guidelines (consume only)."
      ],
      "exhaustiveConsumers": [
        "every UI component (message bubbles, workout card, log card, clarification prompt, empty/error/recovery states)",
        "all assistant + clarification copy (follows BRAND.md voice)",
        "frontend/tailwind.config.js (single token source — no ad-hoc values anywhere)"
      ]
    },
    {
      "name": "Generator tool input schemas (field-described Pydantic)",
      "sourceOfTruth": "backend/app/agents/generator/tools.py + WorkoutPayload models. PRD §7.1 / ADR-001 (one validation lib) / ADR-008.",
      "signature": "Two field-described Pydantic v2 input schemas (field descriptions MANDATORY per graded §7.1): SearchExercisesInput{muscle_groups: list[str] | None = Field(None, description=...), equipment: list[str] | None = Field(None, description=...), movement_patterns: list[str] | None = Field(None, description=...)} -> returns list[Exercise] (routes through ExerciseRepository.search). BuildWorkoutInput{warmup_ids: list[str] = Field(description=...), main_ids: list[str] = Field(description=...), cooldown_ids: list[str] = Field(description=...), prescriptions: list[Prescription] (per-id sets/reps-or-duration/rest, field-described)} -> returns WorkoutPayload. WorkoutPayload = {blocks: list[Block]}; Block = {name: Literal['warmup','main','cooldown'], exercises: list[Prescription]}; Prescription = {exercise_id: str, name: str, sets: int, reps: int | None, duration_seconds: int | None, rest_seconds: int, weight: <as-stated str | None>}. Bound via get_model('generator').bind_tools / with_structured_output. Introduced by F-04. WorkoutPayload is the GeneratorResult arm of SubgraphResult and the {type:'structured'} / ChatResponse.structured payload for workouts.",
      "extensions": [
        "F-04: introduces SearchExercisesInput, BuildWorkoutInput, WorkoutPayload/Block/Prescription; binds tools to the generator model; output-validation gate checks every exercise_id via ExerciseRepository."
      ],
      "exhaustiveConsumers": [
        "the Generator subgraph tool node (bind_tools target)",
        "the output-validation gate (ADR-010 — validates Prescription.exercise_id exists)",
        "the boundary adapter mapping WorkoutPayload onto SubgraphResult=GeneratorResult",
        "the SSE {type:'structured'} emitter + ChatResponse.structured serializer + frontend workout-card renderer"
      ]
    }
  ],
  "features": [
    {
      "id": "F-01",
      "specPath": "docs/iterations/01-p0-core/01-walking-skeleton.md",
      "title": "Walking skeleton (branded chat ↔ SSE ↔ hub stub)",
      "after": []
    },
    {
      "id": "F-02",
      "specPath": "docs/iterations/01-p0-core/02-router-confidence-clarify.md",
      "title": "Router: structured output + confidence + clarify",
      "after": ["F-01"]
    },
    {
      "id": "F-03",
      "specPath": "docs/iterations/01-p0-core/03-coach-subagent.md",
      "title": "Coach sub-agent",
      "after": ["F-01"]
    },
    {
      "id": "F-04",
      "specPath": "docs/iterations/01-p0-core/04-workout-generator.md",
      "title": "Workout Generator sub-agent + output gate",
      "after": ["F-01"]
    },
    {
      "id": "F-05",
      "specPath": "docs/iterations/01-p0-core/05-workout-logger.md",
      "title": "Workout Logger sub-agent + persistence",
      "after": ["F-01"]
    },
    {
      "id": "F-06",
      "specPath": "docs/iterations/01-p0-core/06-resilience-and-tests.md",
      "title": "Resilience hardening + critical-path tests + demo/README",
      "after": ["F-02", "F-04", "F-05"]
    }
  ]
}
```
