import { describe, expect, it } from "vitest";
import type { LogEntry, LogPayload } from "../types/api";
import { renderLogCard, renderLogEntry } from "./LogCard";

const makeEntry = (overrides: Partial<LogEntry> = {}): LogEntry => ({
  session_id: "s1",
  exercise_id: "ex-01",
  raw_name: "Barbell Decline Bench Press",
  sets: 3,
  reps: 10,
  weight: 185,
  unmatched: false,
  logged_at: "2026-06-02T12:00:00Z",
  ...overrides,
});

describe("renderLogEntry", () => {
  it("formats a matched entry with sets, reps, and weight", () => {
    const rendered = renderLogEntry(makeEntry());
    expect(rendered.displayName).toBe("Barbell Decline Bench Press");
    expect(rendered.detail).toContain("3");
    expect(rendered.detail).toContain("10");
    expect(rendered.detail).toContain("185");
    expect(rendered.unmatched).toBe(false);
  });

  it("flags an unmatched entry and shows raw name", () => {
    const rendered = renderLogEntry(
      makeEntry({
        raw_name: "zercher good-mornings",
        exercise_id: null,
        unmatched: true,
      }),
    );
    expect(rendered.displayName).toBe("zercher good-mornings");
    expect(rendered.unmatched).toBe(true);
  });

  it("omits weight when not present", () => {
    const rendered = renderLogEntry(makeEntry({ weight: null }));
    expect(rendered.detail).not.toContain("lbs");
    expect(rendered.detail).not.toContain("null");
  });

  it("handles null sets and reps gracefully", () => {
    const rendered = renderLogEntry(makeEntry({ sets: null, reps: null }));
    expect(rendered.detail).toBeTruthy();
    expect(rendered.displayName).toBeTruthy();
  });
});

describe("renderLogCard", () => {
  const payload: LogPayload = {
    entries: [
      makeEntry(),
      makeEntry({
        raw_name: "zercher good-mornings",
        exercise_id: null,
        unmatched: true,
        weight: null,
      }),
    ],
  };

  it("returns a card with all entries rendered", () => {
    const card = renderLogCard(payload);
    expect(card.entries).toHaveLength(2);
  });

  it("matched count counts only resolved entries", () => {
    const card = renderLogCard(payload);
    expect(card.matchedCount).toBe(1);
    expect(card.unmatchedCount).toBe(1);
  });

  it("has a human-readable summary line", () => {
    const card = renderLogCard(payload);
    expect(typeof card.summary).toBe("string");
    expect(card.summary.length).toBeGreaterThan(0);
  });
});
