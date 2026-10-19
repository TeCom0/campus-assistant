import { useState, type FormEvent } from "react";
import Markdown, { type Components } from "react-markdown";
import "./App.css";
import { LimitError, streamChat } from "./chatStream";
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
  // "limited": the demo's daily cap, the per-IP limit or the LLM provider's
  // limit -- shown as a friendly notice, not as a broken answer. Like
  // "interrupted", it isn't sent back as history (only "done" is).
  status: "streaming" | "done" | "interrupted" | "limited";
  error?: string;
}

type Message = UserMessage | AssistantMessage;

// Footnote ids include the message index: markers restart at [1] in every
// answer, so "source-1" alone would repeat and every link would jump to the
// first answer's footnote.
function sourceId(messageIndex: number, marker: number | string) {
  return `source-${messageIndex}-${marker}`;
}

// Rewrites each "[3]" that has a received citation into a Markdown link to its
// footnote ("[\[3\]](#source-2-3)"; the escaped brackets keep "[3]" as the
// visible text). Markers with no citation stay plain text, so the model can't
// create a link to a source that doesn't exist.
function linkCitationMarkers(text: string, citations: Citation[], messageIndex: number) {
  const knownMarkers = new Set(citations.map((c) => c.marker));
  return text.replace(/\[(\d+)\]/g, (marker, number: string) =>
    knownMarkers.has(Number(number))
      ? `[\\[${number}\\]](#${sourceId(messageIndex, number)})`
      : marker,
  );
}

// Footnote links render as superscripts; any other link in an answer opens in
// a new tab. No raw HTML: react-markdown escapes it unless a plugin allows it.
const markdownComponents: Components = {
  a: ({ href, children }) =>
    href?.startsWith("#source-") ? (
      <sup>
        <a href={href}>{children}</a>
      </sup>
    ) : (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    ),
};

function AnswerText({
  text,
  citations,
  messageIndex,
}: {
  text: string;
  citations: Citation[];
  messageIndex: number;
}) {
  return (
    <Markdown components={markdownComponents}>
      {linkCitationMarkers(text, citations, messageIndex)}
    </Markdown>
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
          const status = ev.kind === "limit" ? "limited" : "interrupted";
          updateLastAssistant((m) => ({ ...m, status, error: ev.message }));
        }
      });
    } catch (err) {
      finished = true;
      const message = err instanceof Error ? err.message : "Connection failed";
      const status = err instanceof LimitError ? "limited" : "interrupted";
      updateLastAssistant((m) => ({ ...m, status, error: message }));
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
                <AnswerText text={m.text} citations={m.citations} messageIndex={i} />
                {m.status === "streaming" && <span className="cursor">▍</span>}
              </div>
              {m.status === "interrupted" && (
                <div className="interrupted">Answer interrupted: {m.error}</div>
              )}
              {m.status === "limited" && <div className="limit-notice">{m.error}</div>}
              {m.citations.length > 0 && (
                // Only cited sources arrive, so markers can skip numbers ([2], [4]).
                // value= makes each footnote show its marker, not its list position.
                <ol className="sources">
                  {m.citations.map((c) => (
                    <li key={c.marker} id={sourceId(i, c.marker)} value={c.marker}>
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
