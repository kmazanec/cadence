# Cadence — Product Requirements Document

> A multi-agent fitness coaching system. A hub agent classifies user intent with LLM
> structured output and routes each message to one of three specialized sub-agents — a
> knowledge **coach**, a **workout generator**, and a **workout logger** — surfaced through
> a branded, premium chat interface inspired by Future (future.co).
>
> **Context:** this is a graded take-home assessment (AI Engineering). The full brief lives at
> `../candidate-assessment/1-multi-agent/ASSESSMENT.md` (external source-of-truth, outside this
> repo root); the exercise dataset (50 entries) is vendored into the repo at `data/exercises.json`.
> This PRD owns WHAT/WHY only — stack and system design are decided in the architecture stage. The
> brief mandates Python + LangGraph + LangChain; that is a fixed constraint, not an architecture
> choice (see §7).
>
> **Cadence is one evolving product, planned in milestones.** What this PRD specs in full —
> §§1–8 — is **Milestone 1 (M1): the multi-agent chat coach**, the thing we build now. A second
> brief (`../candidate-assessment/2-knowledge-graph/KNOWLEDGE_GRAPH_ASSESSMENT.md`, external)
> describes the
> natural maturation of this same product into a **knowledge-graph coaching platform** — the same
> exercises, members, and injury logic, grown into a graph the system can reason and explain over,
> with a coach-facing surface alongside the member one. That is a **real future build**, captured
> here as **future milestones (§10)** so the architecture and roadmap make forward-compatible
> decisions now and we avoid rework — **but no future-milestone work is in M1's scope** (§4). The
> tiers in §4 (P0/P1/P2) describe M1 only.

---

## 1. Problem Statement

A fitness coaching product needs to respond to free-form user messages that mix three very
different intents — asking a fitness/training **question**, requesting a **generated workout**,
and **logging a completed workout** — without making the user choose a mode or learn a command
syntax. A single monolithic prompt handles this poorly: it conflates concerns, is hard to test,
and gives the user no graceful path when intent is genuinely ambiguous (e.g. "I did a workout
yesterday, can you adjust it?"). Cadence solves this by classifying intent up front with a
confidence-scored LLM router and dispatching to a purpose-built sub-agent for each route, so each
capability can be built, tested, and reasoned about in isolation — and so ambiguous input is met
with a clarifying question rather than a confident misroute. The experience is delivered through a
chat interface that feels like a premium Future coach, not a generic chatbot.

## 2. Users & Stakeholders

- **End user (primary): a person training.** Chats naturally to ask training questions, request
  workouts tailored to their time/equipment/target muscles (and, optionally, around an injury),
  and log what they actually did. They never see routes or agents — they see one coach that
  responds appropriately. They expect responses to be correct, to never invent exercises that
  don't exist, and to ask before guessing when their request is unclear.
- **Evaluator (stakeholder): the assessment grader.** Reads the public GitHub repo to judge
  architecture quality (typed graph, composed sub-graphs, structured-output routing, Pydantic
  tool schemas), resilience, test choices and rationale, the demo, and the "How I'd evaluate this
  in production" README section. This stakeholder's needs are encoded directly as P0 requirements.
- **Author/operator (stakeholder): the engineer running and demoing Cadence.** Needs the system
  to run from a clean clone with documented setup, to be model-swappable for evaluation, and to
  surface what each agent and tool did (observability) when debugging or demoing.
- **Coach (future primary user, M2+): a certified trainer managing members.** *Not served in M1.*
  In later milestones the coach asks Cadence about a specific member — "build her a lower-body
  session this week", "why did you skip barbell squats for her?", "what should I watch for?" — and
  expects answers traceable to the member's actual context (injuries, goals, history). Cadence's
  long-term vision serves **both** the member (M1) and the coach (M2+), mirroring Future's real
  human-coach-plus-app model. The coach persona is recorded here so M1's seams (data access,
  injury reasoning, explainability) are shaped to graduate into the coach-facing graph platform
  without rework. See §10.

## 3. Desired Outcome

Success means: a user can hold a natural chat conversation in a branded Future-style interface;
every message is routed to the correct capability (or met with a clarifying question when intent
is genuinely ambiguous); generated workouts are well-structured and reference only real exercises
from the dataset; logged workouts are parsed into structured entries that resolve to real
exercises (or are explicitly flagged as unmatched, never silently invented); and the system
degrades gracefully — never crashing and never hallucinating — when a request can't be satisfied
(e.g. equipment not in the dataset) or when the model emits a malformed tool call. The repository
a grader clones runs end-to-end, contains the mandated architecture, passes its critical-path
tests, and explains how the system would be evaluated in production.

**Behavioral success signals:**
1. A clear-intent message reaches the right sub-agent and produces a correct, in-character response.
2. A genuinely ambiguous message produces a clarifying question, not a guess.
3. A request that the dataset can't satisfy produces an honest, helpful recovery — no invented exercises.
4. A malformed tool call is caught and answered meaningfully — no stack trace reaches the user.
5. The chat UI reads as a premium Future coach experience, not a default chatbot.

## 4. Scope

Requirements are tiered to give the build an explicit, honest cut-order if the 2–3 hour window
runs short. **P0 = must ship** (every graded requirement + the branded UI, declared non-negotiable
by the user). **P1 = cheap, dataset-justified differentiators.** **P2 = build only if P0+P1 are
solid.** Lower tiers are cut from the bottom up; nothing in P0 is sacrificed for a lower tier.

### In Scope

**P0 — Core (must ship):**
1. A hub that classifies each user message into one of three routes — `COACH`, `WORKOUT_GENERATE`,
   `WORKOUT_LOG` — using **LLM structured output**, with a **confidence score** and an explicit
   low-confidence path.
2. Low-confidence handling: when router confidence is below a defined threshold, the hub responds
   with a **clarifying question** rather than dispatching to a sub-agent.
3. A **Coach** sub-agent that answers fitness/training knowledge questions conversationally.
4. A **Workout Generator** sub-agent (tool-calling) that searches the dataset and assembles a
   structured workout with **warmup / main / cooldown** blocks, each exercise carrying sets, reps
   (or duration), and rest, and referencing a real exercise from the dataset.
5. A **Workout Logger** sub-agent that extracts structured log entries (exercise, sets, reps,
   weight) from natural language and resolves each to a real dataset exercise via fuzzy matching —
   or explicitly flags it as unmatched.
6. **Resilience:** empty search results and malformed/invalid tool calls are caught and answered
   meaningfully; the system never crashes and never invents exercises absent from the dataset.
7. A **branded chat UI** that lets a user converse with Cadence end-to-end and reflects Future's
   premium, minimal, human-centered aesthetic and conversational-motivational coach voice.
8. **At least two automated critical-path tests**, each with a written rationale for why it was chosen.
9. A **README** covering setup/run instructions and a **"How I would evaluate this system in
   production"** section (metrics, failure modes to monitor, signals of correct operation), which
   explicitly includes the **model split-testing / eval** story enabled by the model abstraction.
10. A **runnable demo** (the chat UI) plus a committed **transcript** showing the three routes,
    the clarifying-question path, and a resilience recovery.
11. A **model abstraction** so the underlying LLM is swappable for evaluation, with one sensible
    default, exposing which configured models are structured-output / tool-calling capable.

**P1 — Signature differentiators (cheap, dataset-backed):**
12. **Injury avoidance:** the generator accepts an injured-joint constraint (e.g. "avoid loading my
    knee") and excludes exercises whose loaded joints include it.
13. **Bilateral pairing:** when the generator selects a single-side exercise, it auto-includes the
    paired opposite-side exercise so both sides are trained.

**P2 — Build only if P0+P1 are solid:**
14. **Multi-turn conversation memory:** the system remembers earlier turns within a session, so
    follow-ups like "adjust it" or "I did a workout yesterday, can you adjust it?" resolve against
    prior context, and a clarifying question can be resolved by the user's next message without
    re-stating.
15. **Observability:** each LLM call and tool invocation is traced (structured logging or a tracing
    integration), supporting debugging, the demo, and the production-evaluation story.

### Out of Scope

1. User accounts, authentication, or multi-user separation.
2. Nutrition, diet, or meal planning.
3. Real human coaches, scheduling, messaging with a person, or any Future production feature beyond
   the chat-coach *aesthetic and voice*.
4. Mobile-native apps; the demo is a web (browser) experience.
5. Exercise data beyond the provided 50-entry dataset; no external exercise APIs.
6. Progression/periodization across sessions, analytics dashboards, or charts over logged history.
7. Payment, onboarding, or any Future-style pricing/signup flow.

### Deferred

1. **Cross-session persistence of users and history** — P0 logging persists entries to a local
   store for the current demo, but durable, multi-session user history is deferred (no real users
   in scope).
2. **Streaming responses** (a brief stretch goal) — deferred; the UI may render complete responses.
   Rationale: lower correctness signal than the chosen stretches for the time budget.
3. **A formal automated eval/split-test harness** — deferred to a description in the README's
   evaluation section; the model abstraction makes it *possible* but building the harness is out of
   the time budget. Rationale: the brief asks how we'd evaluate, not for a running eval suite.

## 5. Requirements

Behavior- and outcome-focused. Technology-agnostic except where the brief fixes a constraint
(noted in §7). Each is independently verifiable.

**Routing (hub):**

1. The hub shall accept a free-form user message and classify it into exactly one of `COACH`,
   `WORKOUT_GENERATE`, `WORKOUT_LOG`, producing a structured classification that includes the
   chosen route and a numeric confidence value.
2. The classification shall be produced via the model's structured-output capability — never via
   regular expressions, keyword matching, or hand-written string rules.
3. When the classification confidence is at or above a defined threshold, the hub shall dispatch the
   message to the corresponding sub-agent.
4. When the classification confidence is below the threshold, the hub shall not dispatch to a
   sub-agent; it shall instead return a clarifying question that names the plausible interpretations
   (e.g. log vs. adjust).
5. The hub shall be the single entry point; the user shall never select a route manually, and the
   route taken shall be observable for testing/debugging.

**Coach:**

6. The Coach shall answer fitness and training knowledge questions in a conversational, on-brand
   coach voice, grounded in general training knowledge.
7. The Coach shall be the safe destination for general conversation that is not a generation or log
   request.

**Workout Generator:**

8. The Generator shall expose a search capability that, given target muscle group(s), available
   equipment, and/or movement pattern(s), returns matching exercises drawn only from the dataset.
9. The Generator shall expose a build capability that assembles selected exercises into a structured
   workout with three named blocks — warmup, main, cooldown — where every exercise carries sets,
   reps (or duration where the exercise is duration-based), and rest, and references a real dataset
   exercise by its identity.
10. When asked for a workout of a given duration, target, and equipment, the Generator shall produce
    a workout consistent with those constraints to the extent the dataset allows.
11. **(P1)** The Generator shall accept an injured-joint constraint and exclude from selection any
    exercise whose loaded joints include the named joint.
12. **(P1)** When the Generator selects a single-side (unilateral) exercise that has a paired
    opposite-side exercise in the dataset, it shall also include that paired exercise.

**Workout Logger:**

13. The Logger shall parse a natural-language description of a completed workout into one or more
    structured entries, each capturing exercise identity, sets, reps, and weight where stated.
14. The Logger shall resolve each parsed exercise name to a real dataset exercise via fuzzy matching
    (user says "bench press"; dataset says "Barbell Flat Bench Press"), and shall **explicitly flag
    as unmatched** any exercise it cannot confidently resolve — it shall never substitute an invented
    or arbitrary exercise.
15. The Logger shall persist resolved entries to a local store for the session and return the
    structured entries in its response.

**Resilience (cross-cutting):**

16. When a search returns no results (e.g. the user requests equipment absent from the dataset), the
    system shall recover gracefully — acknowledge the gap and offer an honest alternative or a
    clarifying question — and shall not crash and shall not fabricate exercises.
17. When the model emits an invalid tool call (unknown exercise identity, schema-invalid arguments),
    the system shall catch it and return a meaningful response, and shall not surface an unhandled
    error or stack trace to the user.
18. No user-facing response shall reference an exercise that does not exist in the dataset.

**Experience (UI):**

19. The system shall present a web-based chat interface through which a user can send messages and
    receive Cadence's responses end-to-end, exercising all three routes and the clarifying-question
    path.
20. The interface shall reflect Future's brand intent: premium, minimal, clean neutral palette,
    modern sans-serif typography, generous spacing, and a conversational-motivational coach voice
    (warm, encouraging, specific — in the spirit of "Nice lift — you recovered quickly between
    sets"), rather than a generic/default chatbot look and tone.
21. Generated workouts and parsed log entries shall be rendered in a readable, structured form in
    the chat (not as raw JSON dumps to the end user).

**Model abstraction & evaluation:**

22. The underlying LLM shall be swappable via configuration without code changes to agent logic, with
    one sensible default model configured out of the box.
23. The abstraction shall make explicit which configured models are capable of structured output /
    tool calling, since routing and the Generator's tool calls require that capability.
24. The README shall describe how the system would be evaluated in production — metrics, failure
    modes to monitor, signals of correct operation — and shall include how the model abstraction
    enables comparing/split-testing models on the routing and agent tasks.

**Multi-turn (P2):**

25. **(P2)** Within a single chat session, the system shall retain prior turns so that follow-up
    messages referencing earlier context ("adjust it", "I did a workout yesterday") and answers to
    the hub's clarifying questions resolve against that context without the user restating it.

**Observability (P2):**

26. **(P2)** Each LLM call and tool invocation shall be recorded (structured logging or a tracing
    integration) such that, for a given user message, the route taken, the tool calls made, and
    their outcomes can be reconstructed.

## 6. Acceptance Criteria

Each maps near 1:1 onto a test. "The system" = the assembled hub graph unless stated otherwise.

**Routing:**

1. Given the message "What muscles does a deadlift work?", when processed by the hub, then the
   structured classification's route is `COACH` and a numeric confidence is present.
2. Given the message "Build me a 30 min upper body session with dumbbells", when processed by the
   hub, then the route is `WORKOUT_GENERATE`.
3. Given the message "I just did 3x10 bench press at 185 lbs", when processed by the hub, then the
   route is `WORKOUT_LOG`.
4. Given the ambiguous message "I did a workout yesterday, can you adjust it?", when processed by the
   hub, then either (a) the classification confidence is below the threshold and the hub returns a
   clarifying question naming at least two plausible interpretations, or (b) — if confidence is high
   — the route taken is recorded and justifiable; the test asserts the hub did **not** silently
   dispatch a below-threshold classification.
5. Given the bare input "Bench press", when processed by the hub, then the hub returns a clarifying
   question rather than dispatching (confidence below threshold).
6. Given any input, when the hub classifies it, then the classification was obtained through the
   model's structured-output mechanism (verifiable by the classification being a typed object with a
   route enum and confidence field), not from keyword/regex logic.

**Generator:**

7. Given a request for an upper-body dumbbell workout, when the Generator runs, then the result
   contains exactly three named blocks (warmup, main, cooldown), and every exercise in the result
   has a non-empty sets value, a reps-or-duration value, a rest value, and an identity that matches a
   real entry in `data/exercises.json`.
8. Given a request specifying equipment present in the dataset, when the Generator searches, then
   every returned exercise's required equipment is satisfiable by the requested equipment set.
9. **(P1)** Given a request that says to avoid loading the knee, when the Generator builds the
   workout, then no exercise in the result lists "knee" among its loaded joints.
10. **(P1)** Given the Generator selects a unilateral exercise that has a paired opposite-side
    exercise in the dataset, when the workout is built, then the paired exercise also appears in the
    result.

**Logger:**

11. Given "I just did 3x10 bench press at 185 lbs", when the Logger runs, then it returns one
    structured entry with sets=3, reps=10, weight=185, and the resolved exercise identity is a real
    dataset entry whose name contains "Bench Press".
12. Given a logged exercise name with no reasonable dataset match (e.g. "did 3x10 zercher
    good-mornings"), when the Logger runs, then that entry is returned explicitly flagged as
    unmatched, and no invented/arbitrary dataset exercise is substituted for it.
13. Given a successful log parse, when the Logger completes, then the resolved entries are present in
    the local store.

**Resilience:**

14. Given a generation request for equipment absent from the dataset (e.g. "build me a workout using
    only a sled"), when the system runs, then it returns a graceful recovery response (acknowledging
    the gap and/or asking a clarifying question), the process does not raise an unhandled exception,
    and the response names no exercise outside the dataset.
15. Given a simulated invalid tool call (an unknown exercise identity or schema-invalid arguments),
    when the system handles it, then it returns a meaningful response and does not surface an
    unhandled error or stack trace.

**Experience:**

16. Given the demo is running, when a user sends, in turn, a coach question, a generation request, a
    log statement, and an ambiguous message, then the web chat UI displays an appropriate response
    for each (answer, structured workout, structured log confirmation, clarifying question
    respectively), with workouts and logs rendered as readable structured content rather than raw
    JSON.
17. Given the running UI, when inspected against the brand intent, then it uses a clean neutral
    palette, modern sans-serif type, generous spacing, and coach copy in a warm
    conversational-motivational voice — demonstrably distinct from an unstyled/default chat
    interface. (Validated visually against the documented brand tokens; a build-stage checklist
    item, not an automated assertion.)

**Tests, demo, docs, model abstraction:**

18. Given the repository, when its test suite is run from a clean clone per the README, then at least
    two automated critical-path tests execute and pass, and the README/test files state why each was
    chosen.
19. Given a clean clone, when the setup steps in the README are followed, then the chat demo runs and
    a committed transcript exists showing the three routes, the clarifying-question path, and a
    resilience recovery.
20. Given the README, when read, then it contains a "How I would evaluate this system in production"
    section naming concrete metrics, failure modes to monitor, and correctness signals, and
    describing how the model abstraction supports comparing/split-testing models.
21. Given the configured default model is changed to another structured-output-capable model via
    configuration only (no agent-logic code change), when the routing acceptance tests (criteria
    1–3) are re-run, then they still pass — demonstrating model-swappability.

**Multi-turn (P2):**

22. **(P2)** Given a session where the user first generates a workout and then sends "make it
    shorter" (or answers a prior clarifying question), when the second message is processed, then the
    response reflects the earlier turn's context without the user restating it.

**Observability (P2):**

23. **(P2)** Given a processed user message, when the trace/log for that message is inspected, then
    the route taken and each tool invocation with its outcome can be reconstructed.

## 7. Dependencies

1. **Fixed stack constraint (from the brief):** Python, LangGraph, and LangChain. This is a graded
   requirement, not an open architecture choice — the hub must be a LangGraph `StateGraph` with
   typed state and explicit edges, sub-agents must be separate graphs composed into the hub (not
   inlined functions), and tools must have Pydantic input schemas with field descriptions. The
   architecture stage decides everything *else*; these are non-negotiable inputs.
2. **The exercise dataset** (`data/exercises.json`, 50 entries, vendored into the repo) is the sole
   source of exercises. Relevant
   fields: `muscle_groups`, `joints_loaded` (enables P1 injury avoidance), `movement_patterns`,
   `equipment_required`, `is_bilateral` / `bilateral_pair_id` (enables P1 pairing). **Note:**
   `priority_tier` is `2` for all 50 entries — it carries no signal in this dataset and must not be
   relied upon for selection/ranking.
3. **An LLM provider reachable via the chosen abstraction**, with a default model that reliably
   supports structured output / tool calling (required for routing and the Generator). API
   credentials must be supplied via environment/config and documented in the README.
4. **A model abstraction layer** (the user has chosen an OpenRouter-style abstraction) that allows
   swapping the underlying model by configuration and that distinguishes structured-output-capable
   models — the architecture stage will commit the specifics.
5. **A public GitHub repository** for submission, with a clean-clone setup path documented in the
   README.
6. **Brand reference** (future.co aesthetic): captured at PRD level as intent (premium, minimal,
   neutral palette, sans-serif, conversational coach voice); concrete brand tokens (exact colors,
   fonts, spacing) are to be finalized at the architecture/build stage. Cited brand findings live in
   `docs/research/MARKET.md` and a build-stage brand pass.
7. **Forward-compatibility with the M2+ graph platform (design-intent, not M1 work).** Because
   Cadence is one evolving product (§10), three M1 seams should be shaped so the future
   knowledge-graph platform is a clean extension rather than a rewrite — *without* building any M2
   code in M1: **(a)** exercise/data access goes through a seam (a repository/interface boundary)
   so the JSON-backed M1 source can later be swapped for a graph-backed source; **(b)** injury
   avoidance is modeled as a *relationship* — "injury → affected joint(s) → exercises that load
   that joint" — rather than an inline predicate hard-coded against the JSON, since that relation
   *is* the M2 graph traversal in miniature; **(c)** agent responses can carry a structured
   "why"/explanation payload (even if M1 only populates it trivially), so M2's first-class
   explainability has a place to live. These are intents handed to the architecture stage; *how*
   they are realized is its decision. They must not expand M1's build scope or tiers.

## 8. Open Questions & Risks

1. **Scope-vs-time risk (highest).** Four stretch goals (two P1, two P2) plus a P0 branded UI plus
   the full graded core is realistically larger than a 2–3 hour window. *Mitigation:* the P0/P1/P2
   tiering in §4 gives the build an explicit cut-order — cut P2 (memory, observability) first, then
   P1, never P0. The PRD is honest that memory and observability are the first to go.
2. **Clarifying-question flow depends partly on memory (P2).** The "ask a clarifying question" path
   (req 4) works within a single turn even without memory (the hub asks; the user re-sends a
   clearer message). It only feels *seamless* across turns with multi-turn memory (req 25). *Risk:*
   if memory is cut, the clarifying path still satisfies its acceptance criteria but won't resolve
   the user's follow-up against the original message automatically. *Mitigation:* requirements are
   written so the clarifying behavior degrades gracefully without memory; memory is explicitly the
   thing that makes it seamless, not a prerequisite for the P0 criteria.
3. **OpenRouter / model structured-output variance.** OpenRouter exposes many models, but
   structured-output and tool-calling support **varies by underlying model** — reliable on OpenAI
   and Anthropic models, flaky or absent on some open-weight ones. *Risk:* a "swap any model" claim
   is false for non-capable models. *Mitigation:* req 23 — the abstraction must expose which models
   are structured-output-capable; the default and any split-test candidates must be capable ones.
   (See `docs/research/TECHNOLOGY.md`.)
4. **Thin/empty dataset slices make the resilience path easy to trigger — by design.** Long-tail
   equipment (e.g. 2 kettlebell exercises, 0 sleds) means realistic requests return few or no
   results. This is an asset (it makes req 16 demonstrable) but the Generator must handle thin —
   not just empty — result sets sensibly (don't pad a workout with irrelevant exercises just to fill
   blocks).
5. **Confidence threshold is a tuning decision.** The exact numeric threshold for "low confidence"
   (reqs 3–4) is an architecture/build-stage decision; the PRD fixes the *behavior* (below
   threshold → clarify) but not the number. *Risk:* a poorly chosen threshold either over-asks
   (annoying) or under-asks (misroutes). *Mitigation:* choose during build with the ambiguous test
   cases (reqs 4–5) as the calibration set.
6. **Brand replication fidelity.** "Looks like Future" (req 20, criterion 17) is partly subjective.
   *Mitigation:* convert brand intent into concrete documented tokens (palette, type scale, spacing)
   at the build stage and check the UI against those tokens, so "on-brand" becomes a checklist, not
   an opinion.
7. **Research gap.** The automated research pass covered domain/technology/market but **did not run a
   dedicated company/brand aesthetic pass**; brand intent here comes from a direct read of future.co
   plus `MARKET.md`. *Mitigation:* a focused brand-token capture is owed at the architecture/build
   stage before the UI is styled.
8. **Over-engineering M1 for M2 is itself a risk.** The forward-compatibility intents (§7.7) are
   deliberately scoped to *cheap, behavior-neutral seams* — a data interface, a relation-shaped
   injury model, an explanation field. The risk is gold-plating M1 with graph abstractions, a
   premature DB, or unused generality "because M2 needs it." *Mitigation:* the §4 tiers and the
   explicit "build nothing for M2 in M1" rule govern; the architecture stage applies a
   you-aren't-gonna-need-it bar — a seam earns its place in M1 only if it is essentially free and
   reversible. When in doubt, defer to M2.
9. **M2 milestones (§10) are intentionally low-resolution and will churn.** They are recorded at
   milestone level to inform M1 seams and the roadmap, not as a frozen spec. *Risk:* treating them
   as locked. *Mitigation:* §10 milestones get a proper PRD/architecture pass of their own when we
   actually start M2; key open questions for M2 are listed inline in §10.

## 10. Future Milestones (the product vision beyond M1)

> These are **future** milestones, recorded at milestone level to (a) inform the architecture and
> roadmap so M1's seams (§7.7) graduate cleanly, and (b) capture intent before it's lost. **None of
> this is in M1's scope.** Each milestone gets its own full PRD/architecture pass when we start it;
> the requirements below are the load-bearing intent, not a frozen spec (§8.9). The source brief for
> M2–M6 is `../candidate-assessment/2-knowledge-graph/KNOWLEDGE_GRAPH_ASSESSMENT.md` (external) — the
> natural
> maturation of Cadence into a **knowledge-graph coaching platform** that reasons over a member's
> context and **explains itself**, serving the **coach** persona (§2) alongside the member.
>
> **The through-line:** M1's differentiator is correct routing + honest, non-hallucinated answers.
> M2+'s differentiator is **reasoning over relationships** — the graph doing real work, so the
> system can answer *"why?"* by pointing at edges, not rationalizing. M1's injury filter is the seed
> of that thesis; everything below grows it.

**Milestone sequencing note:** M1 ships first and standalone. M2–M6 are grouped by the second brief
into one "1–2 day" platform build; we record them as distinct milestones so the roadmap can sequence
them, but they may be planned/built as a single later iteration. M1 → M2 is the only hard ordering
the PRD asserts; the rest is the roadmap's to sequence.

### M2 — Graph foundation & schema
The member's world modeled as a graph in a graph database, with a **documented schema**: node types
(at minimum Member, Exercise, Injury/Condition, Joint, Workout/History, Context-signal) and edge
types with stated meaning. The canonical traversal the schema must support: `Member → has-injury →
Joint → joints-loaded-by → Exercise`, enabling contraindication filtering by relationship rather
than by inline predicate. The 50-exercise dataset becomes Exercise nodes (carrying muscle_groups,
joints_loaded, movement_patterns, equipment, bilateral pairing). *Key open Qs for M2's own pass:*
graph DB choice (Neo4j preferred by the brief); whether to ground anatomy/injury concepts in a real
ontology (e.g. SNOMED CT) or a clean hand-rolled one; how M1's repository seam (§7.7a) is
re-implemented against the graph.

### M3 — Ingestion pipeline
A pipeline that turns member context — a raw profile plus a few **unstructured** signals (a chat
snippet, a logged injury, a transcript) — into structured nodes and edges. Must demonstrate
raw-text → graph: e.g. a free-text "my knee's been bugging me" becomes an Injury node linked to the
Knee joint. **Synthetic data only — never real member data.** Reuses M1's logger parsing as a
starting point for structuring logged workouts into history edges.

### M4 — GraphRAG retrieval
Retrieval that **combines graph traversal with vector/semantic search** — not one or the other.
Vector embeddings find semantically relevant context (free-text complaint → injury concept or
exercise); graph traversal expands from a matched node to its **safety-relevant neighborhood**
(e.g. injury → affected joints → contraindicated exercises). Assembles a **focused, token-efficient
context window** for generation. This is where "the graph does real work, not semantic search with
extra steps" must visibly hold. *Key open Q:* embedding model/store and how it co-resides with the
graph DB.

### M5 — Injury-aware generation + first-class explainability
Generation of personalized workout/coaching recommendations from the retrieved graph context, with
two hard guarantees: **(a) injury-aware** — an exercise loading an injured joint **never** appears,
and filtering down to few/no valid options recovers gracefully (recommend alternatives, don't crash
or hallucinate); **(b) explainable** — every recommendation answers *"why?"* with reasoning
**traceable to graph relationships** (e.g. "skipped barbell squat: knee injury → loads knee"), not a
vague LLM rationalization. This is the maturation of M1's §7.7c explanation payload and §7.7b
relation-shaped injury model into the product's headline capability. Adds an internal **safety
reviewer** step (a stretch in the brief) that re-checks generated recommendations against
contraindications before they reach the user.

### M6 — Coach-facing platform: API, dashboard, Dockerized infra
The surface that turns Cadence into a coach's co-pilot: **typed REST API** (request/response schemas)
for retrieval and generation; a **simple coach-facing frontend** (dashboard or chat) to demo the
end-to-end flow — including the three canonical coach asks: "build her a session this week", "why did
you skip X for her?", "what should I watch for with this member?"; and a **Dockerized local setup**
(`docker compose up` brings up the full stack: graph DB, API, frontend). Performance target from the
brief: **AI responses under ~5s** with deliberate token efficiency. The member-facing M1 chat
becomes one client of the same platform.

### Cross-cutting future capabilities (sequenced by the roadmap, not fixed to one milestone)
- **Observability across the platform** — tracing LLM calls, tool invocations, **and graph queries**
  (extends M1's P2 observability). Load-bearing for the production-evaluation story.
- **Evaluation pipeline** — measure retrieval relevance and recommendation quality (the M1 README
  describes how we'd evaluate; this milestone *builds* the harness, finally cashing in the model
  abstraction's split-test promise from req 24).
- **Graph visualization** of a member's context (coach-facing, aids trust/explainability).
- **Longitudinal reasoning** — adherence trends and progression over time, reasoning over the history
  subgraph M3 ingests.
- **Streaming responses** (deferred from M1's §4) — applies platform-wide once generation moves
  server-side in M6.

## 11. Revision History

| Date | Change | Decided By |
|------|--------|------------|
| 2026-06-02 | Initial draft. Locked: name "Cadence"; Core+1–2 signature stretches reframed as P0/P1/P2 tiers with branded UI elevated to P0; clarifying-question low-confidence handling; warmup/main/cooldown workout structure; logger resolves-or-flags (no invention); local persistence for logs; OpenRouter-style model abstraction with eval/split-test story in README; injury-avoidance + bilateral-pairing (P1), multi-turn memory + observability (P2). | User + PM |
| 2026-06-02 | Added product-vision framing: Cadence is one evolving product; current scope is **Milestone 1 (M1)**. Recorded the knowledge-graph platform as **future milestones M2–M6 + cross-cutting** (§10) — a real future build, milestone-level detail, both member & coach personas. Added coach persona (§2), three forward-compatibility seam intents for the architecture stage (§7.7, behavior-neutral, no M1 scope change), and over-engineering/churn risks (§8.8–8.9). No change to M1's §4 tiers or §§5–6 requirements/criteria. | User + PM |
