// Mirrors the SSE events emitted by POST /chat (backend/app/main.py).

export interface Citation {
  marker: number;
  source: string;
  pages: number[] | null;
}

// One prior turn sent back to /chat as conversation history.
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; label: string }
  | { type: "citations"; citations: Citation[] }
  | { type: "done" }
  // kind "limit": a demo or provider limit was hit; message is already friendly.
  | { type: "error"; message: string; kind?: "limit" };
