# ADR-017: Observability — structured per-request logging now, optional vendor tracer (P2)

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no (P2 feature) · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

Observability is a P2 (cut-able) requirement: each LLM call and tool invocation should be traceable so
a request's route + tool calls + outcomes can be reconstructed (PRD req 26, criterion 23). It also
underpins the "how I'd evaluate in production" README story (req 24). It must not leak secrets
(ADR-015). Research notes structured logging / Langfuse / OpenTelemetry as the options.

Serves: PRD reqs 24, 26; criterion 23; §10 cross-cutting (platform-wide tracing in M6).

## Options considered

- **Full LangSmith/Langfuse tracing now as the primary path.** Richest traces, best "observability"
  demo, but adds a vendor dependency/account and spends the cut-able P2 budget on infra over core.
- **Minimal logging, defer real observability to M6.** Lightest, but weakens req 24's evaluation
  story. Rejected.
- **Structured logging now + optional env-gated vendor tracer (chosen).**

## Decision

Commit to **structured JSON logging** of every request: a correlation/`session_id`, the route taken,
each LLM call (role, model, latency, token usage if available), each tool invocation (name, args
summary, outcome/error), retry counts, and total latency — enough to **reconstruct any request**
(criterion 23). Secrets are **redacted** (ADR-015). A vendor tracer (LangSmith or Langfuse) is an
**optional, env-gated** add-on (e.g. enabled when its key is present) layered over the same
instrumentation points — not required to run. This is the M1 slice of the platform-wide tracing M6
extends to graph queries.

## Rationale

Structured logs satisfy the requirement and the evaluation story with **zero required dependency**,
keeping the cut-able P2 work cheap and the clean-clone run trivial. Making the vendor tracer optional
captures the "we can flip on rich tracing" capability for the README without taxing the default path.
Instrumenting at well-defined points (model factory, tool nodes, router) means the vendor tracer and
the structured logger share one set of hooks — and M6 reuses those same hooks for graph-query tracing.

## Tradeoffs & risks

- **Structured logs are less rich than full traces** (no flame graphs). Accepted for M1;
  reconstructable-per-request is the bar (criterion 23), and the vendor tracer is one env var away.
- **Token-usage data depends on provider/OpenRouter exposing it.** Mitigation: log what's available;
  don't fail if usage is absent.
- **P2 means it can be cut.** If cut, a minimal route+latency log line remains so the demo/transcript
  can still show the route taken (criterion 16 supports the demo regardless).

## Consequences for the build

- **Policy:** instrument at shared hooks (model factory `get_model`, tool nodes, router node);
  structured JSON logs reconstruct any request; secrets are redacted.
- **Policy:** vendor tracer is optional/env-gated, never required to run or test.
- **Build order:** P2 — built after P0+P1 are solid; if cut, retain a minimal route+latency log.
