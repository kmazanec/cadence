# ADR-003: Hub supervisor StateGraph routing to one of three isolated subgraphs per turn

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The brief mandates a LangGraph `StateGraph` hub with typed state and explicit edges, with the three
sub-agents as **separate graphs composed into the hub (not inlined functions)** (PRD §7.1, reqs 1–5).
Research confirms the supervisor/hub pattern is the right shape at exactly three domains and that
several composition footguns must be designed around (TECHNOLOGY.md §supervisor, §footguns).

Serves: PRD reqs 1–5 (routing/hub), 6–15 (the three sub-agents), §7.1 (mandated architecture).

## Options considered

- **Swarm / direct hand-off loop.** ~47% fewer tokens and lower latency, but lower routing accuracy
  (91% vs 94%), no centralized audit trail, and it violates the brief's mandated hub. Rejected on the
  brief alone.
- **Inlined router functions (no subgraphs).** Simpler, but the brief explicitly forbids inlined
  sub-agents. Rejected.
- **Supervisor hub → exactly one of three compiled subgraphs per turn (chosen).** Matches the brief,
  gives explainable centralized control flow, and — by routing to exactly one subgraph per turn —
  avoids the `MULTIPLE_SUBGRAPHS` checkpoint-namespace collision that fan-out to the same subgraph
  triggers.

## Decision

A hub `StateGraph` whose router node classifies intent (ADR-005) and conditionally edges to **exactly
one** of three subgraphs — Coach, Generator, Logger — each compiled as its **own `StateGraph` with a
unique node name** in the hub. A low-confidence classification edges instead to a **clarification
node** that returns a clarifying question without dispatching (PRD reqs 3–4). After the chosen
subgraph (or clarification) runs, the hub edges to a terminal response-assembly node.

## Rationale

This is the brief's mandated shape, and the research's reasons for it hold here: routing accuracy and
a centralized audit trail matter more than the swarm's token savings for a graded, explainable
system. Routing to exactly one subgraph per turn is the documented way to avoid the
`MULTIPLE_SUBGRAPHS` error (each subgraph owns a stable, unique checkpoint namespace). Unique node
names per subgraph keep namespaces stable for checkpointing/memory (ADR-004).

## Tradeoffs & risks

- **One extra LLM routing call per turn** (~47% token overhead vs swarm, ~+1.4s latency per the
  benchmark). Accepted: routing correctness and explainability are the point; the latency budget
  (ADR-012) absorbs it.
- **Conditional-edge sprawl if routes multiply.** Mitigation: routes are a closed enum (ADR-005);
  adding one is a deliberate contract change, not an accident.
- **Subgraph interrupt/resume can loop if checkpointers are mis-passed** (footgun, ref [10]).
  Mitigation: ADR-004's checkpointer policy; M1 doesn't use interrupts.

## Consequences for the build

- **Policy:** the hub routes to **exactly one** subgraph per turn — never fan-out to the same
  subgraph concurrently.
- **Policy:** each subgraph is a separately compiled `StateGraph` with a unique hub node name; no
  sub-agent is an inlined function.
- **Policy:** edges are explicit and conditional on the router's typed decision; the route taken is
  recorded in state for testing/observability (PRD req 5, criteria 1–5).
