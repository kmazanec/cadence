# ADR-001: Split topology — FastAPI backend + separate React/Vite/Tailwind frontend

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The brief fixes the backend language: Python + LangGraph + LangChain (PRD §7.1). The PRD also makes
a **premium, branded, Future-aesthetic web chat UI a P0, non-negotiable deliverable** (PRD §4 P0.7,
req 19–21, criterion 17). Python's native UI story is weak; a truly premium branded chat UI is best
built with a modern JS/TS frontend. So the two halves — a Python agent backend and a polished web UI
— must relate somehow. This decision also sets up M6, where Cadence grows a **coach-facing typed REST
API and dashboard** (PRD §10 M6); the M1 topology should make that a clean extension, not a rewrite.

Serves: PRD reqs 19–21 (web chat UI), §7.7 forward-compat (M6 API platform), §10 M6.

## Options considered

- **Python-served UI (FastAPI + server-rendered/HTMX or static).** One process, simplest run story
  (one command, no JS build). But hitting a genuinely premium Future-grade aesthetic in
  server-rendered Python is hard, and there's no real client/server API boundary for M6 to inherit.
- **Python API + minimal vanilla frontend.** A real HTTP API plus a hand-built single-page vanilla
  chat. No node toolchain, decent brand control. But more manual UI work (chat state, structured
  workout/log cards) and fewer component niceties.
- **Python API + separate React/Vite/Tailwind frontend (chosen).** FastAPI exposes the graph over
  HTTP; a separate React/Vite/Tailwind app is the branded chat UI. Two processes and dev
  orchestration (CORS, two ports), but the cleanest brand result and a typed API contract M6 extends
  directly.

## Decision

A split topology: a **FastAPI backend** exposes the assembled LangGraph hub over HTTP; a **separate
React + Vite + Tailwind frontend** delivers the premium branded chat UI. The two communicate over a
documented HTTP contract (chat request → streamed response; see ADR-002).

## Rationale

The UI is a P0 centerpiece graded on looking *bespoke, not default-chatbot* (criterion 17); React +
Tailwind give precise control over the brand tokens (ADR-014) that a templated Python UI can't match.
The split also creates a real **client/server boundary now**, so M6's coach-facing API is an
*extension of an existing contract* rather than a retrofit — directly serving the "one evolving
product" thesis (PRD §10). FastAPI is the idiomatic Python choice for a typed async HTTP surface and
pairs naturally with Pydantic, which the brief already mandates for tool schemas (§7.1) — so the API
request/response models and the tool schemas share one validation library.

## Tradeoffs & risks

- **Two processes to run and demo.** Mitigation: a documented `docker compose up` (or a single
  `make dev`) brings up both; the README's clean-clone path (criterion 19) covers it. This also
  pre-stages M6's Dockerized-stack requirement (PRD §10 M6).
- **CORS / dev-orchestration friction.** Mitigation: explicit CORS config for the dev origin; Vite
  dev-proxy to the API in development.
- **More surface than a 2–3h take-home strictly needs.** Accepted deliberately: the UI is P0 and the
  M6 graduation payoff is real. The backend remains runnable headless (CLI/tests) independent of the
  frontend, so core grading never depends on the UI building.

## Consequences for the build

- **Policy:** the backend is the source of truth for all agent behavior; the frontend is a thin
  presentation client and must contain **no agent logic, no exercise-data access, and no routing** —
  it only renders what the API returns. This keeps the M6 API boundary honest.
- **Policy:** the backend must be runnable and testable headless (no frontend dependency) so the
  critical-path tests (PRD req/criteria 18) and CLI demo never require a JS build.
- **Contract (HTTP chat API).** This decision establishes the **client↔server wire contract**, a
  shared cross-cutting shape M6 extends.
  - **Source of truth:** `backend/app/api/schemas.py` (Pydantic request/response models) +
    `backend/app/api/routes.py` (the endpoint(s)). The frontend mirrors these as TypeScript types in
    `frontend/src/types/api.ts`.
  - **Shape (initial):** a chat endpoint accepting `{ message: str, session_id: str | null }` and
    producing an assistant turn carrying `{ route, reply_text, structured (workout | log | null),
    explanation, clarification (question + options | null) }` — the response envelope is defined
    concretely in ADR-002 (transport) and ADR-008 (explanation payload). M6 adds member-scoped
    variants (`member_id`, coach queries) to the same envelope family.
  - **Exhaustive consumers:** the FastAPI route handler (serializer), the frontend API client
    (deserializer/renderer), and the frontend's per-route render branches (coach text vs. workout
    card vs. log card vs. clarification prompt). All must stay in sync with the response envelope.
