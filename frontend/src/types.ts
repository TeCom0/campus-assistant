// Mirrors the SSE events emitted by POST /chat (backend/app/main.py).

export interface Citation {
  marker: number;
  source: string;
  pages: number[] | null;
  // Added for the UI by backend/app/sources.py.
  title: string; // "Academic Catalog 2024–2025"
  section: string | null; // "Undergraduate Studies › Repeat Policy"
  link: string | null; // API path (/sources/...): the PDF at the page, or a fallback page
}

// One prior turn sent back to /chat as conversation history.
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

// Which demo limit refused a question (backend/app/limits.py).
export type LimitKind = "daily_cap" | "per_ip" | "busy";

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; label: string }
  | { type: "citations"; citations: Citation[] }
  | { type: "done" }
  // kind "limit": a demo or provider limit was hit; title and message are friendly.
  | { type: "error"; message: string; kind?: "limit"; limit?: LimitKind; title?: string };
