import { EXAMPLE_QUESTIONS, type ExampleQuestion } from "../examples";

export function EmptyState({ onAsk }: { onAsk: (example: ExampleQuestion) => void }) {
  return (
    <section className="empty" aria-labelledby="empty-title">
      <h1 id="empty-title">Ask about AUI's academic rules, courses and scholarships</h1>
      <p>
        Answers come from the public 2024–2025 Academic Catalog and AUI's scholarship pages,
        with the sources they used.
      </p>
      <div className="examples">
        {EXAMPLE_QUESTIONS.map((example) => (
          <button
            key={example.id}
            type="button"
            className="example"
            lang={example.language}
            onClick={() => onAsk(example)}
          >
            <span className="example-lang">
              {example.language.toUpperCase()} · {example.language === "fr" ? "exemple" : "example"}
            </span>
            <span className="example-text">{example.question}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
