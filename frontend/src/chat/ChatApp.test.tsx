import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import ChatApp from "./ChatApp";

// Minimal fetch mock for SSE streaming
function makeSseResponse(lines: string[]): Response {
  const body = lines.join("\n") + "\n";
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body));
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "content-type": "text/event-stream" },
  });
}

describe("ChatApp", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the chat input and title", () => {
    render(<ChatApp />);
    expect(screen.getByRole("textbox")).toBeDefined();
    // The page should show the product name
    expect(document.body.textContent).toContain("Cadence");
  });

  it("sends a message and shows streaming reply", async () => {
    const events = [
      `data: ${JSON.stringify({ type: "route", route: "coach" })}`,
      `data: ${JSON.stringify({ type: "token", text: "Hello " })}`,
      `data: ${JSON.stringify({ type: "token", text: "there!" })}`,
      `data: ${JSON.stringify({ type: "done" })}`,
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeSseResponse(events));

    render(<ChatApp />);
    const input = screen.getByRole("textbox");
    await act(async () => {
      fireEvent.change(input, { target: { value: "What is a squat?" } });
      fireEvent.submit(input.closest("form")!);
    });

    await waitFor(() => {
      expect(document.body.textContent).toContain("Hello there!");
    });
  });

  it("clears input after submission", async () => {
    const events = [`data: ${JSON.stringify({ type: "done" })}`];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeSseResponse(events));

    render(<ChatApp />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    await act(async () => {
      fireEvent.change(input, { target: { value: "test message" } });
      fireEvent.submit(input.closest("form")!);
    });

    await waitFor(() => expect(input.value).toBe(""));
  });

  it("shows user message in the chat log", async () => {
    const events = [`data: ${JSON.stringify({ type: "done" })}`];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeSseResponse(events));

    render(<ChatApp />);
    await act(async () => {
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: "My test question" },
      });
      fireEvent.submit(screen.getByRole("textbox").closest("form")!);
    });

    await waitFor(() => {
      expect(document.body.textContent).toContain("My test question");
    });
  });

  it("renders the explanation panel when an explanation event is present", async () => {
    const events = [
      `data: ${JSON.stringify({ type: "route", route: "workout_generate" })}`,
      `data: ${JSON.stringify({
        type: "structured",
        payload: { blocks: [] },
      })}`,
      `data: ${JSON.stringify({
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
      })}`,
      `data: ${JSON.stringify({ type: "done" })}`,
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeSseResponse(events));

    render(<ChatApp />);
    await act(async () => {
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: "chest workout, bad knee" },
      });
      fireEvent.submit(screen.getByRole("textbox").closest("form")!);
    });

    await waitFor(() => {
      // The explanation panel summary and the exclusion line must be visible.
      expect(document.body.textContent).toContain("Why these?");
      expect(document.body.textContent).toMatch(/avoided knee/i);
    });
  });

  it("does not render the explanation panel on a coach turn", async () => {
    const events = [
      `data: ${JSON.stringify({ type: "route", route: "coach" })}`,
      `data: ${JSON.stringify({ type: "token", text: "Great question!" })}`,
      `data: ${JSON.stringify({ type: "done" })}`,
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeSseResponse(events));

    render(<ChatApp />);
    await act(async () => {
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: "What muscles does a squat work?" },
      });
      fireEvent.submit(screen.getByRole("textbox").closest("form")!);
    });

    await waitFor(() => {
      expect(document.body.textContent).toContain("Great question!");
    });

    // The explanation panel must not appear on a coach turn.
    expect(document.body.textContent).not.toContain("Why these?");
  });
});
