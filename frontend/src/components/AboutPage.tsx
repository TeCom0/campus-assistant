import { DEMO_VIDEO_URL, LIMITATIONS, REPO_URL, RESULTS, STACK } from "../about";
import { GitHubIcon } from "./icons";

// The About page (#about): what the project is, its measured results with
// their caveats, its limitations and links. The figures live in about.ts,
// checked against the README by about.test.ts.
export function AboutPage() {
  return (
    <article className="about" aria-labelledby="about-title">
      <header className="about-head">
        <span className="eyebrow">About this project</span>
        <h1 id="about-title">A cited, bilingual assistant for one university's rulebook</h1>
        <p className="about-lead">
          Students ask in English or French. An agent decides whether to search the 2024–2025
          Academic Catalog and scholarship pages or to look up structured course data, then answers
          only from what it found and cites the page. An unofficial student project by Youness, with
          its retrieval and its answers' faithfulness measured.
        </p>
        <div className="about-links">
          <a className="link-btn primary" href={REPO_URL} target="_blank" rel="noreferrer">
            <GitHubIcon />
            Source on GitHub
          </a>
          {DEMO_VIDEO_URL ? (
            <a className="link-btn" href={DEMO_VIDEO_URL} target="_blank" rel="noreferrer">
              Demo video
            </a>
          ) : (
            <span className="link-btn off">Demo video · coming soon</span>
          )}
          <a className="link-btn" href="#">
            Try the assistant →
          </a>
        </div>
      </header>

      <section className="about-section" aria-labelledby="results-title">
        <h2 id="results-title">Measured, not assumed</h2>
        <div className="results">
          {RESULTS.map((result) => (
            <div key={result.label} className="result">
              <b>{result.value}</b>
              <span className="result-label">{result.label}</span>
              <span className="result-detail">{result.detail}</span>
            </div>
          ))}
        </div>
        <p className="about-note">
          Retrieval: 14 hand-labelled questions, each with a verbatim answer sentence as its anchor.
          Faithfulness: every cited claim checked against its passage by an LLM judge from another
          model family, whose agreement with hand labels was measured too. Details in the{" "}
          <a href={`${REPO_URL}#evaluation`} target="_blank" rel="noreferrer">
            README's Evaluation section
          </a>
          .
        </p>
      </section>

      <section className="about-section" aria-labelledby="limits-title">
        <h2 id="limits-title">What it doesn't do well yet</h2>
        <ul className="limits">
          {LIMITATIONS.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>

      <section className="about-section" aria-labelledby="stack-title">
        <h2 id="stack-title">Built with</h2>
        <ul className="chips">
          {STACK.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="about-note">
          The live demo answers 30 questions a day in total, and 5 per visitor per 10 minutes. The
          example questions are answers saved in advance: they answer instantly and don't count.
        </p>
      </section>
    </article>
  );
}
