# ADR-006: Resilience — error-feedback-in-state retry, bounded, no reliance on RetryPolicy

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The system must catch empty search results and invalid/malformed tool calls and respond meaningfully —
never crash, never hallucinate an exercise (PRD reqs 16–18, criteria 14–15). Research gives the
production-validated pattern and one critical footgun:

- **Error-feedback-in-state:** catch the tool error, append it as a `ToolMessage` with the validation
  text to state, loop back so the LLM self-corrects — documented to cut structured-output parse errors
  from 40% → 2%; track a retry count with a hard exit (TECHNOLOGY.md §recovery, refs [13][14][15]).
- **Footgun:** LangGraph `RetryPolicy()` **does not catch Pydantic `ValidationError`** — the node runs
  once and the retry is bypassed. Use explicit `try/except` in the node, not `RetryPolicy`
  (§footguns, refs [6][7]).

Serves: PRD reqs 16–18, criteria 14–15; behavioral success signals 3–4.

## Options considered

- **Rely on `RetryPolicy()` for tool/validation errors.** Directly defeated by the documented
  `ValidationError` bypass. Rejected.
- **Single-shot catch → generic apology.** Meets "don't crash" but wastes the self-correction the
  research shows is cheap and effective; weaker UX. Rejected as the primary path.
- **Error-feedback-in-state with bounded retries + graceful terminal fallback (chosen).**

## Decision

Tool-calling subgraphs (Generator, Logger) wrap tool execution in explicit `try/except`. On an
invalid tool call or validation error, the error text is appended to state as a `ToolMessage` and the
subgraph loops back to let the model self-correct, up to a **bounded retry count (max 2)** tracked in
state. On exhausting retries — or on empty/thin search results — the subgraph returns a **graceful
recovery**: acknowledge the gap, offer an honest alternative or a clarifying question, and name **no**
exercise outside the dataset. No unhandled exception or stack trace ever reaches the API/user.

## Rationale

This is the research's superior pattern and it satisfies both resilience criteria: invalid tool calls
self-correct or degrade gracefully (criterion 15), empty results recover without fabrication
(criterion 14). Bounding retries prevents the unbounded-loop failure mode. Using explicit try/except
rather than `RetryPolicy` sidesteps the documented `ValidationError` bypass — a footgun that would
otherwise make the retries silently not happen in exactly the validation-heavy code path we care about.

## Tradeoffs & risks

- **Retries add latency on the unhappy path.** Accepted: capped at 2; the happy path is unaffected,
  and the latency budget (ADR-012) is for the happy path.
- **A determined model could still emit nonsense after retries.** Mitigation: the terminal fallback
  is dataset-bounded by construction (it can only surface real exercises or admit it can't), so the
  no-hallucination invariant (req 18) holds even when self-correction fails. The output-validation
  gate (ADR-010) is the final backstop.

## Consequences for the build

- **Policy:** never use LangGraph `RetryPolicy` for tool/validation errors; use explicit try/except
  in the node with a state-tracked bounded retry counter (max 2).
- **Policy:** every tool-derived, user-facing response is dataset-bounded — a recovery path may say
  "I don't have that" but may never invent an exercise (enforced by ADR-010).
- **Policy:** the API layer catches any escaped exception and returns a structured error event
  (ADR-002 `error`), so no stack trace crosses the trust boundary (ADR-011).
