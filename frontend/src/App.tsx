import { useEffect, useRef, useState } from "react";
import "./App.css";
import { LimitError, streamChat } from "./chatStream";
import { AssistantTurn } from "./components/AssistantTurn";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { TopBar } from "./components/TopBar";
import { AboutPage } from "./components/AboutPage";
import { replayExample, savedExample, type ExampleQuestion } from "./examples";
import type { AssistantMessage, Message } from "./messages";
import { useTheme } from "./theme";
import type { ChatEvent, HistoryMessage } from "./types";
import { useView } from "./view";

const CONNECTION_LOST = "The connection to the assistant dropped. Check your connection and try again.";
// The server's error event says only that something went wrong (details stay in its log).
const STOPPED_EARLY = "The answer stopped before it finished, so the text above may be incomplete.";

// Within this distance of the bottom, new text keeps the page scrolled down;
// a visitor who scrolled up to read stays where they are.
const STICK_TO_BOTTOM_PX = 140;

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const view = useView();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const stickToBottom = useRef(true);

  useEffect(() => {
    const onScroll = () => {
      const fromBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
      stickToBottom.current = fromBottom < STICK_TO_BOTTOM_PX;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (stickToBottom.current) {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "auto" });
    }
  }, [messages]);

  // Switching views: the About page opens at its top; the chat comes back at
  // its latest answer. The conversation lives here in App, so it survives.
  useEffect(() => {
    document.title = view === "about" ? "About · Campus Assistant" : "Campus Assistant";
    stickToBottom.current = view === "chat";
    window.scrollTo({ top: view === "about" ? 0 : document.documentElement.scrollHeight });
  }, [view]);

  // Applies a change to the most recent assistant message, immutably.
  function updateLastAssistant(change: (m: AssistantMessage) => AssistantMessage) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last?.role === "assistant") next[next.length - 1] = change(last);
      return next;
    });
  }

  // One handler for live and replayed answers, so both look and behave the same.
  function handleEvent(ev: ChatEvent) {
    if (ev.type === "token") {
      updateLastAssistant((m) => ({ ...m, text: m.text + ev.text }));
    } else if (ev.type === "tool_call") {
      updateLastAssistant((m) => ({ ...m, steps: [...m.steps, { tool: ev.tool, label: ev.label }] }));
    } else if (ev.type === "citations") {
      updateLastAssistant((m) => ({ ...m, citations: ev.citations }));
    } else if (ev.type === "trace") {
      const { type: _type, ...trace } = ev;
      updateLastAssistant((m) => ({ ...m, trace }));
    } else if (ev.type === "done") {
      updateLastAssistant((m) => ({ ...m, status: "done" }));
    } else if (ev.type === "error") {
      const limited = ev.kind === "limit";
      updateLastAssistant((m) => ({
        ...m,
        status: limited ? "limited" : "interrupted",
        error: limited ? ev.message : STOPPED_EARLY,
        errorTitle: ev.title,
      }));
    }
  }

  async function ask(text: string, historyFrom: Message[], exampleId?: string) {
    // Prior turns sent as history. Interrupted and limited answers are left
    // out: they are partial or empty and would mislead the model.
    const history: HistoryMessage[] = historyFrom.flatMap((m): HistoryMessage[] => {
      if (m.role === "user") return [{ role: "user", content: m.text }];
      return m.status === "done" && m.text ? [{ role: "assistant", content: m.text }] : [];
    });
    const saved = exampleId ? savedExample(exampleId) : undefined;

    stickToBottom.current = true;
    setBusy(true);
    setMessages([
      ...historyFrom,
      { role: "user", text },
      { role: "assistant", text: "", steps: [], citations: [], status: "streaming", example: !!saved },
    ]);

    let finished = false;
    const onEvent = (ev: ChatEvent) => {
      if (ev.type === "done" || ev.type === "error") finished = true;
      handleEvent(ev);
    };
    try {
      if (saved) await replayExample(saved, onEvent);
      else await streamChat(text, history, onEvent);
    } catch (err) {
      finished = true;
      if (err instanceof LimitError) {
        updateLastAssistant((m) => ({ ...m, status: "limited", error: err.message, errorTitle: err.title }));
      } else {
        updateLastAssistant((m) => ({ ...m, status: "interrupted", error: CONNECTION_LOST }));
      }
    } finally {
      if (!finished) {
        updateLastAssistant((m) => ({ ...m, status: "interrupted", error: CONNECTION_LOST }));
      }
      setBusy(false);
    }
  }

  function submitTyped() {
    const text = question.trim();
    if (!text || busy) return;
    setQuestion("");
    void ask(text, messages);
  }

  function askExample(example: ExampleQuestion) {
    if (busy) return;
    void ask(example.question, messages, example.id);
  }

  // Asks the last question again, replacing the failed answer.
  function retryLast() {
    const lastUser = messages.length - 2;
    const failed = messages[lastUser];
    if (busy || failed?.role !== "user") return;
    void ask(failed.text, messages.slice(0, lastUser));
  }

  return (
    <div className="app">
      <TopBar theme={theme} onToggleTheme={toggleTheme} view={view} />
      <main className="main">
        {view === "about" ? (
          <AboutPage />
        ) : messages.length === 0 ? (
          <EmptyState onAsk={askExample} />
        ) : (
          <div className="thread">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <p key={i} className="question">
                  {m.text}
                </p>
              ) : (
                <AssistantTurn
                  key={i}
                  message={m}
                  messageIndex={i}
                  isLast={i === messages.length - 1}
                  onRetry={retryLast}
                  onAskExample={askExample}
                />
              ),
            )}
          </div>
        )}
      </main>
      {view === "chat" && (
        <Composer
          value={question}
          onChange={setQuestion}
          onSubmit={submitTyped}
          busy={busy}
          placeholder={messages.length === 0 ? "Ask a question in English or French" : "Ask a follow-up question"}
        />
      )}
    </div>
  );
}
