import Markdown from "react-markdown";
import { firstParagraph, pagesLabel, stepsSummary } from "../answerFormat";
import { DATA_COUNTS, RESULTS } from "../about";
import { EXAMPLE_QUESTIONS, savedExample, type ExampleQuestion } from "../examples";

// The proof card quotes this saved example (its first paragraph and its first
// source), so the excerpt is always a real, reviewed answer, never typed here.
export const PROOF_EXAMPLE_ID = "acc2302_prereqs_en";

// Real counts, from about.ts (checked against the README by about.test.ts).
const FACTS = [
  [DATA_COUNTS.passages.toLocaleString("en-US"), "passages"],
  [DATA_COUNTS.courses.toLocaleString("en-US"), "courses"],
  [DATA_COUNTS.links.toLocaleString("en-US"), "prerequisite links"],
  [RESULTS[0].value, "retrieval Hit@5"],
];

// French puts a space before "?", "!", ":" and ";". A no-break space keeps
// the mark from wrapping onto a line of its own ("1,99" / "?" on a phone).
function keepPunctuation(text: string): string {
  return text.replace(/ ([?!:;])/g, "\u00a0$1");
}

function ProofCard({ onAsk }: { onAsk: (example: ExampleQuestion) => void }) {
  const question = EXAMPLE_QUESTIONS.find((e) => e.id === PROOF_EXAMPLE_ID);
  const saved = savedExample(PROOF_EXAMPLE_ID);
  const source = saved?.citations[0];
  if (!question || !saved || !source) return null;
  return (
    <figure className="proof">
      <figcaption className="proof-q">{saved.question}</figcaption>
      <blockquote className="proof-a">
        <Markdown>{firstParagraph(saved.answer)}</Markdown>
      </blockquote>
      <div className="proof-src">
        {pagesLabel(source.pages) && <span className="proof-page">{pagesLabel(source.pages)}</span>}
        <span>
          {source.title}
          {source.section && ` · ${source.section}`}
        </span>
        <button type="button" className="proof-more" onClick={() => onAsk(question)}>
          See the full answer →
        </button>
      </div>
    </figure>
  );
}

export function EmptyState({ onAsk }: { onAsk: (example: ExampleQuestion) => void }) {
  return (
    <section className="empty" aria-labelledby="empty-title">
      <div className="hero">
        <span className="hero-eyebrow">AUI academic rules · EN / FR</span>
        <h1 id="empty-title">
          Ask the catalog. Get the <em>page</em> the answer came from.
        </h1>
        <p>
          An AI agent searches the public 2024–2025 Academic Catalog and AUI's scholarship pages,
          looks up course prerequisites in structured data, and cites the passages it used.
        </p>
        <ProofCard onAsk={onAsk} />
        <p className="facts">
          {FACTS.map(([value, label]) => (
            <span key={label}>
              <b>{value}</b> {label}
            </span>
          ))}
          <a href="#about">How it's measured →</a>
        </p>
      </div>
      <h2 className="eyebrow">Try an example · saved answers, replayed instantly, not counted in the daily limit</h2>
      <div className="examples">
        {EXAMPLE_QUESTIONS.map((example) => {
          const saved = savedExample(example.id);
          return (
            <button
              key={example.id}
              type="button"
              className="example"
              lang={example.language}
              onClick={() => onAsk(example)}
            >
              <span className="example-lang">
                <span>
                  {example.language.toUpperCase()} · {example.language === "fr" ? "exemple" : "example"}
                </span>
                {/* The path the saved answer took, from its own tool calls. */}
                {saved && <span className="example-path" lang="en">{stepsSummary(saved.tool_calls)}</span>}
              </span>
              <span className="example-text">{keepPunctuation(example.question)}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
