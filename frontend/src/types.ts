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

// The "Under the hood" trace (backend/app/agent/trace.py: RunTrace.event,
// what the tools record, and the display info main.py adds). Display only:
// the evaluation never reads it.

// One phrasing a search used. origins: what it stands for ("query",
// "query_en", "question"); as_written is the first of them before the
// university's name was stripped.
export interface Phrasing {
  text: string;
  origins: ("query" | "query_en" | "question")[];
  as_written: string;
}

// One passage of a search's top 5, fused by reciprocal rank fusion.
export interface RankedPassage {
  rank: number;
  marker: number;
  new: boolean; // false: already returned by an earlier search
  source: string;
  pages: number[] | null;
  title: string;
  section: string | null;
  snippet: string;
  rrf_score: number;
  vector_rank: number | null; // best rank across phrasings; null: in no vector list
  keyword_rank: number | null;
}

export interface SearchStep {
  tool: "search_documents";
  call_id: string | null;
  args: { query: string; query_en: string };
  phrasings: Phrasing[];
  ranked_lists: number;
  max_rrf_score: number;
  results: RankedPassage[];
  duration_ms: number;
}

export interface CourseStep {
  tool: "query_courses";
  call_id: string | null;
  args: { code: string; follow_prerequisites: boolean };
  found: "course" | "no_description" | "not_found";
  marker?: number;
  title?: string | null;
  pages?: number[] | null;
  chain_length?: number | null; // null: chain not looked up
  duration_ms: number;
}

export type TraceStep = SearchStep | CourseStep;

export type Segment =
  | {
      kind: "llm";
      start_ms: number;
      end_ms: number;
      tool_calls: string[];
      input_tokens: number | null;
      output_tokens: number | null;
      reasoning_tokens: number | null;
    }
  | { kind: "tools" | "fallback" | "stopped"; start_ms: number; end_ms: number };

export interface Trace {
  status: "done" | "fallback" | "limit" | "error";
  steps: TraceStep[];
  timeline: Segment[];
  totals: {
    duration_ms: number;
    first_token_ms: number | null;
    llm_calls: number;
    input_tokens: number;
    output_tokens: number;
    reasoning_tokens: number;
    tokens_complete: boolean;
  };
  model: { provider: string; name: string };
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
  // Before the final done or error event, however the run ended.
  | ({ type: "trace" } & Trace)
  | { type: "done" }
  // kind "limit": a demo or provider limit was hit; title and message are friendly.
  | { type: "error"; message: string; kind?: "limit"; limit?: LimitKind; title?: string };
