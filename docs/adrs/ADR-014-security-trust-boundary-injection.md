# ADR-014: Trust boundary & prompt-injection posture — defense-in-depth via output validation

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

M1 has no auth and no real user data (PRD out-of-scope #1), but it has a genuine trust boundary:
**untrusted free-text user input flows into LLM prompts and then into tool calls.** The two live risks
are (a) **prompt injection** — a message attempting to subvert routing or make an agent fabricate an
exercise or take an unintended action — and (b) ensuring no internal error/detail leaks across the
boundary. The system's defining safety invariant is already established: **no user-facing response may
reference an exercise outside the dataset** (req 18), enforced by the output-validation gate
(ADR-010).

Serves: PRD reqs 16–18 (resilience/safety), behavioral signals 3–4; sets up M5's safety-critical
contraindication (§10 M5).

## Options considered

- **Input sanitization / injection-pattern guardrail before the router.** Adds latency and complexity;
  injection-pattern matching is famously leaky (bypassable), and it duplicates protection the output
  gate already provides structurally. Rejected for M1.
- **Minimal — note injection, defer all handling.** Lightest, but doesn't articulate *why* the system
  is safe. Partially adopted (we do defer dedicated input filtering) but we make the structural
  argument explicit rather than hand-waving.
- **Defense-in-depth via structural invariants (chosen):** accept that user text must reach the LLM,
  and bound the *blast radius* with invariants that hold regardless of what the prompt says.

## Decision

M1 treats the LLM as **inside** the trust boundary for *phrasing* but **never** trusts it for *facts
or actions*. The structural defenses:

1. **Output-validation gate (ADR-010):** every exercise ID in any response is validated against the
   `ExerciseRepository`; an injection that coaxes the model to name a non-dataset exercise is caught
   and converted to a recovery response. A hallucinated/fabricated exercise cannot reach the user.
2. **Bounded tools:** the Generator's and Logger's tools operate *only* over the repository; there are
   no tools that execute arbitrary actions, shell, network, or filesystem writes outside the
   `LogRepository`. The action surface an injection can reach is small and safe-by-construction.
3. **Routing can't execute actions:** the router only *classifies* into a closed enum (ADR-005); a
   below-threshold or adversarial input routes to clarification, not to an arbitrary action.
4. **No internal leakage across the boundary (ADR-006/011):** the API catches any escaped exception
   and returns a structured error event — no stack traces, prompts, or secrets cross to the client.

Dedicated input-filtering/guardrails are **deferred** to when real user data and multi-tenancy arrive
(M6), where the risk profile changes.

## Rationale

For M1, structural invariants give *stronger, simpler* protection than leaky input filtering: the
worst an injection can achieve is a weird-sounding but dataset-bounded, action-free response — and the
output gate even prevents the fabricated-exercise outcome. This is the honest CTO answer ("we bounded
the blast radius rather than playing whack-a-mole with prompt patterns") and it scales: the same
hard-exclusion/output-gate discipline is exactly what M5's safety-critical contraindication needs.

## Tradeoffs & risks

- **An injection could still produce off-brand or off-topic *text*** (within the dataset bound).
  Accepted for M1 (no harm beyond a bad message); the Coach's system prompt sets guardrails on tone
  and scope. Revisit with real users (M6).
- **No rate limiting in M1** → a public demo could be abused for token spend. Mitigation: documented;
  a simple rate limit / deploy-behind-auth is the M6 hardening step; for grading the app runs locally.

## Consequences for the build

- **Policy:** safety is enforced by structural invariants (output gate + bounded tools + classify-only
  routing), not by input-pattern filtering. The output-validation gate is mandatory on every response.
- **Policy:** no tool may perform actions outside the repository / `LogRepository`; no arbitrary
  filesystem/network/shell access from agent tools.
- **Policy:** no internal detail (stack trace, raw prompt, secret) crosses the API boundary; errors
  are structured (ADR-002 `error` event).
- **Deferred (recorded):** input guardrails and rate limiting → M6, when real data/multi-tenancy
  exist.
