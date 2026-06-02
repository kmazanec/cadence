# ADR-015: Secrets env-only & server-side; M1 is deliberately unauthenticated (auth lands in M6)

**Status:** Accepted · **Date:** 2026-06-02 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

M1 needs an OpenRouter API key (and optional `DATABASE_URL`) and must keep them out of git, logs, and
the frontend bundle. It also has no users and no real data (PRD out-of-scope #1), so authentication is
not required — but the *absence* of auth should be a recorded decision, not silence, and the boundary
where auth *does* enter (M6, when coach/member personas and real data arrive) should be named.

Serves: PRD §7.3 (credentials via env/config, documented), out-of-scope #1 (no auth in M1); §10 M6.

## Options considered

**Secrets:**
- **Secrets-manager abstraction now.** Forward-looking for M6 but gold-plating for M1; the env seam is
  already swappable. Rejected for M1.
- **Env-only, server-side, documented (chosen).**

**Auth:**
- **Static shared-secret/API token in M1.** Slight hardening for a public demo, but adds clean-clone
  friction and isn't needed (no sensitive data). Premature. Rejected.
- **Explicit no-auth deferral (chosen).**

## Decision

**Secrets:** the OpenRouter API key and all secrets are read from **environment variables, loaded
server-side only**. A committed `.env.example` documents required vars; `.env` is gitignored. The key
**never** reaches the React bundle (the frontend calls the backend, never OpenRouter directly) and is
never logged (the observability layer redacts secrets — ADR-017).

**Auth:** M1 is **deliberately unauthenticated** — a single-user local/demo experience over synthetic
data. Authentication and authorization (member/coach identity, per-member data isolation) enter in
**M6** when real personas and member data arrive; that is the correct trust-boundary moment, not M1.

## Rationale

Env-only server-side secret handling is the standard a CTO expects and the minimum that keeps keys out
of git/bundle/logs; the frontend-never-calls-the-LLM-directly rule is what guarantees the key can't
leak client-side. Deferring auth is correct *because there is nothing to protect yet* — adding a token
now would tax the clean-clone run (criterion 19) for no security gain. Recording the deferral (and its
M6 trigger) turns an omission into a defensible decision and shows the trust boundary was reasoned
about, not forgotten.

## Tradeoffs & risks

- **A publicly-deployed M1 demo is open** (anyone can spend tokens). Mitigation: documented; the demo
  is intended to run locally for grading; a deploy would add a rate limit / basic gate (M6 hardening,
  cross-ref ADR-014).
- **Env vars can still be mishandled** (e.g. echoed in a debug log). Mitigation: ADR-017 secret
  redaction in logs; `.env` gitignored; `.env.example` carries placeholders only.

## Consequences for the build

- **Policy:** all secrets via env, server-side only; `.env.example` committed, `.env` gitignored; the
  frontend never holds or calls with the OpenRouter key.
- **Policy:** M1 ships no auth; the API is open locally. Do not add user accounts or tokens in M1.
- **Deferred (recorded):** authn/authz + per-member data isolation → M6.
