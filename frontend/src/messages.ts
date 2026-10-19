import type { Citation } from "./types";

export interface UserMessage {
  role: "user";
  text: string;
}

// One tool call the agent made, shown as a status line ("Looking up course ACC 2302").
export interface Step {
  tool: string;
  label: string;
}

export interface AssistantMessage {
  role: "assistant";
  text: string;
  steps: Step[];
  citations: Citation[];
  // "limited": the demo's daily cap, the per-IP limit or the LLM provider's
  // limit -- shown as a calm notice, not as a broken answer. Like
  // "interrupted", it isn't sent back as history (only "done" is).
  status: "streaming" | "done" | "interrupted" | "limited";
  error?: string;
  errorTitle?: string;
  // Replayed from a saved example answer, not generated live.
  example?: boolean;
}

export type Message = UserMessage | AssistantMessage;
