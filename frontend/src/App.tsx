import { useState, type FormEvent } from "react";
import "./App.css";
import { streamChat } from "./chatStream";
import type { Citation, HistoryMessage } from "./types";

interface UserMessage {
  role: "user";
  text: string;
}

interface AssistantMessage {
  role: "assistant";
  text: string;
  labels: string[];
  citations: Citation[];
  status: "streaming" | "done" | "interrupted";
  error?: string;
}

type Message = UserMessage | AssistantMessage;

// Splits "[3]" markers out of the answer so each can be rendered as a link.
// Two regexes on purpose: a global regex used with .test() keeps state
// between calls, so the split pattern and the whole-part check stay separate.
const MARKER_SPLIT = /(\[\d+\])/;
const MARKER_ONLY = /^\[\d+\]$/;

function AnswerText({ text, citations }: { text: string; citations: Citation[] }) {
  const knownMarkers = new Set(citations.map((c) => `[${c.marker}]`));
  return (
    <>
      {text.split(MARKER_SPLIT).map((part, i) =>
        MARKER_ONLY.test(part) && knownMarkers.has(part) ? (
          <sup key={i}>
            <a href={`#source-${part.slice(1, -1)}`}>{part}</a>
          </sup>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);

  // Applies a change to the most recent assistant message, immutably.
  function updateLastAssistant(change: (m: AssistantMessage) => AssistantMessage) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last?.role === "assistant") next[next.length - 1] = change(last);
      return next;
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    // Prior turns sent as history. Interrupted answers are left out: they are
    // partial and would mislead the model about what was actually answered.
    const history: HistoryMessage[] = messages.flatMap((m): HistoryMessage[] => {
      if (m.role === "user") return [{ role: "user", content: m.text }];
      return m.status === "done" && m.text ? [{ role: "assistant", content: m.text }] : [];
    });

    setBusy(true);
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      { role: "user", text: trimmed },
      { role: "assistant", text: "", labels: [], citations: [], status: "streaming" },
    ]);

    let finished = false;
    try {
      await streamChat(trimmed, history, (ev) => {
        if (ev.type === "token") {
          updateLastAssistant((m) => ({ ...m, text: m.text + ev.text }));
        } else if (ev.type === "tool_call") {
          updateLastAssistant((m) => ({ ...m, labels: [...m.labels, ev.label] }));
        } else if (ev.type === "citations") {
          updateLastAssistant((m) => ({ ...m, citations: ev.citations }));
        } else if (ev.type === "done") {
          finished = true;
          updateLastAssistant((m) => ({ ...m, status: "done" }));
        } else if (ev.type === "error") {
          finished = true;
          updateLastAssistant((m) => ({ ...m, status: "interrupted", error: ev.message }));
        }
      });
    } catch (err) {
      finished = true;
      const message = err instanceof Error ? err.message : "Connection failed";
      updateLastAssistant((m) => ({ ...m, status: "interrupted", error: message }));
    } finally {
      if (!finished) {
        updateLastAssistant((m) => ({
          ...m,
          status: "interrupted",
          error: "The answer ended unexpectedly.",
        }));
      }
      setBusy(false);
    }
  }

  return (
    <main className="chat">
      <h1>AUI Assistant</h1>

      <div className="messages">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="message user">
              {m.text}
            </div>
          ) : (
            <div key={i} className="message assistant">
              {m.labels.map((label, j) => (
                <div key={j} className="tool-label">
                  {label}
                </div>
              ))}
              <div className="answer">
                <AnswerText text={m.text} citations={m.citations} />
                {m.status === "streaming" && <span className="cursor">▍</span>}
              </div>
              {m.status === "interrupted" && (
                <div className="interrupted">Answer interrupted: {m.error}</div>
              )}
              {m.citations.length > 0 && (
                // Only cited sources arrive, so markers can skip numbers ([2], [4]).
                // value= makes each footnote show its marker, not its list position.
                <ol className="sources">
                  {m.citations.map((c) => (
                    <li key={c.marker} id={`source-${c.marker}`} value={c.marker}>
                      {c.source}
                      {c.pages && c.pages.length > 0 ? `, p. ${c.pages.join(", ")}` : ""}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ),
        )}
      </div>

      <form onSubmit={handleSubmit} className="composer">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about AUI policies, courses, or scholarships"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !question.trim()}>
          Send
        </button>
      </form>
    </main>
  );
}
