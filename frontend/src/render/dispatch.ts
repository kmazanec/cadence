// Exhaustive consumers of the wire unions: the SSE reducer and the per-route /
// per-event render selectors. Each switch ends in a `never` check so adding a
// variant without handling it fails the type-check rather than slipping
// through at runtime.

import type {
  ChatResponse,
  Reason,
  Route,
  SSEEvent,
  StructuredPayload,
} from "../types/api";
import {
  appendThinking,
  emptyThinkingBuffers,
  renderThinking,
  type ThinkingBuffers,
} from "./thinking";

function assertNever(value: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(value)}`);
}

// What the chat view holds as a turn streams in.
export interface ChatState {
  route: Route | null;
  replyText: string;
  // Raw 'thinking' fragments, kept per-source so router JSON and subagent prose
  // can be parsed apart. Never displayed directly — see `thinkingLines`.
  thinking: ThinkingBuffers;
  // Human-readable, deemphasized progress lines derived from `thinking`. This is
  // what the UI shows; it never contains raw JSON. Persists after the answer.
  thinkingLines: string[];
  structured: StructuredPayload | null;
  // Structured reasons the agent produced this turn (workout turns only).
  explanation: Reason[];
  clarification: { question: string; options: string[] } | null;
  error: string | null;
  done: boolean;
}

export function initialChatState(): ChatState {
  return {
    route: null,
    replyText: "",
    thinking: emptyThinkingBuffers(),
    thinkingLines: [],
    structured: null,
    explanation: [],
    clarification: null,
    error: null,
    done: false,
  };
}

// Reduce one SSE event into chat state. Exhaustive over all variants.
export function reduceSSE(state: ChatState, event: SSEEvent): ChatState {
  switch (event.type) {
    case "route":
      return { ...state, route: event.route };
    case "token":
      return { ...state, replyText: state.replyText + event.text };
    case "thinking": {
      const thinking = appendThinking(state.thinking, event.source, event.text);
      return { ...state, thinking, thinkingLines: renderThinking(thinking) };
    }
    case "structured":
      return { ...state, structured: event.payload };
    case "explanation":
      return { ...state, explanation: event.reasons };
    case "clarification":
      return {
        ...state,
        clarification: { question: event.question, options: event.options },
      };
    case "done":
      return { ...state, done: true };
    case "error":
      return { ...state, error: event.message };
    default:
      return assertNever(event);
  }
}

// Which card a structured payload renders as, switched on the route. Handles a
// null route (clarification turn) and a null structured payload (coach turn).
export type RenderKind =
  | "coach-text"
  | "workout-card"
  | "log-card"
  | "clarification"
  | "empty";

export function selectRender(response: ChatResponse): RenderKind {
  if (response.clarification !== null) {
    return "clarification";
  }
  if (response.route === null) {
    return "empty";
  }
  switch (response.route) {
    case "coach":
      return "coach-text";
    case "workout_generate":
      return "workout-card";
    case "workout_log":
      return "log-card";
    default:
      return assertNever(response.route);
  }
}
