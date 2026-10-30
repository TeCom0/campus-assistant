import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { UnderTheHood } from "./components/UnderTheHood";
import type { SavedExample } from "./examples";
import transferCredits from "./examples/transfer_credits_en.json";
import {
  formatMs,
  passageUse,
  scoreFraction,
  segmentPercents,
  summaryParts,
  writtenWords,
} from "./traceView";
import type { RankedPassage, SearchStep, Trace } from "./types";

function passage(marker: number, extra: Partial<RankedPassage> = {}): RankedPassage {
  return {
    rank: marker,
    marker,
    new: true,
    source: "academic_catalog_2024_2025",
    pages: [103],
    title: "Academic Catalog 2024–2025",
    section: "Adding/Dropping Courses",
    snippet: "Students in good academic standing…",
    rrf_score: 0.0492,
    vector_rank: 1,
    keyword_rank: null,
    ...extra,
  };
}

function search(results: RankedPassage[], call_id = "c1"): SearchStep {
  return {
    tool: "search_documents",
    call_id,
    args: { query: "comment ajouter ou supprimer un cours AUI", query_en: "how to add or drop a course" },
    phrasings: [
      { text: "comment ajouter ou supprimer un cours", origins: ["query"], as_written: "comment ajouter ou supprimer un cours AUI" },
      { text: "how to add or drop a course", origins: ["query_en"], as_written: "how to add or drop a course" },
    ],
    ranked_lists: 4,
    max_rrf_score: 0.0656,
    results,
    duration_ms: 412,
  };
}

// Shape of the live ACC 2302 trace (2026-10-23), with a search added.
const TRACE: Trace = {
  status: "done",
  steps: [search([passage(1), passage(2)])],
  timeline: [
    { kind: "llm", start_ms: 0, end_ms: 1381, tool_calls: ["search_documents"], input_tokens: 888, output_tokens: 47, reasoning_tokens: 14 },
    { kind: "tools", start_ms: 1381, end_ms: 1434 },
    { kind: "llm", start_ms: 1434, end_ms: 2041, tool_calls: [], input_tokens: 1148, output_tokens: 315, reasoning_tokens: 74 },
  ],
  totals: {
    duration_ms: 2041,
    first_token_ms: 1768,
    llm_calls: 2,
    input_tokens: 2036,
    output_tokens: 362,
    reasoning_tokens: 88,
    tokens_complete: true,
  },
  model: { provider: "groq", name: "openai/gpt-oss-20b" },
};

// The saved example whose question "How many credits can I transfer to AUI?"
// was searched as "How many credits can I transfer to ?".
const TRANSFER = transferCredits as SavedExample;

describe("summaryParts", () => {
  it("counts tool calls, phrasings searched, time and tokens", () => {
    expect(summaryParts(TRACE)).toEqual(["1 tool call", "2 queries", "2.0 s", "2,398 tokens"]);
  });

  it("leaves tokens out when a call didn't report them", () => {
    const partial = { ...TRACE, totals: { ...TRACE.totals, tokens_complete: false } };
    expect(summaryParts(partial).some((part) => part.includes("tokens"))).toBe(false);
  });
});

describe("formatMs", () => {
  it("shows milliseconds under a second, else seconds", () => {
    expect([formatMs(53), formatMs(999), formatMs(1381)]).toEqual(["53 ms", "999 ms", "1.4 s"]);
  });
});

describe("segmentPercents", () => {
  it("is proportional, with a visible sliver for a very short segment", () => {
    const [first, tools, last] = segmentPercents(TRACE.timeline);
    expect(first).toBeCloseTo((1381 / 2041) * 100);
    expect(tools).toBeCloseTo((53 / 2041) * 100); // 2.6%: above the minimum, so unchanged
    expect(last).toBeCloseTo((607 / 2041) * 100);
    const tiny = segmentPercents([
      { kind: "llm", start_ms: 0, end_ms: 5000, tool_calls: [], input_tokens: 1, output_tokens: 1, reasoning_tokens: 0 },
      { kind: "tools", start_ms: 5000, end_ms: 5010 },
    ]);
    expect(tiny[1]).toBe(1.5);
  });
});

describe("scoreFraction", () => {
  it("scales a score to the best one possible in its search, capped at 1", () => {
    expect(scoreFraction(passage(1, { rrf_score: 0.0328 }), 0.0656)).toBeCloseTo(0.5);
    expect(scoreFraction(passage(1, { rrf_score: 0.07 }), 0.0656)).toBe(1);
    expect(scoreFraction(passage(1), 0)).toBe(0);
  });
});

describe("passageUse", () => {
  const steps = [search([passage(1), passage(2)], "c1"), search([passage(1, { new: false }), passage(3)], "c2")];

  it("marks cited and uncited passages", () => {
    const cited = new Set([1]);
    expect(passageUse(steps[0].results[0], 0, steps, cited)).toEqual({ kind: "cited" });
    expect(passageUse(steps[0].results[1], 0, steps, cited)).toEqual({ kind: "unused" });
  });

  it("points a passage returned again to the step that first returned it", () => {
    expect(passageUse(steps[1].results[0], 1, steps, new Set([1]))).toEqual({ kind: "seen", step: 1 });
  });
});

describe("writtenWords", () => {
  it("marks the university's name the search left out", () => {
    const words = writtenWords(search([]).phrasings[0]);
    expect(words?.filter((w) => w.removed).map((w) => w.word)).toEqual(["AUI"]);
  });

  it("marks the name inside a word, keeping its punctuation", () => {
    const step = TRANSFER.trace!.steps[0] as SearchStep;
    const question = step.phrasings.find((p) => p.origins.includes("question"))!;
    expect(writtenWords(question)?.slice(-3)).toEqual([
      { word: "to", removed: false, attached: false },
      { word: "AUI", removed: true, attached: false },
      { word: "?", removed: false, attached: true },
    ]);
    const quoted = writtenWords({ text: "credits ( ).", origins: ["question"], as_written: "credits (AUI)." });
    expect(quoted?.map((w) => [w.word, w.removed, w.attached])).toEqual([
      ["credits", false, false],
      ["(", false, false],
      ["AUI", true, true],
      [").", false, true],
    ]);
  });

  it("is null when nothing was removed", () => {
    expect(writtenWords(search([]).phrasings[1])).toBeNull();
  });

  it("is null when the words can't be lined up", () => {
    expect(writtenWords({ text: "a b", origins: ["query"], as_written: "x y" })).toBeNull();
  });
});

describe("UnderTheHood", () => {
  const html = renderToStaticMarkup(
    <UnderTheHood trace={TRACE} citations={[{ marker: 1, source: "s", pages: [103], title: "t", section: null, link: null }]} />,
  );

  it("is closed by default, with the summary visible", () => {
    expect(html).toMatch(/^<details class="uth">/);
    expect(html).toContain("1 tool call · 2 queries · 2.0 s · 2,398 tokens");
  });

  it("shows the phrasings, the struck-out name, and which passage was cited", () => {
    expect(html).toContain("agent&#x27;s English version");
    expect(html).toContain('<s title="Removed before searching">AUI</s>');
    expect(html).toContain("cited [1]");
    expect(html).toContain("not cited");
  });

  it("strikes out the name in the transfer-credits example, with no space before the ?", () => {
    const shown = renderToStaticMarkup(
      <UnderTheHood trace={TRANSFER.trace!} citations={TRANSFER.citations} savedAt={TRANSFER.generated_at} />,
    );
    expect(shown).toContain('<s title="Removed before searching">AUI</s>');
    expect(shown.replace(/<[^>]+>/g, "")).toContain("How many credits can I transfer to AUI?");
  });

  it("says when the run stopped early", () => {
    const stopped = renderToStaticMarkup(<UnderTheHood trace={{ ...TRACE, status: "limit" }} citations={[]} />);
    expect(stopped).toContain("The run stopped at a usage limit");
  });
});
