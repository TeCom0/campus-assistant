// Mirrors the SSE events emitted by POST /chat (backend/app/main.py).

export interface Citation {
  marker: number;
  source: string;
  pages: number[] | null;
}

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; label: string }
  | { type: "citations"; citations: Citation[] }
  | { type: "done" }
  | { type: "error"; message: string };
