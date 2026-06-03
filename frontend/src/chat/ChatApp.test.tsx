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
});
