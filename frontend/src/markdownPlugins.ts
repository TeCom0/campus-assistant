import type { Nodes, Parents } from "mdast";
import remarkGfm from "remark-gfm";

// "<br>", "<br/>", "<br />", any case. Only a whole HTML node matches, so
// "<br>" inside other HTML or inside `code` is left alone.
const BR_TAG_RE = /^<br\s*\/?>$/i;

// The model often writes "<br>" for a line break inside a table cell, where
// Markdown has no other way to break a line. Raw HTML stays disabled (it would
// let an answer inject markup), so react-markdown would print the tag as text.
// After parsing, each "<br>" is an `html` node in the Markdown tree: this
// replaces exactly those nodes with Markdown's own line break (`break`, the
// node a trailing "\" makes), which renders as a real <br>. Any other HTML is
// untouched and still shown as text.
export function remarkHtmlBreaks() {
  return (tree: Nodes) => replaceBreaks(tree);
}

function replaceBreaks(node: Nodes) {
  if (!("children" in node)) return;
  const parent = node as Parents;
  parent.children = parent.children.map((child) =>
    child.type === "html" && BR_TAG_RE.test(child.value.trim()) ? { type: "break" } : child,
  ) as Parents["children"];
  parent.children.forEach(replaceBreaks);
}

// remark-gfm: tables, which the agent often uses for lists of rules or courses.
export const ANSWER_REMARK_PLUGINS = [remarkGfm, remarkHtmlBreaks];
