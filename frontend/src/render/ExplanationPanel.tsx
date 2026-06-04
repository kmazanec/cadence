/**
 * ExplanationPanel: a collapsed disclosure showing why the workout was built
 * the way it was.
 *
 * Renders inside WorkoutCardView on workout turns only. Uses the native
 * <details>/<summary> element — no JavaScript state needed; collapsed by
 * default per spec. Returns null when there is nothing to show (empty reasons
 * or note-only reasons), so the panel is invisible on non-workout turns.
 *
 * All visual values come from brand tokens; no ad-hoc colors or spacing.
 */

import type { Reason } from "../types/api";
import { explanationLines } from "./explanationLines";

interface Props {
  reasons: Reason[];
}

export function ExplanationPanel({ reasons }: Props) {
  const lines = explanationLines(reasons);

  // Nothing to show — hide the panel rather than rendering an empty disclosure.
  if (lines.length === 0) {
    return null;
  }

  return (
    <details className="mt-3 rounded-button border border-border bg-surface-sunken px-3 py-2 text-sm">
      <summary className="cursor-pointer select-none font-subheading text-accent-deep">
        Why these?
      </summary>
      <ul className="mt-2 space-y-1">
        {lines.map((line, i) => (
          <li key={i} className="text-text-secondary">
            {line}
          </li>
        ))}
      </ul>
    </details>
  );
}
