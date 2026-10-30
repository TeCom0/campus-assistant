import type { Step } from "./messages";

// Small text helpers shared by the answers (AssistantTurn) and the first
// screen (EmptyState), which shows parts of a saved answer.

// "p. 103", "p. 103–104", "p. 31, 38"; "" when the passage has no page.
export function pagesLabel(pages: number[] | null): string {
  if (!pages || pages.length === 0) return "";
  if (pages.length === 1) return `p. ${pages[0]}`;
  const consecutive = pages.every((p, i) => i === 0 || p === pages[i - 1] + 1);
  return consecutive ? `p. ${pages[0]}–${pages[pages.length - 1]}` : `p. ${pages.join(", ")}`;
}

// "2 searches", "1 course lookup", "1 search · 1 course lookup".
export function stepsSummary(steps: Pick<Step, "tool">[]): string {
  const searches = steps.filter((s) => s.tool === "search_documents").length;
  const lookups = steps.filter((s) => s.tool === "query_courses").length;
  const parts = [];
  if (searches) parts.push(`${searches} ${searches === 1 ? "search" : "searches"}`);
  if (lookups) parts.push(`${lookups} course ${lookups === 1 ? "lookup" : "lookups"}`);
  return parts.join(" · ") || `${steps.length} steps`;
}

// An answer's first paragraph without its [N] markers, for an excerpt shown
// next to its source (the first screen's proof card) rather than with chips.
export function firstParagraph(answer: string): string {
  const [first] = answer.trim().split(/\n\s*\n/);
  return first.replace(/\s*\[\d+\]/g, "").trim();
}
