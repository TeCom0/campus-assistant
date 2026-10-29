// What the About page says about the project's measured results. Every
// figure is from the README's Evaluation section, and `readme` holds the
// exact README text it comes from: about.test.ts fails if the README stops
// containing that text, or if a figure here isn't in it, so the page can't
// quietly drift from the documented results.

export const REPO_URL = "https://github.com/TeCom0/campus-assistant";
// Set once the demo video exists; until then the page says "coming soon".
export const DEMO_VIDEO_URL: string | null = null;

// The README's faithfulness row: the result tile and the interval chart both
// come from it.
export const FAITHFULNESS_ROW =
  "| `main` answers with ≥ 1 unsupported cited claim (judge) | 17/47 = 36.2% (95% CI 24.0–50.5%) | 6/26 = 23.1% (95% CI 11.0–42.1%) |";

export interface Result {
  value: string;
  label: string;
  detail: string;
  readme: string[];
}

export const RESULTS: Result[] = [
  {
    value: "85.7%",
    label: "Retrieval Hit@5",
    detail: "12/14. Current 14-question set (EN/FR); vector search alone: 64.3%.",
    readme: [
      "**Current 14-question set (12 original + 2 added 2026-10-21), today's system:**",
      "| **Hybrid + English version, after** | 78.6% | 85.7% | **0.717** |",
      "| Vector alone (pgvector, cosine) | 64.3% | 64.3% | 0.594 |",
    ],
  },
  {
    value: "36.2% → 23.1%",
    label: "Answers with an unsupported cited claim",
    detail:
      "LLM judge, 17/47 before vs. 6/26 after three fixes. The 95% intervals overlap " +
      "(24.0–50.5% vs. 11.0–42.1%): suggestive, not proven.",
    readme: [FAITHFULNESS_ROW],
  },
  {
    value: "6 → 0",
    label: "Crashes",
    detail: "Before vs. after the fixes, over all evaluation sets.",
    readme: ["| Crashes (all sets) | 6 | **0** |"],
  },
  {
    value: "5/55 → 0/30",
    label: "False refusals",
    detail: "Answerable questions the assistant declined, before vs. after the fixes.",
    readme: ["| False refusals (answerable questions declined) | 5/55 | **0/30** |"],
  },
];

// The README's "Known limitations", shortened.
export const LIMITATIONS = [
  "Cited answers can still contain a wrong detail (the faithfulness result above).",
  "Everyday wording can miss a passage written in the catalog's vocabulary.",
  "Undergraduate and graduate rules aren't filtered by level yet.",
  "One catalog edition, 2024–2025; newer editions exist.",
];

export const STACK = [
  "FastAPI",
  "LangGraph",
  "Groq gpt-oss-20b",
  "pgvector",
  "Postgres full-text",
  "multilingual-e5-small",
  "React + TypeScript",
  "Docker",
  "GitHub Actions",
  "pytest · vitest",
];

// The interval chart's two runs: `main` answers with at least one unsupported
// cited claim, and the 95% interval around that share.
export interface Run {
  label: string;
  run: string;
  count: number;
  total: number;
  percent: number;
  low: number;
  high: number;
}

// The chart's scale runs 0–60%; about.test.ts checks every interval fits.
export const CI_SCALE_MAX = 60;

export const FAITHFULNESS_RUNS: Run[] = [
  {
    label: "Before the fixes",
    run: "run 1",
    count: 17,
    total: 47,
    percent: 36.2,
    low: 24.0,
    high: 50.5,
  },
  {
    label: "After fixes A–C",
    run: "run 3",
    count: 6,
    total: 26,
    percent: 23.1,
    low: 11.0,
    high: 42.1,
  },
];

// What ingestion stored, shown in the architecture diagram, with the README
// text each count comes from.
export const DATA_COUNTS = { passages: 1161, courses: 660, links: 526 };
export const DATA_COUNTS_README = ["document_chunks<br/>1161 chunks", "660 courses, 526 links"];
