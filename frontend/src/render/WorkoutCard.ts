// Workout card renderer: turns a WorkoutPayload into a display-ready structure.
//
// Parallel to LogCard: a pure shaper, no JSX. The caller renders these values
// using brand tokens (card/spacing/text-primary/text-secondary). Each block
// (warmup / main / cooldown) becomes a titled group of prescriptions, each
// formatted into a single human-readable line.

import type { Block, BlockName, Prescription, WorkoutPayload } from "../types/api";

export interface RenderedPrescription {
  /** The exercise's display name. */
  name: string;
  /** Human-readable prescription detail (e.g. "3 × 10 @ 135 lbs, 60s rest"). */
  detail: string;
}

export interface RenderedBlock {
  /** Block label for display (e.g. "Warmup", "Main", "Cooldown"). */
  title: string;
  exercises: RenderedPrescription[];
}

export interface RenderedWorkoutCard {
  blocks: RenderedBlock[];
  /** Total prescriptions across all blocks. */
  exerciseCount: number;
  /** One-line summary for the message bubble. */
  summary: string;
}

const BLOCK_TITLES: Record<BlockName, string> = {
  warmup: "Warmup",
  main: "Main",
  cooldown: "Cooldown",
};

/** Format the prescription detail for one exercise. */
function formatDetail(p: Prescription): string {
  const parts: string[] = [];

  // Reps-based or duration-based prescription, never both.
  if (p.reps !== null) {
    parts.push(`${p.sets} × ${p.reps}`);
  } else if (p.duration_seconds !== null) {
    parts.push(`${p.sets} × ${p.duration_seconds}s`);
  } else {
    parts.push(`${p.sets} set${p.sets !== 1 ? "s" : ""}`);
  }

  if (p.weight !== null) {
    parts.push(`@ ${p.weight}`);
  }

  parts.push(`${p.rest_seconds}s rest`);

  return parts.join(", ");
}

/** Render a single prescription into display-ready form. */
export function renderPrescription(p: Prescription): RenderedPrescription {
  return { name: p.name, detail: formatDetail(p) };
}

/** Render a single block into display-ready form. */
export function renderBlock(block: Block): RenderedBlock {
  return {
    title: BLOCK_TITLES[block.name],
    exercises: block.exercises.map(renderPrescription),
  };
}

/** Render the full workout payload into a card-ready structure. */
export function renderWorkoutCard(payload: WorkoutPayload): RenderedWorkoutCard {
  const blocks = payload.blocks.map(renderBlock);
  const exerciseCount = blocks.reduce((n, b) => n + b.exercises.length, 0);

  const summary =
    exerciseCount === 0
      ? "No exercises in this workout."
      : `Workout ready — ${exerciseCount} exercise${exerciseCount !== 1 ? "s" : ""} across ${blocks.length} block${blocks.length !== 1 ? "s" : ""}.`;

  return { blocks, exerciseCount, summary };
}
