import type { MouseEvent } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "../chatStream";
import { EXAMPLE_QUESTIONS, savedExample, type ExampleQuestion } from "../examples";
import type { AssistantMessage, Step } from "../messages";
import { prefersReducedMotion } from "../theme";
import type { Citation } from "../types";
import { AlertIcon, CheckIcon, ClockIcon } from "./icons";

// Source card ids include the message index: markers restart at [1] in every
// answer, so "source-1" alone would repeat and every chip would jump to the
// first answer's card.
function sourceId(messageIndex: number, marker: number | string) {
  return `source-${messageIndex}-${marker}`;
}

// Rewrites each "[3]" that has a received citation into a Markdown link to its
// card ("[3](#source-2-3)"), rendered as a chip by markdownComponents. The
// citations arrive only once the answer is complete, so while it streams every
// marker becomes a pending (muted, not clickable) chip. After that, markers
// with no citation stay plain text, so the model can't link to a source that
// doesn't exist. Grouped markers ("[2, 4]") stay plain text too, for now.
function linkCitationMarkers(
  text: string,
  citations: Citation[],
  messageIndex: number,
  streaming: boolean,
) {
  const knownMarkers = new Set(citations.map((c) => c.marker));
  return text.replace(/\[(\d+)\]/g, (marker, number: string) => {
    if (knownMarkers.has(Number(number))) return `[${number}](#${sourceId(messageIndex, number)})`;
    return streaming ? `[${number}](#pending-${number})` : marker;
  });
}

// A chip scrolls to its card and briefly highlights it (no smooth scroll with
// reduced motion). The class is removed and re-added so a second click
// restarts the highlight.
function jumpToSource(event: MouseEvent<HTMLAnchorElement>, href: string) {
  event.preventDefault();
  const card = document.getElementById(href.slice(1));
  if (!card) return;
  card.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "nearest" });
  card.classList.remove("flash");
  void card.offsetWidth;
  card.classList.add("flash");
}

// No raw HTML: react-markdown escapes it unless a plugin allows it. Links
// other than citation chips open in a new tab.
const markdownComponents: Components = {
  a: ({ href, children }) =>
    href?.startsWith("#pending-") ? (
      <span className="cite pending">{children}</span>
    ) : href?.startsWith("#source-") ? (
      <a className="cite" href={href} onClick={(e) => jumpToSource(e, href)}>
        {children}
      </a>
    ) : (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    ),
};

function pagesLabel(pages: number[] | null): string {
  if (!pages || pages.length === 0) return "";
  if (pages.length === 1) return `p. ${pages[0]}`;
  const consecutive = pages.every((p, i) => i === 0 || p === pages[i - 1] + 1);
  return consecutive ? `p. ${pages[0]}–${pages[pages.length - 1]}` : `p. ${pages.join(", ")}`;
}

function stepsSummary(steps: Step[]): string {
  const searches = steps.filter((s) => s.tool === "search_documents").length;
  const lookups = steps.filter((s) => s.tool === "query_courses").length;
  const parts = [];
  if (searches) parts.push(`${searches} ${searches === 1 ? "search" : "searches"}`);
  if (lookups) parts.push(`${lookups} course ${lookups === 1 ? "lookup" : "lookups"}`);
  return parts.join(" · ") || `${steps.length} steps`;
}

function Steps({ message }: { message: AssistantMessage }) {
  const { steps, status, text } = message;
  if (steps.length === 0) return null;
  const working = status === "streaming";
  // A step is done once something comes after it: the next step, the first
  // words of the answer, or the end of the stream.
  const list = (
    <ul className="steps">
      {steps.map((step, i) => {
        const done = i < steps.length - 1 || text.length > 0 || !working;
        return (
          <li key={i} className="step">
            {done ? (
              <span className="step-ok">
                <CheckIcon />
              </span>
            ) : (
              <span className="spin" aria-hidden="true" />
            )}
            <span>{step.label}</span>
          </li>
        );
      })}
    </ul>
  );
  if (working && text.length === 0) return list;
  return (
    <details className="steps-summary">
      <summary>{stepsSummary(steps)}</summary>
      {list}
    </details>
  );
}

function Sources({ citations, messageIndex }: { citations: Citation[]; messageIndex: number }) {
  return (
    <section className="sources" aria-label="Sources">
      <h2 className="eyebrow">Sources</h2>
      <div className="cards">
        {citations.map((c, i) => {
          const inner = (
            <>
              <span className="card-top">
                <span className="num">{c.marker}</span>
                <span className="doc">{c.title}</span>
              </span>
              <span className="meta">
                {pagesLabel(c.pages) && <span className="pages">{pagesLabel(c.pages)}</span>}
                {pagesLabel(c.pages) && c.section && " · "}
                {c.section}
              </span>
              {c.link && <span className="open">Open at page ↗</span>}
            </>
          );
          const props = {
            id: sourceId(messageIndex, c.marker),
            className: "card",
            style: { animationDelay: `${i * 70}ms` },
          };
          return c.link ? (
            <a key={c.marker} {...props} href={`${API_URL}${c.link}`} target="_blank" rel="noreferrer">
              {inner}
            </a>
          ) : (
            <div key={c.marker} {...props}>
              {inner}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function AssistantTurn({
  message,
  messageIndex,
  isLast,
  onRetry,
  onAskExample,
}: {
  message: AssistantMessage;
  messageIndex: number;
  isLast: boolean;
  onRetry: () => void;
  onAskExample: (example: ExampleQuestion) => void;
}) {
  const streaming = message.status === "streaming";
  const savedExamples = EXAMPLE_QUESTIONS.filter((e) => savedExample(e.id));
  return (
    <article className="turn" aria-busy={streaming}>
      {message.example && <span className="example-tag">Example answer, saved in advance</span>}
      <Steps message={message} />

      {streaming && message.text.length === 0 && (
        <div className="skeleton" aria-label="Writing the answer">
          <i style={{ width: "92%" }} />
          <i style={{ width: "78%" }} />
          <i style={{ width: "54%" }} />
        </div>
      )}

      {message.text.length > 0 && (
        // While streaming, the caret is drawn by CSS after the last paragraph or
        // list item, so it sits at the end of the text, not on a line of its own.
        <div className={streaming ? "answer streaming" : "answer"}>
          {/* remark-gfm: tables, which the agent often uses for lists of rules or courses. */}
          <Markdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
            {linkCitationMarkers(message.text, message.citations, messageIndex, streaming)}
          </Markdown>
        </div>
      )}

      {message.status === "interrupted" && (
        <div className="state state-error" role="alert">
          <div className="state-head">
            <AlertIcon />
            {message.errorTitle ?? "The answer was cut off"}
          </div>
          <p>{message.error}</p>
          {isLast && (
            <button type="button" className="btn" onClick={onRetry}>
              Ask again
            </button>
          )}
        </div>
      )}

      {message.status === "limited" && (
        <div className="state state-limit" role="status">
          <div className="state-head">
            <ClockIcon />
            {message.errorTitle}
          </div>
          <p>{message.error}</p>
          {savedExamples.length > 0 && (
            <div className="mini-examples">
              {savedExamples.map((e) => (
                <button key={e.id} type="button" className="mini" lang={e.language} onClick={() => onAskExample(e)}>
                  {e.short}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {message.citations.length > 0 && (
        <Sources citations={message.citations} messageIndex={messageIndex} />
      )}
    </article>
  );
}
