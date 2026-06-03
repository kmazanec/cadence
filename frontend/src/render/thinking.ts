// Turns the raw 'thinking' stream into readable, deemphasized progress text.
//
// Thinking arrives as a token stream from non-reply nodes. The router streams
// PARTIAL JSON of its routing decision (e.g. `{"route":"coach","confidence":
// 0.9,"rationale":"The user is asking a question..."}`); other agents stream
// plain prose. The UI must NEVER show raw JSON — so router fragments are parsed
// down to their human `rationale`, and everything else passes through as prose.
//
// The parse is tolerant of incomplete JSON: the stream is mid-flight when we
// render, so we extract the `rationale` string value even before the closing
// brace has arrived.

import type { Route } from "../types/api";

/** Accumulated raw thinking text, kept separately per source node. */
export interface ThinkingBuffers {
  /** Raw partial-JSON from the router node. */
  router: string;
  /** Raw prose from any other (subagent) node, concatenated. */
  agent: string;
}

export function emptyThinkingBuffers(): ThinkingBuffers {
  return { router: "", agent: "" };
}

/** Append a thinking fragment to the right buffer based on its source. */
export function appendThinking(
  buffers: ThinkingBuffers,
  source: string,
  text: string,
): ThinkingBuffers {
  if (source === "router") {
    return { ...buffers, router: buffers.router + text };
  }
  return { ...buffers, agent: buffers.agent + text };
}

const ROUTE_LABELS: Record<Route, string> = {
  coach: "answer your question",
  workout_generate: "build your workout",
  workout_log: "log your session",
};

/**
 * Extract a string field's value from possibly-incomplete JSON text.
 *
 * Scans for `"<field>"`, then the opening quote of its value, then reads until
 * the closing quote — honoring `\"` escapes. If the closing quote hasn't
 * streamed in yet, returns whatever has arrived so far (so the rationale can
 * render as it types). Returns null if the field/value hasn't started.
 */
export function extractJsonString(raw: string, field: string): string | null {
  const key = `"${field}"`;
  const keyAt = raw.indexOf(key);
  if (keyAt === -1) return null;

  // Find the opening quote of the value after the colon.
  let i = keyAt + key.length;
  while (i < raw.length && raw[i] !== ":") i++;
  i++; // past the colon
  while (i < raw.length && raw[i] !== '"') {
    // If we hit a non-whitespace, non-quote (e.g. `null`), there's no string.
    if (raw[i] !== " " && raw[i] !== "\t" && raw[i] !== "\n") return null;
    i++;
  }
  if (i >= raw.length) return null; // opening quote not yet streamed
  i++; // past the opening quote

  let out = "";
  while (i < raw.length) {
    const ch = raw[i];
    if (ch === "\\" && i + 1 < raw.length) {
      const next = raw[i + 1];
      // Translate the common JSON escapes; leave others as the literal char.
      out += next === "n" ? "\n" : next === "t" ? "\t" : next;
      i += 2;
      continue;
    }
    if (ch === '"') break; // closing quote — value complete
    out += ch;
    i++;
  }
  return out;
}

/** Extract the `route` enum value from partial router JSON, if present. */
export function extractRoute(raw: string): Route | null {
  const value = extractJsonString(raw, "route");
  if (
    value === "coach" ||
    value === "workout_generate" ||
    value === "workout_log"
  ) {
    return value;
  }
  return null;
}

/**
 * Render the buffered thinking into readable, deemphasized lines — never JSON.
 *
 * Produces a short ordered list of progress lines:
 * - a routing line once we know the route ("Routing to … to build your workout")
 * - the router's rationale sentence, parsed out of its JSON
 * - any subagent prose, as-is
 */
export function renderThinking(buffers: ThinkingBuffers): string[] {
  const lines: string[] = [];

  const route = extractRoute(buffers.router);
  if (route) {
    lines.push(`Routing your message to ${ROUTE_LABELS[route]}.`);
  } else if (buffers.router.length > 0) {
    // Router has started but the route field hasn't fully arrived yet.
    lines.push("Working out what you need…");
  }

  const rationale = extractJsonString(buffers.router, "rationale");
  if (rationale && rationale.trim().length > 0) {
    lines.push(rationale.trim());
  }

  // Subagent prose passes through, but some subagents (the logger) stream their
  // structured payload as "thinking" tokens — that data already renders as a
  // card, and the UI must NEVER show raw JSON. So suppress an agent buffer that
  // reads as JSON (starts with `{` or `[`) rather than prose.
  const agent = buffers.agent.trim();
  if (agent.length > 0 && !looksLikeJson(agent)) {
    lines.push(agent);
  }

  return lines;
}

/** True when the text reads as a JSON value/stream rather than prose. */
function looksLikeJson(text: string): boolean {
  return text.startsWith("{") || text.startsWith("[");
}
