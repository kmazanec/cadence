import { describe, expect, it } from "vitest";
import {
  appendThinking,
  emptyThinkingBuffers,
  extractJsonString,
  extractRoute,
  renderThinking,
} from "./thinking";

describe("extractJsonString", () => {
  it("reads a complete string field", () => {
    expect(extractJsonString('{"rationale":"hello there"}', "rationale")).toBe(
      "hello there",
    );
  });

  it("reads a partial value before the closing quote arrives", () => {
    // Mid-stream: the rationale is still typing, no closing quote yet.
    expect(extractJsonString('{"rationale":"hello the', "rationale")).toBe(
      "hello the",
    );
  });

  it("returns null when the field hasn't appeared", () => {
    expect(extractJsonString('{"route":"coach"', "rationale")).toBeNull();
  });

  it("returns null for a non-string (null) value", () => {
    expect(extractJsonString('{"clarification":null}', "clarification")).toBeNull();
  });

  it("honors escaped quotes inside the value", () => {
    expect(
      extractJsonString('{"rationale":"a \\"quoted\\" word"}', "rationale"),
    ).toBe('a "quoted" word');
  });
});

describe("extractRoute", () => {
  it("extracts a known route", () => {
    expect(extractRoute('{"route":"workout_generate"')).toBe("workout_generate");
  });
  it("returns null for an unknown/partial route", () => {
    expect(extractRoute('{"route":"wor')).toBeNull();
  });
});

describe("renderThinking", () => {
  it("never emits raw JSON and surfaces the rationale + routing line", () => {
    let b = emptyThinkingBuffers();
    for (const frag of [
      '{"route":"coach",',
      '"confidence":0.95,',
      '"rationale":"It is a question about an exercise."}',
    ]) {
      b = appendThinking(b, "router", frag);
    }
    const lines = renderThinking(b);
    const joined = lines.join("\n");
    expect(joined).not.toMatch(/[{}"]/);
    expect(joined).toContain("It is a question about an exercise.");
    expect(lines.some((l) => /answer your question/i.test(l))).toBe(true);
  });

  it("passes subagent prose through as-is", () => {
    let b = emptyThinkingBuffers();
    b = appendThinking(b, "generate", "Selecting exercises that fit dumbbells.");
    const lines = renderThinking(b);
    expect(lines).toContain("Selecting exercises that fit dumbbells.");
  });

  it("suppresses a subagent buffer that streams raw JSON (e.g. the logger)", () => {
    // The logger streams its structured payload as 'thinking' tokens; that data
    // renders as a card, so it must not leak into the thinking trace as JSON.
    let b = emptyThinkingBuffers();
    b = appendThinking(
      b,
      "log",
      '{"entries":[{"raw_name":"bench press","sets":3}]}{"pick":1}',
    );
    const lines = renderThinking(b);
    expect(lines.join("\n")).not.toMatch(/[{}[\]]/);
  });

  it("shows a holding line before the route field finishes streaming", () => {
    let b = emptyThinkingBuffers();
    b = appendThinking(b, "router", '{"rou');
    const lines = renderThinking(b);
    expect(lines.length).toBeGreaterThan(0);
    expect(lines.join("\n")).not.toContain("{");
  });
});
