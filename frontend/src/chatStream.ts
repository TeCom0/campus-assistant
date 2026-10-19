import type { ChatEvent, HistoryMessage } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

// Splits a buffer of SSE text into complete events plus any trailing partial
// frame. SSE frames are separated by a blank line; a network chunk can end
// mid-frame, so the incomplete tail is returned to be completed by later text.
export function parseSse(buffer: string): { events: ChatEvent[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const frames = normalized.split("\n\n");
  const rest = frames.pop() ?? "";

  const events: ChatEvent[] = [];
  for (const frame of frames) {
    let eventName = "";
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).trim());
      }
    }
    if (!eventName) continue;

    const payload = JSON.parse(dataLines.join("\n") || "{}");
    events.push({ type: eventName, ...payload } as ChatEvent);
  }
  return { events, rest };
}

// The demo refused the question (HTTP 429: daily cap or per-IP limit). The
// server's message is friendly and already in the question's language.
export class LimitError extends Error {}

// POST /chat and call onEvent for each event as it arrives. EventSource can't
// be used here: it only supports GET, and /chat needs a POST with a JSON body.
export async function streamChat(
  question: string,
  history: HistoryMessage[],
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, messages: history }),
  });
  if (response.status === 429) {
    const body = await response.json().catch(() => ({}));
    throw new LimitError(body.message ?? "The demo limit was reached. Please try again later.");
  }
  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed with HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSse(buffer);
    buffer = parsed.rest;
    parsed.events.forEach(onEvent);
  }

  buffer += decoder.decode();
  parseSse(buffer + "\n\n").events.forEach(onEvent);
}
