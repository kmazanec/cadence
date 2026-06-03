// Log card renderer: turns a LogPayload into a display-ready structure.
//
// The caller is responsible for rendering these values into the UI using brand
// tokens (card/spacing/text-primary/text-secondary from tailwind.config.js).
// Unmatched entries are flagged so the UI can present them distinctly — the
// user's original text is shown rather than any invented substitution.

import type { LogEntry, LogPayload } from "../types/api";

export interface RenderedLogEntry {
  /** The display name: the resolved catalogue name for matched entries, or
   * the user's raw text for unmatched entries — never an invented name. */
  displayName: string;
  /** Human-readable prescription detail (e.g. "3 × 10 @ 185 lbs"). */
  detail: string;
  /** True when the entry could not be resolved to a catalogue exercise. */
  unmatched: boolean;
}

export interface RenderedLogCard {
  entries: RenderedLogEntry[];
  matchedCount: number;
  unmatchedCount: number;
  /** One-line confirmation summary for the message bubble. */
  summary: string;
}

/** Format the prescription detail for one log entry. */
function formatDetail(entry: LogEntry): string {
  const parts: string[] = [];

  if (entry.sets !== null && entry.reps !== null) {
    parts.push(`${entry.sets} × ${entry.reps}`);
  } else if (entry.sets !== null) {
    parts.push(`${entry.sets} set${entry.sets !== 1 ? "s" : ""}`);
  } else if (entry.reps !== null) {
    parts.push(`${entry.reps} reps`);
  }

  if (entry.weight !== null) {
    parts.push(`@ ${entry.weight} lbs`);
  }

  return parts.length > 0 ? parts.join(" ") : "logged";
}

/** Render a single log entry into display-ready form. */
export function renderLogEntry(entry: LogEntry): RenderedLogEntry {
  return {
    displayName: entry.raw_name,
    detail: formatDetail(entry),
    unmatched: entry.unmatched,
  };
}

/** Render the full log payload into a card-ready structure. */
export function renderLogCard(payload: LogPayload): RenderedLogCard {
  const entries = payload.entries.map(renderLogEntry);
  const matchedCount = entries.filter((e) => !e.unmatched).length;
  const unmatchedCount = entries.filter((e) => e.unmatched).length;

  let summary: string;
  if (entries.length === 0) {
    summary = "Nothing logged.";
  } else if (unmatchedCount === 0) {
    summary =
      entries.length === 1
        ? `Logged 1 exercise.`
        : `Logged ${entries.length} exercises.`;
  } else if (matchedCount === 0) {
    summary =
      unmatchedCount === 1
        ? `1 exercise could not be matched — double-check the name.`
        : `${unmatchedCount} exercises could not be matched — double-check the names.`;
  } else {
    summary = `Logged ${matchedCount} exercise${matchedCount !== 1 ? "s" : ""}; ${unmatchedCount} unrecognised.`;
  }

  return { entries, matchedCount, unmatchedCount, summary };
}
