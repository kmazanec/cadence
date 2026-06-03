# Cadence Demo Transcript

This transcript shows the three canonical routes (coach, workout generator,
workout logger), the clarification path, and a resilience recovery
(empty-equipment search). All interactions were captured from a running
instance with `OPENROUTER_API_KEY` set.

---

## Session 1: Coach route — fitness question

**User:** What's the best way to build grip strength for deadlifts?

**Route:** `coach`

**Assistant (Cadence):**
> Let's talk grip — it's one of the most overlooked limiters in the deadlift.
> The two most practical moves: (1) Farmer's carries with heavy dumbbells or
> trap bar — these load your grip under a full-body carry pattern that mirrors
> the demands of a heavy pull. Go 3–4 sets of 30–40 metres. (2) Dead hangs from
> a pull-up bar — 3 sets of max hold time, 3× per week. Your grip will catch up
> within 4–6 weeks of consistent work. If you're already pulling near your grip
> ceiling, consider chalk before straps — you want to train the weakness, not
> just mask it.

---

## Session 2: Workout generator route

**User:** Build me a 30-minute upper-body dumbbell workout, no equipment except dumbbells.

**Route:** `workout_generate`

**Assistant (Cadence):**
> Here's your upper-body dumbbell workout:
>
> **Warmup (5 min)**
> - Dumbbell Arm Circle × 2 sets × 30 s, rest 30 s
> - Push-Up to Knee-Drive × 2 sets × 10 reps, rest 30 s
>
> **Main (20 min)**
> - Dumbbell Neutral-Grip Bench Press × 3 sets × 10 reps @ moderate weight, rest 60 s
> - Alternating Dumbbell Decline Bench Press × 3 sets × 10 reps each side, rest 60 s
> - Incline Dumbbell Chest Fly × 3 sets × 12 reps, rest 60 s
>
> **Cooldown (5 min)**
> - Dumbbell Standing Side Bend × 2 sets × 15 reps each side, rest 30 s

---

## Session 3: Workout logger route

**User:** Just finished: 3 sets of bench press at 135 lbs for 8 reps, and 2 sets of dumbbell curls at 30 lbs for 12.

**Route:** `workout_log`

**Assistant (Cadence):**
> Logged. Here's what I recorded:
>
> - **Bench press** (matched → Barbell Decline Bench Press): 3 × 8 @ 135 lb
> - **Dumbbell curls** (matched → Alternating Dumbbell Curl): 2 × 12 @ 30 lb

---

## Session 4: Clarification path — ambiguous intent

**User:** Help me with recovery.

**Route:** `clarification` (confidence 0.45 < threshold 0.70)

**Assistant (Cadence):**
> Could you tell me a bit more about what you'd like to do?
>
> - Ask a fitness question
> - Build me a workout
> - Log a workout I did

**User (follow-up, selects "Ask a fitness question"):** How do I reduce DOMS after leg day?

**Route:** `coach`

**Assistant (Cadence):**
> DOMS is mostly a sign your muscles got a novel stimulus — embrace it but
> don't let it sideline you. The fastest relief: light movement the next day
> (a 20-minute walk or easy spin) drives blood flow without adding damage.
> Cold/warm contrast showers help some people. Sleep is the non-negotiable:
> 7–9 hours is where the actual repair happens. And for next time, ramp up
> volume gradually — DOMS above a 3/10 soreness level is usually too much
> too fast.

---

## Session 5: Resilience recovery — equipment absent from dataset

**User:** Build me a workout using only a sled.

**Route:** `workout_generate`

**Generator behaviour:** `search_exercises(equipment=["sled"])` returns an
empty list. The generator tool loop finds no matching exercises. The subgraph
exhausts its retry budget (RETRY_CEILING = 2) and returns `workout=None`.
The hub boundary adapter emits a graceful recovery message. No exception
propagated; no non-dataset exercise was named.

**Assistant (Cadence):**
> I wasn't able to build a workout for that request. Try widening the
> equipment or muscle group selection.

**No traceback, no hallucinated exercise, no crash.**

---

*Transcript captured with `openai/gpt-4o-mini` as the default model.*
*Session IDs redacted for clarity.*
