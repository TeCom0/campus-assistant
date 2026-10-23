import {
  courseOutcome,
  formatCount,
  formatMs,
  originLabel,
  passageUse,
  scoreFraction,
  segmentLabel,
  segmentPercents,
  summaryParts,
  writtenWords,
} from "../traceView";
import type { Citation, Phrasing, SearchStep, Trace, TraceStep } from "../types";

// The "Under the hood" panel under an answer: what the agent did, in order.
// Closed by default (a native <details>: keyboard and screen readers get it
// for free), with a one-line summary always visible. Display only: the
// evaluation never reads the trace.

const STATUS_NOTES: Partial<Record<Trace["status"], string>> = {
  fallback:
    "The model couldn't write an answer, so the reply above was built in code from the passages found.",
  limit: "The run stopped at a usage limit; this is what it did until then.",
  error: "The run stopped on an error; this is what it did until then.",
};

function Timeline({ trace }: { trace: Trace }) {
  const percents = segmentPercents(trace.timeline);
  const { first_token_ms } = trace.totals;
  return (
    <div className="uth-block">
      <h3 className="eyebrow">Timeline · {formatMs(trace.totals.duration_ms)}</h3>
      <div className="tl-bar" aria-hidden="true">
        {trace.timeline.map((segment, i) => (
          <i key={i} className={`seg seg-${segment.kind}`} style={{ width: `${percents[i]}%` }} />
        ))}
      </div>
      <ul className="tl-legend">
        {trace.timeline.map((segment, i) => (
          <li key={i} className={`seg-${segment.kind}`}>
            {segmentLabel(segment)} {formatMs(segment.end_ms - segment.start_ms)}
          </li>
        ))}
        {first_token_ms != null && <li className="tl-first">first word at {formatMs(first_token_ms)}</li>}
      </ul>
    </div>
  );
}

function PhrasingText({ phrasing }: { phrasing: Phrasing }) {
  const words = writtenWords(phrasing);
  if (!words) return <span className="q">{phrasing.text}</span>;
  return (
    <span className="q">
      {words.map((w, i) => (
        <span key={i}>
          {i > 0 && " "}
          {w.removed ? <s title="Removed before searching">{w.word}</s> : w.word}
        </span>
      ))}
    </span>
  );
}

function SearchDetails({
  step,
  index,
  steps,
  cited,
}: {
  step: SearchStep;
  index: number;
  steps: TraceStep[];
  cited: Set<number>;
}) {
  return (
    <>
      <dl className="kv">
        <dt>query</dt>
        <dd>{step.args.query}</dd>
        <dt>query_en</dt>
        <dd>{step.args.query_en || "(not written)"}</dd>
      </dl>
      <div className="uth-block">
        <h4 className="eyebrow">
          Searched · {step.phrasings.length} {step.phrasings.length === 1 ? "phrasing" : "phrasings"} ×
          (vector + keyword) = {step.ranked_lists} ranked lists
        </h4>
        <ul className="phrasings">
          {step.phrasings.map((phrasing) => (
            <li key={phrasing.text}>
              <PhrasingText phrasing={phrasing} />
              <span className="origin">{originLabel(phrasing)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="uth-block">
        <h4 className="eyebrow">Fused by RRF (k = 60) · top {step.results.length} sent to the model</h4>
        {step.results.length === 0 ? (
          <p className="uth-none">No passages found.</p>
        ) : (
          <div className="res-scroll">
            <table className="res">
              <thead>
                <tr>
                  <th scope="col" className="n">#</th>
                  <th scope="col">Passage</th>
                  <th scope="col" className="n" title={`Best possible here: ${step.max_rrf_score}`}>
                    RRF
                  </th>
                  <th scope="col" className="n" title="Best rank across phrasings">Vector</th>
                  <th scope="col" className="n" title="Best rank across phrasings">Keyword</th>
                  <th scope="col"><span className="visually-hidden">Used</span></th>
                </tr>
              </thead>
              <tbody>
                {step.results.map((passage) => {
                  const use = passageUse(passage, index, steps, cited);
                  return (
                    <tr key={passage.marker}>
                      <td className="n rank">{passage.rank}</td>
                      <td className="psg">
                        {passage.section ?? passage.title}
                        <small>
                          {passage.pages?.length ? `p. ${passage.pages[0]} · ` : ""}
                          {passage.snippet}
                        </small>
                      </td>
                      <td className="n metric first-metric" data-label="RRF">
                        <span className="score">
                          {passage.rrf_score.toFixed(4)}
                          <b aria-hidden="true">
                            <i style={{ width: `${scoreFraction(passage, step.max_rrf_score) * 100}%` }} />
                          </b>
                        </span>
                      </td>
                      <td className="n metric" data-label="Vector">{passage.vector_rank ?? "–"}</td>
                      <td className="n metric" data-label="Keyword">{passage.keyword_rank ?? "–"}</td>
                      <td className="metric">
                        {use.kind === "cited" && <span className="used">cited [{passage.marker}]</span>}
                        {use.kind === "seen" && <span className="unused">seen in step {use.step}</span>}
                        {use.kind === "unused" && <span className="unused">not cited</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

function StepCard({
  step,
  index,
  steps,
  cited,
}: {
  step: TraceStep;
  index: number;
  steps: TraceStep[];
  cited: Set<number>;
}) {
  return (
    <li className="uth-step">
      <div className="step-head">
        <span className="step-n">{index + 1}</span>
        <code>{step.tool}</code>
        <span className="ms">{formatMs(step.duration_ms)}</span>
      </div>
      {step.tool === "search_documents" ? (
        <SearchDetails step={step} index={index} steps={steps} cited={cited} />
      ) : (
        <dl className="kv">
          <dt>code</dt>
          <dd>{step.args.code}</dd>
          <dt>chain</dt>
          <dd>{step.args.follow_prerequisites ? "full prerequisite chain (recursive SQL)" : "no"}</dd>
          <dt>found</dt>
          <dd>{courseOutcome(step)}</dd>
        </dl>
      )}
    </li>
  );
}

function Tokens({ trace }: { trace: Trace }) {
  const { totals } = trace;
  const tiles: [string, string][] = [
    [String(totals.llm_calls), totals.llm_calls === 1 ? "LLM call" : "LLM calls"],
    [formatCount(totals.input_tokens), "input tokens"],
    [formatCount(totals.output_tokens), `output tokens (${formatCount(totals.reasoning_tokens)} reasoning)`],
    [totals.first_token_ms != null ? formatMs(totals.first_token_ms) : "–", "to first word"],
  ];
  return (
    <div className="uth-block">
      <h3 className="eyebrow">
        Model · {trace.model.name} on {trace.model.provider === "groq" ? "Groq" : trace.model.provider}
      </h3>
      <div className="tok">
        {tiles.map(([value, label]) => (
          <div key={label}>
            <b>{value}</b>
            <span>{label}</span>
          </div>
        ))}
      </div>
      {!totals.tokens_complete && <p className="uth-none">Some calls reported no token counts.</p>}
    </div>
  );
}

export function UnderTheHood({ trace, citations }: { trace: Trace; citations: Citation[] }) {
  const cited = new Set(citations.map((c) => c.marker));
  const note = STATUS_NOTES[trace.status];
  return (
    <details className="uth">
      <summary>
        <span className="uth-title">Under the hood</span>
        <span className="uth-stats">{summaryParts(trace).join(" · ")}</span>
      </summary>
      <div className="uth-body">
        {note && <p className="uth-note">{note}</p>}
        <Timeline trace={trace} />
        {trace.steps.length > 0 && (
          <ol className="uth-steps">
            {trace.steps.map((step, i) => (
              <StepCard key={step.call_id ?? i} step={step} index={i} steps={trace.steps} cited={cited} />
            ))}
          </ol>
        )}
        <Tokens trace={trace} />
        <p className="uth-foot">
          Shown for transparency only: the evaluation never reads this trace.
        </p>
      </div>
    </details>
  );
}
