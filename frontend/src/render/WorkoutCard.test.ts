import { describe, expect, it } from "vitest";
import type { WorkoutPayload } from "../types/api";
import { renderWorkoutCard } from "./WorkoutCard";

function rx(over: Record<string, unknown> = {}) {
  return {
    exercise_id: "ex1",
    name: "Bench Press",
    sets: 3,
    reps: 10,
    duration_seconds: null,
    rest_seconds: 60,
    weight: "135 lbs",
    ...over,
  };
}

describe("renderWorkoutCard", () => {
  it("titles blocks and formats reps-based prescriptions", () => {
    const payload: WorkoutPayload = {
      blocks: [{ name: "main", exercises: [rx()] }],
    };
    const card = renderWorkoutCard(payload);
    expect(card.blocks[0].title).toBe("Main");
    expect(card.blocks[0].exercises[0].name).toBe("Bench Press");
    expect(card.blocks[0].exercises[0].detail).toBe("3 × 10, @ 135 lbs, 60s rest");
    expect(card.exerciseCount).toBe(1);
  });

  it("formats duration-based prescriptions without reps", () => {
    const payload: WorkoutPayload = {
      blocks: [
        {
          name: "warmup",
          exercises: [
            rx({ reps: null, duration_seconds: 30, weight: null }),
          ],
        },
      ],
    };
    const card = renderWorkoutCard(payload);
    expect(card.blocks[0].title).toBe("Warmup");
    expect(card.blocks[0].exercises[0].detail).toBe("3 × 30s, 60s rest");
  });

  it("summarises across blocks", () => {
    const payload: WorkoutPayload = {
      blocks: [
        { name: "warmup", exercises: [rx()] },
        { name: "main", exercises: [rx(), rx()] },
      ],
    };
    const card = renderWorkoutCard(payload);
    expect(card.exerciseCount).toBe(3);
    expect(card.summary).toContain("3 exercises");
    expect(card.summary).toContain("2 blocks");
  });

  it("handles an empty workout", () => {
    const card = renderWorkoutCard({ blocks: [] });
    expect(card.exerciseCount).toBe(0);
    expect(card.summary).toBe("No exercises in this workout.");
  });
});
