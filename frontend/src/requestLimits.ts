import type { HistoryMessage } from "./types";

// What the API accepts on /chat (backend/app/config.py; a backend test checks
// these are the same numbers). The server refuses anything over them, so what
// the UI sends must never go over them.
export const MAX_BODY_BYTES = 65536; // 64 KiB
export const MAX_QUESTION_CHARS = 2000;
export const MAX_REQUEST_MESSAGES = 20;
export const MAX_USER_CONTENT_CHARS = 2000;
export const MAX_ASSISTANT_CONTENT_CHARS = 6000;

// The composer starts showing a counter at 90% of the limit.
export const COUNTER_FROM_CHARS = 1800;

// Characters as the server counts them (Python's len: code points). JavaScript's
// .length counts an emoji as 2.
export function charCount(text: string): number {
  return [...text].length;
}

// The one place the request body is written, so what historyToSend() measures
// is exactly what streamChat() sends.
export function chatRequestBody(question: string, messages: HistoryMessage[]): string {
  return JSON.stringify({ question, messages });
}

// Bytes, not characters: "é" is 2 bytes, and JSON writes a newline as 2 characters.
function bodyBytes(question: string, messages: HistoryMessage[]): number {
  return new TextEncoder().encode(chatRequestBody(question, messages)).length;
}

// A turn is a question and its answer. An interrupted answer isn't in the
// history at all, so its turn is the question alone.
function toTurns(history: HistoryMessage[]): HistoryMessage[][] {
  const turns: HistoryMessage[][] = [];
  for (const message of history) {
    if (message.role === "user" || turns.length === 0) turns.push([message]);
    else turns[turns.length - 1].push(message);
  }
  return turns;
}

function withinFieldLimits(turn: HistoryMessage[]): boolean {
  return turn.every((message) => {
    const limit = message.role === "user" ? MAX_USER_CONTENT_CHARS : MAX_ASSISTANT_CONTENT_CHARS;
    return charCount(message.content) <= limit;
  });
}

// The prior turns to send with a question: the newest ones that fit under the
// server's limits. It drops whole turns, oldest first, never a single message:
// an answer without its question, or the reverse, would misrepresent the
// conversation to the model. A turn over a field limit is left out whole too.
export function historyToSend(question: string, history: HistoryMessage[]): HistoryMessage[] {
  const turns = toTurns(history).filter(withinFieldLimits);
  let kept: HistoryMessage[] = [];
  for (let i = turns.length - 1; i >= 0; i--) {
    const candidate = [...turns[i], ...kept];
    if (candidate.length > MAX_REQUEST_MESSAGES) break;
    if (bodyBytes(question, candidate) > MAX_BODY_BYTES) break;
    kept = candidate;
  }
  return kept;
}
