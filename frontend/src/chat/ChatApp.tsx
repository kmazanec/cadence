/**
 * The main chat view: message log, input form, and SSE streaming integration.
 *
 * Every color, font, and spacing value comes from the Tailwind brand tokens
 * defined in tailwind.config.js — no ad-hoc values in this component.
 */

import { useState, useRef, useEffect } from "react";
import { initialChatState, reduceSSE } from "../render/dispatch";
import { streamChat } from "./sseClient";
import { WorkoutCardView } from "../render/WorkoutCardView";
import { LogCardView } from "../render/LogCardView";
import type { Reason, Route, SSEEvent, StructuredPayload } from "../types/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  route?: Route | null;
  // Human-readable thinking lines (never raw JSON). Persist after the answer.
  thinkingLines?: string[];
  structured?: StructuredPayload | null;
  // Structured reasons from the agent (workout turns only).
  explanation?: Reason[];
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
            thinkingLines: chatState.thinkingLines,
            structured: chatState.structured,
            explanation: chatState.explanation,
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

          {messages.map((msg, i) => {
            // What the assistant turn has produced so far.
            const hasReply = !!msg.content;
            const hasCard = !!msg.structured;
            const thinkingLines = msg.thinkingLines ?? [];
            const hasThinking =
              msg.role === "assistant" && thinkingLines.length > 0;
            // Nothing has streamed in yet — show a bare placeholder.
            const isEmpty =
              msg.role === "assistant" &&
              !hasReply &&
              !hasCard &&
              !hasThinking;

            return (
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
                  {/* Deemphasized 'thinking' trace — parsed, never raw JSON.
                      Stays visible above the answer after it arrives. */}
                  {hasThinking && (
                    <div className="mb-2 border-l-2 border-border pl-3 space-y-0.5">
                      <p className="text-xs font-subheading uppercase tracking-wide text-text-secondary opacity-70">
                        Thinking
                      </p>
                      {thinkingLines.map((line, li) => (
                        <p
                          key={li}
                          className="text-sm italic text-text-secondary opacity-70 whitespace-pre-wrap"
                        >
                          {line}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Workout / log cards render the structured payload. */}
                  {msg.structured && msg.route === "workout_generate" && (
                    <WorkoutCardView
                      payload={msg.structured as Parameters<typeof WorkoutCardView>[0]["payload"]}
                      reasons={msg.explanation ?? []}
                    />
                  )}
                  {msg.structured && msg.route === "workout_log" && (
                    <LogCardView
                      payload={msg.structured as Parameters<typeof LogCardView>[0]["payload"]}
                    />
                  )}

                  {/* The conversational reply (coach). */}
                  {hasReply && (
                    <p className="text-body whitespace-pre-wrap">{msg.content}</p>
                  )}

                  {/* Bare placeholder before anything has streamed in. */}
                  {isEmpty && msg.isStreaming && (
                    <span className="text-text-secondary text-sm">Thinking…</span>
                  )}
                </div>
              </div>
            );
          })}

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
