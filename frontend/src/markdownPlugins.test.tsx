import { renderToStaticMarkup } from "react-dom/server";
import Markdown from "react-markdown";
import { describe, expect, it } from "vitest";
import { ANSWER_REMARK_PLUGINS } from "./markdownPlugins";

// Renders an answer the way AssistantTurn does (same remark plugins, raw HTML
// still disabled) and returns the HTML string.
function render(markdown: string) {
  return renderToStaticMarkup(<Markdown remarkPlugins={ANSWER_REMARK_PLUGINS}>{markdown}</Markdown>);
}

describe("remarkHtmlBreaks", () => {
  it("turns <br> in a table cell into a line break", () => {
    // Shape of the live answer that showed a literal "<br>" (2026-10-20).
    const html = render(
      "| Course | Prerequisites |\n|---|---|\n| CSC 3326 | CSC 2306<br>MTH 2301 |",
    );
    // react-markdown writes a newline after each <br/>; the browser ignores it.
    expect(html).toContain("<td>CSC 2306<br/>\nMTH 2301</td>");
    expect(html).not.toContain("&lt;br");
  });

  it("accepts <br/>, <br /> and any case", () => {
    const html = render("| a |\n|---|\n| 1<br/>2<br />3<BR>4 |");
    expect(html).toContain("<td>1<br/>\n2<br/>\n3<br/>\n4</td>");
  });

  it("works in a paragraph too", () => {
    expect(render("first<br>second")).toBe("<p>first<br/>\nsecond</p>");
  });

  it("keeps every other HTML tag escaped", () => {
    const html = render('a <b>bold</b> <img src=x onerror="alert(1)"> <br class="x">');
    expect(html).not.toContain("<b>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;b&gt;");
    // A <br> with attributes isn't a plain line break: left as text.
    expect(html).toContain("&lt;br class=");
  });

  it("leaves <br> inside code alone", () => {
    expect(render("`a<br>b`")).toBe("<p><code>a&lt;br&gt;b</code></p>");
  });
});
