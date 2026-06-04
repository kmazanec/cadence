import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { ExplanationPanel } from "./ExplanationPanel";
import type { Reason } from "../types/api";

function reason(
  claim: Reason["claim"],
  relation: Reason["relation"],
  subject: string,
  obj: string | null = null,
): Reason {
  return { claim, relation, subject, object: obj, detail: null };
}

const EXCLUDED_REASON = reason("excluded", "loads_joint", "Barbell Squat", "knee");
const INCLUDED_REASON = reason("included", "matches_target", "Push-Up", "chest");
const ADDED_REASON = reason("added", "bilateral_pair_of", "Right Curl", "Left Curl");

describe("ExplanationPanel", () => {
  it("renders nothing when reasons array is empty", () => {
    const { container } = render(<ExplanationPanel reasons={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when all reasons are note-only", () => {
    const { container } = render(
      <ExplanationPanel
        reasons={[reason("note", "matches_target", "Coach", "chest")]}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a <details> element (collapsed by default) for non-empty reasons", () => {
    const { container } = render(
      <ExplanationPanel reasons={[EXCLUDED_REASON]} />,
    );
    const details = container.querySelector("details");
    expect(details).not.toBeNull();
    // Collapsed by default — no `open` attribute.
    expect(details?.hasAttribute("open")).toBe(false);
  });

  it("shows an injury-exclusion line for an excluded/loads_joint reason", () => {
    const { container } = render(
      <ExplanationPanel reasons={[EXCLUDED_REASON]} />,
    );
    expect(container.textContent).toMatch(/avoided knee/i);
  });

  it("shows 'paired both sides' for an added/bilateral_pair_of reason", () => {
    const { container } = render(
      <ExplanationPanel reasons={[ADDED_REASON]} />,
    );
    expect(container.textContent).toMatch(/paired both sides/i);
  });

  it("shows a target-match line for included/matches_target", () => {
    const { container } = render(
      <ExplanationPanel reasons={[INCLUDED_REASON]} />,
    );
    expect(container.textContent).toMatch(/matched chest/i);
  });

  it("renders all three canonical reason types when present", () => {
    const { container } = render(
      <ExplanationPanel
        reasons={[EXCLUDED_REASON, ADDED_REASON, INCLUDED_REASON]}
      />,
    );
    expect(container.textContent).toMatch(/avoided knee/i);
    expect(container.textContent).toMatch(/paired both sides/i);
    expect(container.textContent).toMatch(/matched chest/i);
  });

  it("has a summary element for the disclosure affordance", () => {
    const { container } = render(
      <ExplanationPanel reasons={[EXCLUDED_REASON]} />,
    );
    const summary = container.querySelector("summary");
    expect(summary).not.toBeNull();
    expect(summary?.textContent).toMatch(/why these/i);
  });
});
