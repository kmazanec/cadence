import { describe, expect, it } from "vitest";
import type { Reason } from "../types/api";
import { explanationLines } from "./explanationLines";

// Helpers to build Reason triples concisely.
function reason(
  claim: Reason["claim"],
  relation: Reason["relation"],
  subject: string,
  obj: string | null = null,
  detail: string | null = null,
): Reason {
  return { claim, relation, subject, object: obj, detail };
}

describe("explanationLines", () => {
  it("returns [] for an empty reasons array", () => {
    expect(explanationLines([])).toEqual([]);
  });

  it("returns [] when only note reasons are present", () => {
    const reasons: Reason[] = [
      reason("note", "matches_target", "Coach", "chest"),
      reason("note", "loads_joint", "Coach", "knee"),
    ];
    expect(explanationLines(reasons)).toEqual([]);
  });

  it("produces an 'avoided <joint>' line for excluded/loads_joint", () => {
    const reasons: Reason[] = [
      reason("excluded", "loads_joint", "Barbell Squat", "knee"),
    ];
    const lines = explanationLines(reasons);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatch(/avoided knee/i);
  });

  it("collapses multiple excluded/loads_joint to one line with distinct joints", () => {
    const reasons: Reason[] = [
      reason("excluded", "loads_joint", "Barbell Squat", "knee"),
      reason("excluded", "loads_joint", "Leg Press", "knee"),
      reason("excluded", "loads_joint", "Overhead Press", "shoulder"),
    ];
    const lines = explanationLines(reasons);
    // Only one excluded line summarising distinct joints.
    const excludedLines = lines.filter((l) => /avoided/i.test(l));
    expect(excludedLines).toHaveLength(1);
    // Both distinct joints appear in that line.
    expect(excludedLines[0]).toMatch(/knee/i);
    expect(excludedLines[0]).toMatch(/shoulder/i);
  });

  it("produces a 'paired both sides' line for added/bilateral_pair_of", () => {
    const reasons: Reason[] = [
      reason("added", "bilateral_pair_of", "Right Curl", "Left Curl"),
    ];
    const lines = explanationLines(reasons);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatch(/paired both sides/i);
  });

  it("produces a 'matched <targets>' line for included/matches_target", () => {
    const reasons: Reason[] = [
      reason("included", "matches_target", "Push-Up", "chest"),
    ];
    const lines = explanationLines(reasons);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatch(/matched chest/i);
  });

  it("collapses many included/matches_target to one line of distinct muscle groups", () => {
    // Simulates the per-muscle-group explosion from the generator.
    const muscles = ["chest", "back", "chest", "back", "shoulders", "chest"];
    const reasons = muscles.map((m) =>
      reason("included", "matches_target", "Push-Up", m),
    );
    const lines = explanationLines(reasons);
    const matchedLines = lines.filter((l) => /matched/i.test(l));
    expect(matchedLines).toHaveLength(1);
    // Distinct muscles appear once each.
    expect(matchedLines[0]).toMatch(/chest/i);
    expect(matchedLines[0]).toMatch(/back/i);
    expect(matchedLines[0]).toMatch(/shoulders/i);
    // No duplicates — the summary is deduplicated.
    const parts = matchedLines[0].split(",").map((s) => s.trim());
    const uniqueParts = new Set(parts);
    expect(uniqueParts.size).toBe(parts.length);
  });

  it("includes all three canonical lines when all reason types present", () => {
    const reasons: Reason[] = [
      reason("excluded", "loads_joint", "Squat", "knee"),
      reason("added", "bilateral_pair_of", "Right Curl", "Left Curl"),
      reason("included", "matches_target", "Push-Up", "chest"),
    ];
    const lines = explanationLines(reasons);
    expect(lines.some((l) => /avoided/i.test(l))).toBe(true);
    expect(lines.some((l) => /paired/i.test(l))).toBe(true);
    expect(lines.some((l) => /matched/i.test(l))).toBe(true);
  });

  it("handles reasons with null object gracefully", () => {
    const reasons: Reason[] = [
      reason("included", "matches_target", "Push-Up", null),
    ];
    // Should not throw; object-less reasons are skipped or produce a fallback line.
    expect(() => explanationLines(reasons)).not.toThrow();
  });
});
