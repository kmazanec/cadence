/**
 * The main chat view: message log, input form, and SSE streaming integration.
 *
 * Every color, font, and spacing value comes from the Tailwind brand tokens
 * defined in tailwind.config.js — no ad-hoc values in this component.
 */

import { useState, useRef, useEffect } from "react";
import { initialChatState, reduceSSE } from "../render/dispatch";
import { streamChat } from "./sseClient";
import type { Route, SSEEvent } from "../types/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  route?: Route | null;
  isStreaming?: boolean;
}

export default function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to the latest message as it streams (no-op in test environments).
  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    setIsLoading(true);

    // Add the user message immediately.
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    // Add a placeholder for the assistant reply.
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", isStreaming: true },
    ]);

    let chatState = initialChatState();

    const handleEvent = (event: SSEEvent) => {
      chatState = reduceSSE(chatState, event);
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          next[next.length - 1] = {
            ...last,
            content: chatState.replyText,
            route: chatState.route,
          };
        }
        return next;
      });
    };

    try {
      await streamChat(text, sessionId, {
        onEvent: handleEvent,
        onDone: () => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = { ...last, isStreaming: false };
            }
            return next;
          });
          setIsLoading(false);
        },
        onError: () => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                content: "Something went wrong — please try again.",
                isStreaming: false,
              };
            }
            return next;
          });
          setIsLoading(false);
        },
      });
    } catch {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background font-sans">
      {/* Header */}
      <header className="border-b border-border bg-surface px-6 py-4 shrink-0">
        <h1 className="text-xl font-heading text-text-primary tracking-tight">
          Cadence
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Your fitness training partner
        </p>
      </header>

      {/* Message log */}
      <main className="flex-1 overflow-y-auto px-4 py-section">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <p className="text-text-secondary text-body">
                Ask a fitness question, request a workout, or log what you did.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`rounded-card px-card py-3 max-w-[80%] ${
                  msg.role === "user"
                    ? "bg-accent text-white"
                    : "bg-surface border border-border text-text-primary"
                }`}
              >
                {msg.content ? (
                  <p className="text-body whitespace-pre-wrap">{msg.content}</p>
                ) : msg.isStreaming ? (
                  <span className="text-text-secondary text-sm">
                    Thinking…
                  </span>
                ) : null}
              </div>
            </div>
          ))}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input form */}
      <footer className="border-t border-border bg-surface px-4 py-4 shrink-0">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question, request a workout, or log your session…"
              disabled={isLoading}
              className="flex-1 rounded-button border border-border bg-background px-4 py-2.5 text-body text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="rounded-button bg-accent px-6 py-2.5 text-sm font-subheading text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
            >
              Send
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
}
