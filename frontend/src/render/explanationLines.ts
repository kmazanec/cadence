// Turns structured Reason triples into human-readable summary lines for the
// explanation panel.
//
// The generator emits one reason per muscle group AND per equipment item, so a
// typical 6-exercise workout produces 30+ triples. Summarization groups by
// (claim, relation) and collapses distinct `object` values into one line —
// without this step the panel would be an unreadable wall of text (ADR-012).
//
// The `note` claim is a coach-internal annotation, never surfaced to the user.

import type { Reason } from "../types/api";

/**
 * Convert a list of structured Reason triples into deduplicated, human-readable
 * summary lines suitable for the explanation panel.
 *
 * Returns an empty array when there is nothing user-relevant to show (no
 * reasons, or only `note` reasons). This is the signal for the panel to hide.
 */
export function explanationLines(reasons: Reason[]): string[] {
  // Group reasons by (claim, relation), collecting distinct non-null objects.
  const groups = new Map<string, Set<string>>();

  for (const r of reasons) {
    // Skip coach-internal annotations — they are never shown to the user.
    if (r.claim === "note") continue;
    // Reasons without an object are not renderable as a summary line.
    if (r.object === null) continue;

    const key = `${r.claim}|${r.relation}`;
    if (!groups.has(key)) {
      groups.set(key, new Set());
    }
    groups.get(key)!.add(r.object);
  }

  const lines: string[] = [];

  // Emit in a stable, user-meaningful order: exclusions first (safety-critical),
  // then pairings (notable auto-inclusions), then target matches, then equipment.
  const ORDER: [string, (objects: string[]) => string][] = [
    [
      "excluded|loads_joint",
      (objs) => `avoided ${objs.join(", ")}`,
    ],
    [
      "added|bilateral_pair_of",
      (_objs) => "paired both sides",
    ],
    [
      "included|matches_target",
      (objs) => `matched ${objs.join(", ")}`,
    ],
    [
      "matched|matches_target",
      (objs) => `matched ${objs.join(", ")}`,
    ],
    [
      "included|equipment_match",
      (objs) => `used ${objs.join(", ")}`,
    ],
  ];

  for (const [key, formatter] of ORDER) {
    const objs = groups.get(key);
    if (objs && objs.size > 0) {
      lines.push(formatter(Array.from(objs)));
    }
  }

  return lines;
}
