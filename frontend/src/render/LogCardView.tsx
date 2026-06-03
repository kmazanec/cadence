/**
 * LogCardView: renders a LogPayload as a branded confirmation card.
 *
 * The card's shape comes from the pure `renderLogCard` shaper; this component
 * only maps that shape onto brand tokens. Unmatched entries are flagged so the
 * user sees their original text rather than an invented substitution.
 */

import { renderLogCard } from "./LogCard";
import type { LogPayload } from "../types/api";

export function LogCardView({ payload }: { payload: LogPayload }) {
  const card = renderLogCard(payload);

  return (
    <div className="space-y-2">
      <p className="text-sm font-subheading text-text-secondary">
        {card.summary}
      </p>

      <ul className="space-y-1">
        {card.entries.map((entry, i) => (
          <li key={i} className="text-body text-text-primary">
            <span className="font-subheading">{entry.displayName}</span>
            <span className="text-text-secondary"> — {entry.detail}</span>
            {entry.unmatched && (
              <span className="ml-1 text-xs text-accent">(unrecognised)</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
