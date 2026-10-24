// What the About page says about the project's measured results. Every
// figure is from the README's Evaluation section, and `readme` holds the
// exact README text it comes from: about.test.ts fails if the README stops
// containing that text, or if a figure here isn't in it, so the page can't
// quietly drift from the documented results.

export const REPO_URL = "https://github.com/TeCom0/campus-assistant";
// Set once the demo video exists; until then the page says "coming soon".
export const DEMO_VIDEO_URL: string | null = null;

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
    readme: [
      "| `main` answers with ≥ 1 unsupported cited claim (judge) | 17/47 = 36.2% (95% CI 24.0–50.5%) | 6/26 = 23.1% (95% CI 11.0–42.1%) |",
    ],
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
