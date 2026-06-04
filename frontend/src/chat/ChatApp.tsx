/**
 * The main chat view: branded chrome, message log, and the composer, wired to
 * the SSE stream.
 *
 * Visual language ("Cadence — find your rhythm", energetic & athletic on a
 * bright canvas) is documented in BRAND.md. Every color, font, radius, and
 * shadow comes from the Tailwind brand tokens in tailwind.config.js — no ad-hoc
 * values live in this component.
 */

import { useState, useRef, useEffect } from "react";
import { initialChatState, reduceSSE } from "../render/dispatch";
import { streamChat } from "./sseClient";
import { WorkoutCardView } from "../render/WorkoutCardView";
import { LogCardView } from "../render/LogCardView";
import { AppHeader } from "../chrome/AppHeader";
import { QuickActions } from "../chrome/QuickActions";
import { CadenceMark } from "../brand/CadenceMark";
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

/** Animated tempo bars — the "Cadence is thinking" beat. */
function TempoBars() {
  return (
    <span className="inline-flex items-end gap-0.5" aria-hidden="true">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className="h-3.5 w-1 origin-bottom rounded-full bg-accent-deep animate-tempo-bounce"
          style={{ animationDelay: `${i * 0.12}s` }}
        />
      ))}
    </span>
  );
}

/** A short label for each route, shown as a tag on the assistant turn. */
const ROUTE_TAG: Record<Route, { label: string; icon: string }> = {
  coach: { label: "Coach", icon: "💬" },
  workout_generate: { label: "Workout", icon: "🏋️" },
  workout_log: { label: "Logged", icon: "✅" },
};

export default function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to the latest message as it streams (no-op in test environments).
  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setInput("");
    setIsLoading(true);

    // Add the user message immediately, plus a placeholder assistant reply.
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
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

    void streamChat(trimmed, sessionId, {
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
              content:
                "Something tripped up on my end — give it another go and we'll pick up right where we left off.",
              isStreaming: false,
            };
          }
          return next;
        });
        setIsLoading(false);
      },
    }).catch(() => setIsLoading(false));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  // Quick-action chips and the empty-state prompts prefill + focus the composer.
  function prefill(prompt: string) {
    setInput(prompt);
    inputRef.current?.focus();
  }

  // Enter sends; Shift+Enter makes a newline.
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const isEmptyConversation = messages.length === 0;

  return (
    <div className="flex h-screen flex-col font-sans text-text-primary">
      <AppHeader />

      {/* Message log */}
      <main className="scroll-cadence flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl">
          {isEmptyConversation ? (
            <EmptyState onPick={prefill} disabled={isLoading} />
          ) : (
            <div className="space-y-5">
              {messages.map((msg, i) => (
                <MessageBubble key={i} msg={msg} />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Composer */}
      <footer className="shrink-0 border-t border-border bg-canvas/80 px-4 pb-5 pt-4 backdrop-blur-sm">
        <div className="mx-auto max-w-3xl">
          {!isEmptyConversation && (
            <div className="mb-3">
              <QuickActions onPick={prefill} disabled={isLoading} />
            </div>
          )}
          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-2 rounded-card border border-border-strong bg-surface p-2 shadow-card transition-shadow focus-within:border-accent-deep focus-within:shadow-card-hover"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question, request a workout, or log your session…"
              disabled={isLoading}
              className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-body leading-relaxed text-text-primary placeholder:text-text-muted focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              aria-label="Send message"
              className="group grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-button surface-accent shadow-glow transition-all hover:scale-105 active:scale-95 disabled:scale-100 disabled:opacity-40 disabled:shadow-none"
            >
              {isLoading ? (
                <TempoBars />
              ) : (
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5 text-accent-ink transition-transform group-hover:translate-x-0.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M5 12h13M13 6l6 6-6 6" />
                </svg>
              )}
            </button>
          </form>
          <p className="mt-2 text-center text-xs text-text-muted">
            Cadence can build workouts, log sessions, and answer training
            questions. Press Enter to send.
          </p>
        </div>
      </footer>
    </div>
  );
}

/** The first-run hero: big welcome, the brand mark, and the three ways in. */
function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (prompt: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col items-center px-2 py-12 text-center sm:py-20 animate-rise-in">
      <span className="mb-6 grid h-16 w-16 place-items-center rounded-card bg-ink text-accent-volt shadow-glow">
        <CadenceMark size={40} strokeWidth={3} animated />
      </span>
      <h2 className="max-w-xl font-heading text-section text-ink">
        Let&apos;s build something today.
      </h2>
      <p className="mt-3 max-w-md text-body text-text-secondary">
        I&apos;m your training partner — I can program a workout, log what you
        did, or talk through anything on your mind. Pick a starting point:
      </p>
      <div className="mt-8 flex justify-center">
        <QuickActions onPick={onPick} disabled={disabled} />
      </div>
    </div>
  );
}

/** One turn in the log: user bubble, or the assistant's tagged card. */
function MessageBubble({ msg }: { msg: Message }) {
  const hasReply = !!msg.content;
  const hasCard = !!msg.structured;
  const thinkingLines = msg.thinkingLines ?? [];
  const hasThinking = msg.role === "assistant" && thinkingLines.length > 0;
  const isEmpty =
    msg.role === "assistant" && !hasReply && !hasCard && !hasThinking;

  if (msg.role === "user") {
    return (
      <div className="flex justify-end animate-rise-in">
        <div className="max-w-[82%] rounded-card rounded-br-md surface-accent px-card py-2.5 text-body font-medium shadow-glow">
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>
      </div>
    );
  }

  const tag = msg.route ? ROUTE_TAG[msg.route] : null;

  return (
    <div className="flex justify-start gap-2.5 animate-rise-in">
      {/* Coach avatar — the brand mark in a chip. */}
      <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-button bg-ink text-accent-volt">
        <CadenceMark size={18} strokeWidth={3} animated={msg.isStreaming} />
      </span>

      <div className="max-w-[82%] rounded-card rounded-tl-md border border-border bg-surface px-card py-3 shadow-card">
        {/* Route tag — which specialist answered. */}
        {tag && (
          <span className="mb-2 inline-flex items-center gap-1 rounded-pill bg-surface-sunken px-2 py-0.5 text-[0.7rem] font-subheading uppercase tracking-wide text-accent-deep">
            <span aria-hidden="true">{tag.icon}</span>
            {tag.label}
          </span>
        )}

        {/* Deemphasized 'thinking' trace — parsed, never raw JSON. */}
        {hasThinking && (
          <div className="mb-2 border-l-2 border-accent-volt pl-3">
            <p className="mb-0.5 text-[0.7rem] font-subheading uppercase tracking-wide text-text-muted">
              Thinking
            </p>
            {thinkingLines.map((line, li) => (
              <p
                key={li}
                className="whitespace-pre-wrap text-sm italic text-text-secondary"
              >
                {line}
              </p>
            ))}
          </div>
        )}

        {/* Structured workout / log cards. */}
        {msg.structured && msg.route === "workout_generate" && (
          <WorkoutCardView
            payload={
              msg.structured as Parameters<typeof WorkoutCardView>[0]["payload"]
            }
            reasons={msg.explanation ?? []}
          />
        )}
        {msg.structured && msg.route === "workout_log" && (
          <LogCardView
            payload={
              msg.structured as Parameters<typeof LogCardView>[0]["payload"]
            }
          />
        )}

        {/* The conversational reply (coach). */}
        {hasReply && (
          <p className="whitespace-pre-wrap text-body">{msg.content}</p>
        )}

        {/* Placeholder before anything has streamed in. */}
        {isEmpty && msg.isStreaming && (
          <span className="flex items-center gap-2 text-sm text-text-secondary">
            <TempoBars />
            Finding your rhythm…
          </span>
        )}
      </div>
    </div>
  );
}
