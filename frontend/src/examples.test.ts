import { afterEach, describe, expect, it, vi } from "vitest";
import { replayExample, type SavedExample } from "./examples";
import type { ChatEvent, Trace } from "./types";

const TRACE: Trace = {
  status: "done",
  steps: [],
  timeline: [{ kind: "tools", start_ms: 0, end_ms: 50 }],
  totals: {
    duration_ms: 50,
    first_token_ms: null,
    llm_calls: 0,
    input_tokens: 0,
    output_tokens: 0,
    reasoning_tokens: 0,
    tokens_complete: true,
  },
  model: { provider: "groq", name: "openai/gpt-oss-20b" },
};

const EXAMPLE: SavedExample = {
  id: "x",
  question: "Q?",
  language: "en",
  cached_example: true,
  generated_at: "2026-10-30T10:00:00+00:00",
  model: "openai/gpt-oss-20b",
  tool_calls: [{ tool: "search_documents", label: "Searching" }],
  answer: "Yes [1].",
  citations: [],
};

// Replays with reduced motion (no pauses) and returns the events in order.
async function replay(example: SavedExample): Promise<ChatEvent[]> {
  vi.stubGlobal("window", { matchMedia: () => ({ matches: true }) });
  const events: ChatEvent[] = [];
  await replayExample(example, (event) => events.push(event));
  return events;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("replayExample", () => {
  it("sends the saved trace like a live answer: after citations, before done", async () => {
    const events = await replay({ ...EXAMPLE, trace: TRACE });
    expect(events.map((e) => e.type)).toEqual(["tool_call", "token", "citations", "trace", "done"]);
    expect(events[3]).toEqual({ type: "trace", ...TRACE });
  });

  it("sends no trace for an example saved before traces existed", async () => {
    const events = await replay(EXAMPLE);
    expect(events.map((e) => e.type)).toEqual(["tool_call", "token", "citations", "done"]);
  });
});
