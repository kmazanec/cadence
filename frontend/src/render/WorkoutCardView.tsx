/**
 * WorkoutCardView: renders a WorkoutPayload as a branded workout card.
 *
 * The card's shape comes from the pure `renderWorkoutCard` shaper; this
 * component only maps that shape onto brand tokens (no ad-hoc colors/spacing).
 * Structured content always renders as a card, never as raw JSON.
 *
 * Visual language: a summary banner, then each block as a labelled lane with a
 * tempo-dot marker and a clean numbered prescription list.
 */

import { renderWorkoutCard } from "./WorkoutCard";
import type { WorkoutPayload } from "../types/api";

export function WorkoutCardView({ payload }: { payload: WorkoutPayload }) {
  const card = renderWorkoutCard(payload);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 rounded-button bg-surface-sunken px-3 py-2">
        <span aria-hidden="true">🏋️</span>
        <p className="text-sm font-subheading text-text-primary">
          {card.summary}
        </p>
      </div>

      {card.blocks.map((block, bi) => (
        <div key={bi}>
          <h3 className="mb-2 flex items-center gap-2 font-subheading text-[0.8rem] uppercase tracking-wide text-accent-deep">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-volt ring-2 ring-accent/30" />
            {block.title}
          </h3>
          <ul className="space-y-2">
            {block.exercises.map((ex, ei) => (
              <li
                key={ei}
                className="flex items-baseline gap-3 border-b border-border/60 pb-2 last:border-0 last:pb-0"
              >
                <span className="w-5 shrink-0 font-display text-sm font-bold text-text-muted">
                  {ei + 1}
                </span>
                <div className="flex-1">
                  <span className="font-subheading text-body text-text-primary">
                    {ex.name}
                  </span>
                  <span className="block text-sm text-text-secondary">
                    {ex.detail}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
