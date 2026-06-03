/**
 * LogCardView: renders a LogPayload as a branded confirmation card.
 *
 * The card's shape comes from the pure `renderLogCard` shaper; this component
 * only maps that shape onto brand tokens. Unmatched entries are flagged so the
 * user sees their original text rather than an invented substitution.
 *
 * Visual language: a confirmation banner, then each entry as a checked-off row.
 * Matched entries get a volt check; unmatched ones get a warning flag and keep
 * the user's raw text.
 */

import { renderLogCard } from "./LogCard";
import type { LogPayload } from "../types/api";

export function LogCardView({ payload }: { payload: LogPayload }) {
  const card = renderLogCard(payload);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-button bg-surface-sunken px-3 py-2">
        <span aria-hidden="true">✅</span>
        <p className="text-sm font-subheading text-text-primary">
          {card.summary}
        </p>
      </div>

      <ul className="space-y-2">
        {card.entries.map((entry, i) => (
          <li key={i} className="flex items-start gap-2.5">
            <span
              aria-hidden="true"
              className={`mt-1 grid h-4 w-4 shrink-0 place-items-center rounded-full text-[0.6rem] ${
                entry.unmatched
                  ? "bg-surface-sunken text-text-muted"
                  : "surface-accent"
              }`}
            >
              {entry.unmatched ? "?" : "✓"}
            </span>
            <div className="flex-1">
              <span className="font-subheading text-body text-text-primary">
                {entry.displayName}
              </span>
              <span className="text-sm text-text-secondary"> — {entry.detail}</span>
              {entry.unmatched && (
                <span className="ml-1.5 rounded-pill bg-surface-sunken px-1.5 py-0.5 text-xs text-text-muted">
                  unrecognised
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
