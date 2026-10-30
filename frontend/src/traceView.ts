import type { Phrasing, RankedPassage, Segment, Trace, TraceStep } from "./types";

// What the "Under the hood" panel shows, computed from a trace. Kept apart
// from the component so the numbers are tested without rendering anything.

export function formatMs(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

// The panel's one-line summary: "1 tool call · 3 queries · 2.0 s · 2,398 tokens".
// Tokens are left out unless every LLM call reported them: a partial sum
// would read as the real total.
export function summaryParts(trace: Trace): string[] {
  const queries = trace.steps.reduce(
    (n, step) => n + (step.tool === "search_documents" ? step.phrasings.length : 0),
    0,
  );
  const parts = [plural(trace.steps.length, "tool call", "tool calls")];
  if (queries > 0) parts.push(plural(queries, "query", "queries"));
  parts.push(formatMs(trace.totals.duration_ms));
  const { totals } = trace;
  if (totals.llm_calls > 0 && totals.tokens_complete) {
    parts.push(`${formatCount(totals.input_tokens + totals.output_tokens)} tokens`);
  }
  return parts;
}

export function segmentLabel(segment: Segment): string {
  switch (segment.kind) {
    case "llm":
      return segment.tool_calls.length > 0 ? "LLM picks tools" : "LLM writes the answer";
    case "tools":
      return "tools";
    case "fallback":
      return "fallback, built in code";
    case "stopped":
      return "stopped";
  }
}

// Each segment's share of the run, in percent. A segment too short to see
// (a 50 ms tool next to 2 s of LLM) gets a sliver, so it's never invisible.
const MIN_SEGMENT_PERCENT = 1.5;

export function segmentPercents(timeline: Segment[]): number[] {
  const total = timeline.length > 0 ? timeline[timeline.length - 1].end_ms : 0;
  if (total <= 0) return timeline.map(() => 100 / Math.max(timeline.length, 1));
  return timeline.map((s) => Math.max(((s.end_ms - s.start_ms) / total) * 100, MIN_SEGMENT_PERCENT));
}

// A passage's score bar, scaled to the most any passage could score in that
// search (first in every ranked list), so bars compare across answers.
export function scoreFraction(passage: RankedPassage, maxScore: number): number {
  return maxScore > 0 ? Math.min(passage.rrf_score / maxScore, 1) : 0;
}

// What became of a retrieved passage: cited in the answer, returned already
// by an earlier step (whose row says whether it was cited), or not cited.
export type PassageUse = { kind: "cited" } | { kind: "seen"; step: number } | { kind: "unused" };

export function passageUse(
  passage: RankedPassage,
  stepIndex: number,
  steps: TraceStep[],
  citedMarkers: Set<number>,
): PassageUse {
  if (!passage.new) {
    const earlier = steps
      .slice(0, stepIndex)
      .findIndex(
        (step) =>
          (step.tool === "search_documents" && step.results.some((r) => r.marker === passage.marker)) ||
          (step.tool === "query_courses" && step.marker === passage.marker),
      );
    if (earlier >= 0) return { kind: "seen", step: earlier + 1 };
  }
  return citedMarkers.has(passage.marker) ? { kind: "cited" } : { kind: "unused" };
}

const ORIGIN_LABELS: Record<Phrasing["origins"][number], string> = {
  query: "agent's query",
  query_en: "agent's English version",
  question: "student's question (first turn)",
};

export function originLabel(phrasing: Phrasing): string {
  return phrasing.origins.map((origin) => ORIGIN_LABELS[origin]).join(" = ");
}

// A word's letters and digits, with the punctuation around them:
// "(l'AUI)?" -> "(", "l'AUI", ")?".
const PUNCTUATION_AROUND = /^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*)$/u;

// The phrasing as written, word by word, marking the words search left out
// (the university's name): "comment ajouter … cours ~~AUI~~". The name can
// be part of a word: search keeps the punctuation around it ("transfer to
// AUI?" was searched as "transfer to ?"), so that word comes back in pieces,
// `attached` to the one before ("to ~~AUI~~?"). null when nothing was
// removed, or when the two can't be lined up word by word.
export function writtenWords(
  phrasing: Phrasing,
): { word: string; removed: boolean; attached: boolean }[] | null {
  const searched = phrasing.text.split(/\s+/).filter(Boolean);
  const words = [];
  let next = 0;
  const takeNext = (text: string) => {
    const same = next < searched.length && text.toLowerCase() === searched[next].toLowerCase();
    if (same) next += 1;
    return same;
  };
  for (const word of phrasing.as_written.split(/\s+/).filter(Boolean)) {
    if (takeNext(word)) {
      words.push({ word, removed: false, attached: false });
      continue;
    }
    const [, lead, core, trail] = PUNCTUATION_AROUND.exec(word)!;
    const keepLead = lead !== "" && takeNext(lead);
    const keepTrail = trail !== "" && takeNext(trail);
    if (keepLead) words.push({ word: lead, removed: false, attached: false });
    const removed = (keepLead ? "" : lead) + core + (keepTrail ? "" : trail);
    words.push({ word: removed, removed: true, attached: keepLead });
    if (keepTrail) words.push({ word: trail, removed: false, attached: true });
  }
  if (next !== searched.length || !words.some((w) => w.removed)) return null;
  return words;
}

export function courseOutcome(step: Extract<TraceStep, { tool: "query_courses" }>): string {
  if (step.found === "no_description") return "In the catalog, but with no course description";
  if (step.found === "not_found") return "No course with this code in the catalog";
  const page = step.pages?.length ? `, p. ${step.pages[0]}` : "";
  const chain =
    step.chain_length == null
      ? ""
      : ` · prerequisite chain: ${plural(step.chain_length, "course", "courses")}`;
  return `${step.title ?? "Found"}${page}${chain}`;
}
