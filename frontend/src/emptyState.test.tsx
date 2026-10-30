import { renderToStaticMarkup } from "react-dom/server";
import Markdown from "react-markdown";
import { describe, expect, it } from "vitest";
import { firstParagraph, pagesLabel, stepsSummary } from "./answerFormat";
import { EmptyState, PROOF_EXAMPLE_ID } from "./components/EmptyState";
import { EXAMPLE_QUESTIONS, savedExample } from "./examples";

const html = renderToStaticMarkup(<EmptyState onAsk={() => {}} />);

describe("firstParagraph", () => {
  it("keeps the first paragraph and drops its markers", () => {
    expect(firstParagraph("You need **ACC 2301** [1].\n\n- MTH 1305 [1]")).toBe("You need **ACC 2301**.");
  });
});

describe("first screen", () => {
  it("quotes the saved example, not hand-typed text", () => {
    const saved = savedExample(PROOF_EXAMPLE_ID)!;
    const excerpt = renderToStaticMarkup(<Markdown>{firstParagraph(saved.answer)}</Markdown>);
    expect(html).toContain(excerpt);
    expect(html).toContain(saved.question);
    expect(html).toContain(`<span class="proof-page">${pagesLabel(saved.citations[0].pages)}</span>`);
  });

  it("tags each example with the path its saved answer took", () => {
    for (const example of EXAMPLE_QUESTIONS) {
      const saved = savedExample(example.id);
      if (saved) expect(html).toContain(`>${stepsSummary(saved.tool_calls)}</span>`);
    }
    expect(html).toContain(">1 course lookup</span>");
  });
});
