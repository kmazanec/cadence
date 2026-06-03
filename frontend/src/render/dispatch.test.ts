import { describe, expect, it } from "vitest";
import type { ChatResponse, SSEEvent } from "../types/api";
import { initialChatState, reduceSSE, selectRender } from "./dispatch";

describe("reduceSSE", () => {
  it("handles every SSE variant", () => {
    const events: SSEEvent[] = [
      { type: "route", route: "coach" },
      { type: "token", text: "Hel" },
      { type: "token", text: "lo" },
      { type: "structured", payload: { blocks: [] } },
      { type: "clarification", question: "Which?", options: ["a", "b"] },
      { type: "done" },
      { type: "error", message: "snag" },
    ];
    const state = events.reduce(reduceSSE, initialChatState());
    expect(state.route).toBe("coach");
    expect(state.replyText).toBe("Hello");
    expect(state.structured).not.toBeNull();
    expect(state.clarification).not.toBeNull();
    expect(state.done).toBe(true);
    expect(state.error).toBe("snag");
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
