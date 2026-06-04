/**
 * WorkoutCardView: renders a WorkoutPayload as a branded card with an optional
 * explanation panel.
 *
 * The card's shape comes from the pure `renderWorkoutCard` shaper; this
 * component only maps that shape onto brand tokens (no ad-hoc colors/spacing).
 * Structured content always renders as a card, never as raw JSON. When reasons
 * are present the ExplanationPanel appears collapsed below the exercise list.
 */

import { renderWorkoutCard } from "./WorkoutCard";
import { ExplanationPanel } from "./ExplanationPanel";
import type { Reason, WorkoutPayload } from "../types/api";

interface Props {
  payload: WorkoutPayload;
  /** Structured reasons from the agent — rendered as a collapsed disclosure. */
  reasons?: Reason[];
}

export function WorkoutCardView({ payload, reasons = [] }: Props) {
  const card = renderWorkoutCard(payload);

  return (
    <div className="space-y-3">
      <p className="text-sm font-subheading text-text-secondary">
        {card.summary}
      </p>

      {card.blocks.map((block, bi) => (
        <div key={bi} className="space-y-1.5">
          <h3 className="text-xs font-subheading uppercase tracking-wide text-text-secondary">
            {block.title}
          </h3>
          <ul className="space-y-1">
            {block.exercises.map((ex, ei) => (
              <li key={ei} className="text-body text-text-primary">
                <span className="font-subheading">{ex.name}</span>
                <span className="text-text-secondary"> — {ex.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <ExplanationPanel reasons={reasons} />
    </div>
  );
}
