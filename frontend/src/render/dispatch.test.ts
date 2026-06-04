import { describe, expect, it } from "vitest";
import type { ChatResponse, SSEEvent } from "../types/api";
import { initialChatState, reduceSSE, selectRender } from "./dispatch";

describe("reduceSSE", () => {
  it("handles every SSE variant", () => {
    const events: SSEEvent[] = [
      { type: "route", route: "coach" },
      { type: "token", text: "Hel" },
      { type: "token", text: "lo" },
      { type: "thinking", source: "router", text: "rou" },
      { type: "thinking", source: "router", text: "ting" },
      { type: "structured", payload: { blocks: [] } },
      {
        type: "explanation",
        reasons: [
          {
            claim: "excluded",
            relation: "loads_joint",
            subject: "Barbell Squat",
            object: "knee",
            detail: null,
          },
        ],
      },
      { type: "clarification", question: "Which?", options: ["a", "b"] },
      { type: "done" },
      { type: "error", message: "snag" },
    ];
    const state = events.reduce(reduceSSE, initialChatState());
    expect(state.route).toBe("coach");
    expect(state.replyText).toBe("Hello");
    expect(state.structured).not.toBeNull();
    expect(state.explanation).toHaveLength(1);
    expect(state.explanation[0].claim).toBe("excluded");
    expect(state.clarification).not.toBeNull();
    expect(state.done).toBe(true);
    expect(state.error).toBe("snag");
  });

  it("stores explanation reasons from explanation event", () => {
    const events: SSEEvent[] = [
      { type: "route", route: "workout_generate" },
      {
        type: "explanation",
        reasons: [
          {
            claim: "excluded",
            relation: "loads_joint",
            subject: "Barbell Squat",
            object: "knee",
            detail: null,
          },
          {
            claim: "added",
            relation: "bilateral_pair_of",
            subject: "Right Curl",
            object: "Left Curl",
            detail: null,
          },
        ],
      },
      { type: "done" },
    ];
    const state = events.reduce(reduceSSE, initialChatState());
    expect(state.explanation).toHaveLength(2);
    expect(state.explanation[0].claim).toBe("excluded");
    expect(state.explanation[1].claim).toBe("added");
  });

  it("initialChatState has empty explanation array", () => {
    const state = initialChatState();
    expect(state.explanation).toEqual([]);
  });

  it("parses router thinking into readable lines, never raw JSON", () => {
    const events: SSEEvent[] = [
      { type: "thinking", source: "router", text: '{"route":"coach"' },
      { type: "thinking", source: "router", text: ',"confidence":0.9,' },
      {
        type: "thinking",
        source: "router",
        text: '"rationale":"The user is asking a question."}',
      },
      { type: "token", text: "The answer." },
    ];
    const state = events.reduce(reduceSSE, initialChatState());
    const joined = state.thinkingLines.join("\n");
    // No raw JSON braces/keys leak into the displayed thinking.
    expect(joined).not.toContain("{");
    expect(joined).not.toContain('"route"');
    expect(joined).not.toContain("confidence");
    // The human rationale and a routing line are surfaced.
    expect(joined).toContain("The user is asking a question.");
    expect(state.thinkingLines.some((l) => /answer your question/i.test(l))).toBe(
      true,
    );
    // The reply itself is unaffected by thinking.
    expect(state.replyText).toBe("The answer.");
  });
});

describe("selectRender", () => {
  const base: ChatResponse = {
    route: null,
    reply_text: "",
    structured: null,
    explanation: [],
    clarification: null,
  };

  it("renders a card per route", () => {
    expect(selectRender({ ...base, route: "coach" })).toBe("coach-text");
    expect(selectRender({ ...base, route: "workout_generate" })).toBe(
      "workout-card",
    );
    expect(selectRender({ ...base, route: "workout_log" })).toBe("log-card");
  });

  it("renders clarification when present", () => {
    expect(
      selectRender({
        ...base,
        clarification: { question: "Which?", options: ["a"] },
      }),
    ).toBe("clarification");
  });

  it("renders empty for a null route with no clarification", () => {
    expect(selectRender(base)).toBe("empty");
  });
});
