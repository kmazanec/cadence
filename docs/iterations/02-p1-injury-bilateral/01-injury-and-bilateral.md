# Feature: Injury avoidance + bilateral pairing (P1)

**ID:** F-07 · **Iteration:** 02-p1-injury-bilateral · **Status:** Not started

## What this delivers (before → after)
**Before:** The generator ignores injuries and trains only one side of unilateral exercises.
**After:** The generator excludes any exercise loading an injured joint (hard pre-filter) and, when it
selects a single-side exercise with a dataset pair, auto-includes the opposite side.

## How it fits the roadmap
The whole of iteration 02 (P1 differentiators). Both are small `build_workout` extensions sharing the
generator code path, cut together. Iteration 02 is independent of iteration 03 (can build
concurrently once iteration 01 is merged).

## Requirements traced (from the PRD)
Reqs 11–12; acceptance criteria 9–10.

## Dependencies (must exist before this starts)
- **F-04 (workout generator)** — HARD dep: extends the generator's selection/build path with the
  contraindication exclusion set and the bilateral-pair inclusion.
- (Builds on F-01's `ExerciseRepository`, extended with `contraindicated_ids` + `bilateral_pair`.)

## Unblocks (what waits on this)
- F-11 ("why these?" panel) — renders the exclusion/pairing reasons this feature emits.

## Contracts touched
- **ExerciseRepository** (ADR-008) — extends with `contraindicated_ids(injuries)` (the injury→joint→
  exercise relation + hard-exclusion set) and `bilateral_pair(id)`.
- **Reason/explanation payload** (ADR-012) — extends with `excluded`/`loads_joint` and
  `added`/`bilateral_pair_of` reasons.
- **Injury-as-relationship policy** (ADR-009) — hard pre-filter (exclude, never soft re-rank).

## Acceptance criteria (product behavior)
1. A request to avoid loading the knee yields a workout with **zero** exercises listing "knee" in
   their loaded joints (hard exclusion, regardless of other ranking).
2. When the generator selects a unilateral exercise that has a `bilateral_pair_id` in the dataset, the
   paired opposite-side exercise also appears in the result.
3. Over-exclusion leaving few/no valid exercises recovers gracefully (alternatives or honest gap), per
   the resilience policy — never padding with contraindicated or irrelevant exercises.
4. The exclusion and pairing decisions are emitted as structured explanation reasons.

## Testing requirements
- **Integration (deterministic, no LLM):** given a knee injury, assert the built workout contains no
  knee-loading exercise (designated critical path ADR-018 #2 — safety; rationale recorded).
- **Unit:** `contraindicated_ids({knee})` returns exactly the knee-loading IDs; `bilateral_pair`
  returns the partner; a unilateral selection pulls in its pair.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)

### Pre-build decisions (locked by Keith, 2026-06-02)

- **Dangling `bilateral_pair_id` (AC #2):** all 18 `bilateral_pair_id` values in
  `data/exercises.json` are dangling — `repo.bilateral_pair()` returns `None` for every
  catalogue entry. **DECISION: synthetic fixture.** Exercise the bilateral auto-pairing
  build path and the `bilateral_pair` unit test against a small in-memory fixture repo
  (a `list[Exercise]` with one reciprocal resolvable pair). **Do NOT mutate the shipped
  `data/exercises.json`.** Make any real-dataset AC #2 assertion conditional/skip with a
  recorded rationale, since no real pair resolves. The auto-pairing CODE path must still
  be fully exercised by the fixture.

<!-- BUILD-PLAN:kmaz-plan-iteration -->

## Build plan (kmaz-plan-iteration) — F-07

**Model tier:** `sonnet`

F-07 is wiring + reasons + tests, not new infrastructure: the repo methods (contraindicated_ids, bilateral_pair), the Reason vocabulary (excluded/loads_joint, added/bilateral_pair_of), and GeneratorState.injuries all already exist and are correct. The real work is (1) actually feeding injuries into the generator — they are currently hardcoded to [] at hub.py:178 with no extractor anywhere; (2) applying the contraindication set as a hard pre-filter in the search-candidate path AND as a gate check (defense-in-depth per ADR-009/010); (3) auto-including a selected unilateral exercise's bilateral pair during build; and (4) emitting the exclusion/pairing Reasons in the generator boundary node where the other reasons are already built. The single biggest blocker is that ALL 18 bilateral_pair_id values in data/exercises.json are dangling (none resolve via _by_id), so bilateral_pair() returns None for every catalogue entry and AC #2 cannot pass against the real dataset without either a dataset fix or a synthetic-pair test fixture — this needs a decision before build.

### Reuse — already exists, do NOT rebuild

- contraindicated_ids(injuries)->set[str] fully implemented: case-folds injuries, intersects with each exercise's joints_loaded, returns the exclusion id set. Do NOT rebuild.  
  _backend/app/data/json_repository.py:65-73_
- bilateral_pair(id)->Exercise|None fully implemented: resolves bilateral_pair_id via _by_id, returns None on missing/dangling. Do NOT rebuild.  
  _backend/app/data/json_repository.py:75-79_
- ExerciseRepository Protocol already declares both methods — the 'extends ExerciseRepository' contract in the spec is already satisfied at the data layer.  
  _backend/app/data/repository.py:56-62_
- Reason vocabulary already includes claim 'excluded'/'added' and relation 'loads_joint'/'bilateral_pair_of' — no explanation.py change needed.  
  _backend/app/graph/explanation.py:15-23_
- GeneratorState already carries injuries: list[str] and targets: list[str] — no state schema change needed; injuries is currently dead (always []).  
  _backend/app/agents/generator/state.py:16-22_
- The generator boundary node is where include-reasons are already built (matches_target/equipment_match) and where injuries are hardcoded to [] — this is the wiring seam for both injury extraction and exclusion/pairing reasons.  
  _backend/app/graph/hub.py:163-235 (injuries=[] at line 178; reason loop at 189-216)_
- _execute_search is the candidate-search seam inside the generate node — the natural place to apply the hard pre-filter so contraindicated ids are never offered to the LLM.  
  _backend/app/agents/generator/graph.py:64-87 (called at line 168)_
- validate_workout output gate iterates every prescription id — extend it to also reject contraindicated ids (defense-in-depth), reusing its existing GateResult/retry plumbing.  
  _backend/app/agents/generator/output_gate.py:35-49_
- build_workout is the assembly point that resolves ids per block — bilateral auto-pairing is a build_workout extension (the spec says 'small build_workout extension').  
  _backend/app/agents/generator/build_workout.py:21-72_
- Existing generator integration test + schema-aware sequential fake model pattern to copy for the new deterministic tests.  
  _backend/tests/integration/test_generator_subgraph.py:95-120_
- Joint vocabulary is small and clean (shoulder/elbow/wrist/knee/hip/cervical spine/ankle/thoracic spine/lumbar spine) — bounds the M1 injury synonym/normalization map ADR-009 calls for.  
  _data/exercises.json (50 entries; 21 load knee, 29 remain after knee exclusion)_

### Contrarian risks & mitigations

- **Risk:** SHOWSTOPPER for AC #2: all 18 bilateral_pair_id values in data/exercises.json are DANGLING — zero resolve via _by_id, so bilateral_pair() returns None for every catalogue exercise. The Exercise docstring even warns of this ('may reference a row not present'). The bilateral unit test ('bilateral_pair returns the partner') and AC #2 ('paired opposite-side exercise also appears') cannot pass against the real dataset.  
  **Mitigation:** Decide at build start (open question): EITHER (a) test bilateral_pair + the auto-pairing build logic against a small synthetic in-memory fixture repo that has a genuinely resolvable pair (keeps the dataset untouched, still proves the wiring) AND make AC #2's integration assertion conditional/skip-with-rationale since no real pair exists; OR (b) patch a couple of reciprocal bilateral_pair_id links into exercises.json so one left/right pair truly resolves, then assert against it. Prefer (a): do not silently mutate the shipped dataset. Either way the auto-pairing CODE path must be exercised by a fixture, not assumed reachable via real data.
- **Risk:** No injury extractor exists anywhere. injuries is hardcoded to [] (hub.py:178) and ChatRequest carries only message/session_id. Without a source, the entire feature is inert end-to-end even though the repo method works.  
  **Mitigation:** Add a deterministic injury-extraction helper (keyword/synonym scan over user_message against the known joint vocab — ADR-009 explicitly asks for 'a small explicit synonym/normalization map in M1'). Wire it in the generator boundary node to populate generator_input['injuries']. Keep it pure/deterministic so the ADR-018 #2 critical-path test needs NO LLM. Do NOT route injuries through the LLM tool args — that reintroduces nondeterminism into a safety path.
- **Risk:** Reasons are built in the hub boundary node (hub.py:189), but exclusion/pairing decisions are made inside the subgraph (search filter, build pairing). The boundary node cannot see what was excluded or auto-added unless the subgraph surfaces it.  
  **Mitigation:** Surface the decisions on GeneratorState: add excluded_ids and/or added_pair_ids (or recompute excluded set in the boundary node from injuries+repo, which is deterministic and cheap). Simplest: boundary node recomputes contraindicated_ids(injuries) for the 'excluded' reasons, and reads the assembled workout to detect auto-added pair members for 'added' reasons. Avoid adding a reasons list to GeneratorState if recomputation in the boundary is equivalent — keeps the subgraph state lean.
- **Risk:** ADR-009 mandates hard PRE-filter, never soft re-rank, and complements (not replaces) the output gate. Applying the filter ONLY at the gate would let contraindicated candidates reach the LLM and force retries; applying ONLY at search would lose the safety net if the LLM invents/echoes a contraindicated id.  
  **Mitigation:** Apply at BOTH: (1) filter contraindicated ids out of _execute_search results so the LLM never sees them; (2) extend validate_workout to fail if any prescription id is in the contraindicated set (reusing the existing retry/recovery plumbing). The critical-path test asserts the END-TO-END invariant (zero knee-loading exercises in the built workout), which both layers jointly guarantee.
- **Risk:** Auto-pairing can blow up block size or duplicate an already-selected pair, and the pair member may itself be contraindicated (e.g. a knee-loading left/right pair under a knee injury), which would violate the exclusion invariant if added blindly.  
  **Mitigation:** When auto-including a bilateral pair: (a) skip if the partner id is already in the selected set; (b) re-check the partner against the contraindicated set and do NOT add it if contraindicated (exclusion wins over pairing — safety precedence); (c) place the partner in the same block as its source. Add a test for the contraindicated-partner case.
- **Risk:** Over-exclusion recovery (AC #3): if injuries exclude most/all candidates, the generator must recover gracefully (alternatives or honest gap), never pad with contraindicated/irrelevant exercises. The existing retry loop just retries the same prompt and will exhaust to the empty-result path.  
  **Mitigation:** Verify the empty/thin path already routes to the graceful 'I wasn't able to build a workout' reply (hub.py:218-229) and that the gate's contraindication failure increments retry without fabricating. Add a deterministic test with an over-broad injury set (e.g. exclude hip+knee+ankle+shoulder) asserting graceful gap, no contraindicated padding. This overlaps ADR-018 #3 — coordinate so it isn't double-owned.
- **Risk:** Schema-aware fake seam lesson (ADR-018, memory): a per-feature fake that ignores schema breaks the shared get_model seam. Any new structured-output call site (e.g. if injury extraction were ever made LLM-based) would re-trigger the latent integration break.  
  **Mitigation:** Keep injury extraction deterministic (no get_model call). For the new deterministic generator tests, reuse the existing _SequentialFakeModel pattern from test_generator_subgraph.py; do not introduce a new role-specific fake.

### Contract touchpoints

- **ExerciseRepository (ADR-008)** — already implemented in backend/app/data/json_repository.py (contraindicated_ids:65-73, bilateral_pair:75-79) and declared in repository.py:56-62. No signature change — F-07 consumes, does not extend.
- **Reason / explanation payload (ADR-012)** — already satisfied — claim 'excluded'/'added' and relation 'loads_joint'/'bilateral_pair_of' already in explanation.py:15-23. F-07 only emits these triples from hub.py; no vocabulary change.
- **Injury-as-relationship hard-exclusion policy (ADR-009)** — new enforcement: hard pre-filter in _execute_search (graph.py) AND a contraindication check added to validate_workout (output_gate.py). Never a soft re-rank.
- **GeneratorState (ADR-004 isolated subgraph state)** — injuries: list[str] field already exists (state.py:18) but is dead; F-07 populates it. May add excluded_ids/added_pair_ids only if boundary-node recomputation is insufficient — prefer recompute, no schema growth.
- **output_gate GateResult (ADR-010)** — extend GateResult with a contraindicated_ids field and validate_workout signature to accept injuries (or the contraindicated set); reuse existing valid/retry plumbing.
- **build_workout assembly (F-04)** — signature extended to accept injuries (or contraindicated set) so auto-paired partners can be exclusion-checked before inclusion; adds same-block bilateral partner inclusion with dedupe + dangling-pair guard.

### Build steps (checkbox)

- [ ] **1.** Resolve the dangling-pair open question with the human: confirm approach (a) synthetic fixture repo for the bilateral path + conditional/rationale on AC#2, vs (b) patch reciprocal links into exercises.json. Record the decision in the spec's Implementation notes before writing pairing tests.
  - Files: `docs/iterations/02-p1-injury-bilateral/01-injury-and-bilateral.md`
  - Verify: Decision recorded; no code yet. Gates step 6/7.
- [ ] **2.** Write the critical-path test FIRST (ADR-018 #2, deterministic, no LLM): given injuries=['knee'], run build_generator_subgraph with the sequential fake whose canned build_workout call deliberately includes a knee-loading id; assert the final state['workout'] contains ZERO exercises whose joints_loaded includes 'knee'. Include a written rationale docstring per ADR-018.
  - Files: `backend/tests/critical/test_injury_hard_exclusion.py`
  - Verify: uv run pytest tests/critical/test_injury_hard_exclusion.py -k knee — RED before impl, GREEN after steps 4-5. This is the gating safety test.
- [ ] **3.** Write unit tests for the repo methods against an in-memory fixture: contraindicated_ids({'knee'}) equals exactly the set of knee-loading ids (compute expected from the dataset); contraindicated_ids([]) == set(); case-insensitive ('Knee'). For bilateral_pair, use a synthetic fixture repo with one resolvable reciprocal pair (per step-1 decision) and assert it returns the partner, and returns None for a dangling/absent id.
  - Files: `backend/tests/unit/test_contraindication.py`, `backend/tests/unit/test_bilateral_pair.py`
  - Verify: uv run pytest tests/unit/test_contraindication.py tests/unit/test_bilateral_pair.py — GREEN (these test already-implemented methods; they lock behavior, esp. the dangling-pair None case).
- [ ] **4.** Add a deterministic injury-extraction helper (pure function: user_message -> list[str] of normalized joints) with a small synonym/normalization map over the known joint vocab (knee/hip/shoulder/ankle/elbow/wrist/spine synonyms). Unit-test it (e.g. 'my knee hurts' -> ['knee']; 'no injuries' -> []).
  - Files: `backend/app/agents/generator/injury_extraction.py`, `backend/tests/unit/test_injury_extraction.py`
  - Verify: uv run pytest tests/unit/test_injury_extraction.py — GREEN; helper is deterministic, no get_model call.
- [ ] **5.** Apply the hard pre-filter in the candidate path: in _execute_search (graph.py), drop any result whose id is in repo.contraindicated_ids(state injuries). Thread the injuries from GeneratorState into _make_generate_node so the search filter and tool loop can see them.
  - Files: `backend/app/agents/generator/graph.py`
  - Verify: New subgraph test: with injuries=['knee'], search results returned to the model contain no knee-loading id. Critical-path test (step 2) still relies on the gate too.
- [ ] **6.** Extend the output gate: validate_workout(payload, repo, injuries) (or a sibling check) fails when any prescription id is in contraindicated_ids(injuries); reuse GateResult/unknown_ids-style plumbing (add contraindicated_ids field). Wire the gate node to pass injuries through. This is the defense-in-depth layer that makes the step-2 critical-path test pass even if a contraindicated id reaches build.
  - Files: `backend/app/agents/generator/output_gate.py`, `backend/app/agents/generator/graph.py`
  - Verify: uv run pytest tests/critical/test_injury_hard_exclusion.py — now GREEN; add a gate unit test feeding a knee-loading id under injuries=['knee'] -> GateResult.valid is False.
- [ ] **7.** Implement bilateral auto-pairing in build_workout: after resolving each block, for any selected unilateral exercise with a resolvable bilateral_pair, also include the partner in the SAME block IF the partner is not already selected AND not contraindicated under the current injuries. Pass injuries (or the contraindicated set) into build_workout. Guard against duplicates and dangling pairs (skip when bilateral_pair returns None).
  - Files: `backend/app/agents/generator/build_workout.py`, `backend/app/agents/generator/graph.py`
  - Verify: uv run pytest tests/integration/test_bilateral_pairing.py — selecting a unilateral exercise (synthetic fixture w/ resolvable pair per step 1) yields both sides; a contraindicated partner is NOT auto-added.
- [ ] **8.** Wire injuries end-to-end in the generator boundary node: replace hardcoded injuries=[] (hub.py:178) with the extracted injuries from user_message via the step-4 helper.
  - Files: `backend/app/graph/hub.py`
  - Verify: Existing hub/generator integration tests still pass; a new test asserts a 'knee injury' message produces a knee-free workout through the hub.
- [ ] **9.** Emit exclusion + pairing Reasons in the boundary node: for each id in contraindicated_ids(injuries) that is relevant, append Reason(claim='excluded', subject=name, relation='loads_joint', object='knee'); for each auto-added partner detected in the workout, append Reason(claim='added', subject=partner.name, relation='bilateral_pair_of', object=source.name). Append alongside the existing matches_target/equipment_match reasons.
  - Files: `backend/app/graph/hub.py`
  - Verify: Test asserts response.explanation contains an 'excluded'/'loads_joint' reason for a knee request and an 'added'/'bilateral_pair_of' reason when a pair is auto-included (synthetic fixture).
- [ ] **10.** Add the over-exclusion graceful-recovery test (AC #3): with an over-broad injury set, assert the generator recovers gracefully (honest gap reply, no contraindicated/fabricated padding) rather than crashing or padding. Coordinate ownership with ADR-018 #3 so it isn't duplicated.
  - Files: `backend/tests/integration/test_injury_over_exclusion_recovery.py`
  - Verify: uv run pytest tests/integration/test_injury_over_exclusion_recovery.py — graceful path, workout is None or honestly thin, zero contraindicated ids.
- [ ] **11.** Run the full backend suite to confirm no regression in router/generator/logger wiring (schema-aware fake seam intact).
  - Files: _(no file change)_
  - Verify: uv run pytest — all green; ADR-018 #1 router tests unaffected by the new injury wiring.

### Test plan

| Test | Kind | Critical | Asserts |
|------|------|----------|---------|
| `test_injury_hard_exclusion::knee_request_yields_zero_knee_loading` | integration | ✅ **yes** | With injuries=['knee'] and a fake build call that includes a knee-loading id, the final built workout contains zero exercises whose joints_loaded includes 'knee' (end-to-end safety invariant, no LLM). Includes written rationale docstring. |
| `test_contraindication::exact_knee_set_and_empty_and_caseinsensitive` | unit | no | contraindicated_ids({'knee'}) equals exactly the dataset's knee-loading id set; contraindicated_ids([]) == set(); 'Knee' matches case-insensitively. |
| `test_bilateral_pair::returns_partner_and_none_on_dangling` | unit | no | Against a synthetic fixture with one resolvable reciprocal pair, bilateral_pair(source) returns the partner; against a dangling/absent id it returns None (locks the real-dataset behavior). |
| `test_injury_extraction::message_to_joints` | unit | no | Deterministic helper maps 'my knee is hurt' -> ['knee'], handles synonyms, and returns [] when no injury mentioned. No get_model call. |
| `test_search_excludes_contraindicated` | unit | no | _execute_search under injuries=['knee'] returns no knee-loading id to the model (pre-filter layer). |
| `test_gate_rejects_contraindicated` | unit | no | validate_workout with a knee-loading prescription under injuries=['knee'] returns GateResult.valid=False with the id in contraindicated_ids (defense-in-depth layer). |
| `test_bilateral_pairing::unilateral_selection_pulls_in_pair` | integration | no | Selecting a unilateral exercise (synthetic resolvable pair) auto-includes its opposite side in the same block; a contraindicated partner is NOT auto-added; no duplicate when partner already selected (AC #2). |
| `test_explanation_reasons::excluded_and_added_emitted` | integration | no | response.explanation contains a Reason(claim='excluded', relation='loads_joint') for a knee request and a Reason(claim='added', relation='bilateral_pair_of') when a pair is auto-included (AC #4). |
| `test_injury_over_exclusion_recovery` | integration | no | An over-broad injury set yields graceful recovery (honest gap / thin result), never padding with contraindicated or irrelevant exercises (AC #3). |

### Open questions (decide before/at build)

- ❓ BLOCKER for AC #2: all 18 bilateral_pair_id values in data/exercises.json are dangling (none resolve), so bilateral_pair() returns None catalogue-wide and no real unilateral selection can pull in a real partner. Choose before build: (a) test the auto-pairing code path against a synthetic in-memory fixture repo with a resolvable reciprocal pair, and make AC #2's real-dataset assertion conditional with a recorded rationale; or (b) patch a couple of reciprocal bilateral_pair_id links into exercises.json so one left/right pair truly resolves. Recommend (a) — do not silently mutate the shipped dataset.
- ❓ Confirm the injury source for M1: deterministic keyword/synonym extraction from user_message (recommended, keeps ADR-018 #2 LLM-free) vs adding an explicit injuries field to ChatRequest/the API envelope. The plan assumes deterministic extraction.
- ❓ Ownership of the over-exclusion graceful-recovery test (AC #3) overlaps ADR-018 critical-path #3 (output gate + empty-result recovery, owned elsewhere). Confirm whether F-07 adds its injury-specific recovery test or extends the existing one to avoid double-coverage.
