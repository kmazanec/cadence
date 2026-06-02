# ADR-004: Typed state contract — isolated subgraph schemas, boundary adapters, session-keyed messages

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The graph's state schema is the single most-shared shape in the system: every node reads/writes it,
and it's directly graded ("typed state"). Research documents two silent-corruption footguns that make
state-sharing dangerous: (1) parent and child defining **different reducers for the same key**
silently corrupts state on write-back; missing keys in a subgraph's `input_schema` are **silently
dropped**; and (2) `Annotated[list, add]` accumulator fields **double on re-invocation** if initial
state is re-passed on resume (TECHNOLOGY.md §footguns, refs [3][9][11]). The PRD makes multi-turn
memory **P2 / cut-able** but explicitly wants the state shape *not* to change when memory is toggled
(PRD §8.2, req 25).

Serves: PRD reqs 1–5, 25 (memory), §7.1 (typed state), §8.2.

## Options considered

**Hub↔subgraph state sharing:**
- **One shared state schema across all graphs.** Less wiring, but walks straight into the
  reducer-conflict and accumulator-doubling footguns in the graded code. Rejected.
- **Isolated subgraph state + explicit boundary adapters (chosen).** Each subgraph declares its own
  typed input/output schema; the hub wraps each subgraph in a node that maps hub-state → subgraph
  input and subgraph output → hub-state explicitly.

**Memory shape:**
- **Stateless per-request, add memory in P2.** Simplest now, but changes the state contract when
  memory lands — the rework the PRD seam intent forbids. Rejected.
- **Messages list in state from day one, session-keyed (chosen).** State carries a typed messages
  list from the start; a per-session checkpointer thread persists it.

## Decision

- **Hub state** is a typed schema carrying: `session_id`, `messages` (the running conversation),
  `user_message` (current turn), `route` + `routing_confidence` + `routing_raw` (router output),
  `subgraph_result` (the active subgraph's typed output), `explanation` (ADR-008), `clarification`
  (question + options, nullable), and `error` (nullable recovery info).
- **Each subgraph** (Coach/Generator/Logger) declares its **own** input and output TypedDict. The hub
  composes each via a **boundary-adapter node** that explicitly translates in both directions. Parent
  and subgraphs never share a mutable key under different reducers.
- **Memory** lives as the session-keyed `messages` list with a per-session checkpointer thread. M1 P0
  uses it within a single turn; enabling P2 multi-turn is "keep prior turns in the thread" — no schema
  change. Initial state is passed **only on first invocation** of a thread (never re-passed on
  resume) to avoid accumulator doubling.

## Rationale

Isolated schemas + explicit adapters make the silent reducer/`input_schema` corruption *structurally
impossible* (there are no shared mutable keys to mis-reduce), and they give each subgraph a clean,
unit-testable contract — which is also the seam M6 re-implements against the graph platform. Putting
`messages` in state from day one means the P2 memory decision is a behavior toggle, not a contract
migration, honoring the PRD's "memory is the seam, not a prerequisite" intent. The first-invocation
rule directly neutralizes the documented doubling bug.

## Tradeoffs & risks

- **More wiring (adapter nodes per subgraph).** Accepted: the wiring is small, explicit, and the
  thing that buys footgun-immunity and testability.
- **Checkpointer persistence adds write latency.** Mitigation: store IDs/findings in state, not raw
  documents (research rule: lean state < 10KB → <15ms SQLite checkpoint writes); the Generator stores
  selected exercise **IDs**, not full exercise objects.
- **Accumulator-doubling footgun is low-confidence/version-dependent.** Mitigation: the
  first-invocation-only rule is cheap insurance regardless; a memory test asserts no turn duplication.

## Consequences for the build

- **Contract (graph state schema).** The most-shared shape in the system.
  - **Source of truth:** `backend/app/graph/state.py` (hub `HubState`) + each subgraph's
    `state.py` (`CoachState`, `GeneratorState`, `LoggerState`).
  - **Shape (initial):** as enumerated under Decision; `route` is the closed enum from ADR-005;
    `messages` uses an explicit, single-owner reducer; `subgraph_result` is a discriminated union over
    the three subgraph output types.
  - **Exhaustive consumers:** the router node, each subgraph boundary-adapter, the response-assembly
    node, the checkpointer config, and the API serializer (ADR-001). Any new state field must be
    threaded through the adapters, not silently shared.
- **Policy:** no shared mutable state key across hub/subgraph boundaries; cross only through adapters.
- **Policy:** pass initial state only on a thread's first invocation; store IDs not documents in state.
