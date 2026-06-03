/**
 * SSE client: streams events from the /chat endpoint and calls handlers
 * for each event variant.
 *
 * Parses the raw SSE wire format (newline-separated `data: ...` frames) and
 * hands each parsed event to the caller's reducer. The variant set mirrors the
 * backend's closed union; unrecognised types are silently skipped rather than
 * crashing.
 */

import type { SSEEvent } from "../types/api";

export interface SseHandlers {
  onEvent: (event: SSEEvent) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

/**
 * POST to /chat, read the SSE stream, and call handlers for each event.
 * Returns a Promise that resolves when the stream closes.
 */
export async function streamChat(
  message: string,
  sessionId: string | null,
  handlers: SseHandlers,
): Promise<void> {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok || !response.body) {
    handlers.onError?.(new Error(`HTTP ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last (possibly incomplete) segment in the buffer.
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let event: SSEEvent;
        try {
          event = JSON.parse(raw) as SSEEvent;
        } catch {
          continue;
        }

        handlers.onEvent(event);
        if (event.type === "done") {
          handlers.onDone?.();
          return;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  handlers.onDone?.();
}
