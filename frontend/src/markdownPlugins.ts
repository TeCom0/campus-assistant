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

// A citation marker after AssistantTurn has linked it ("[1](#source-2-1)",
// "[1](#pending-1)"), or one left as plain text because no citation matches.
const MARKER_LINK_RE = /^#(source|pending)-/;
const MARKER_TEXT_RE = /^\[\d+\]/;

function isMarker(node: Nodes | undefined) {
  if (node?.type === "link") return MARKER_LINK_RE.test(node.url);
  return node?.type === "text" && MARKER_TEXT_RE.test(node.value);
}

// The model ends most lines with two spaces (a hard line break) and sometimes
// puts the marker on the next line ("...the process.  \n   [1]"), so the chip
// showed on its own line under the bullet. A line break right before a marker
// becomes a space, which keeps the marker on the line it cites. Every other
// break stays, and a marker in its own paragraph (blank line before it) is
// left alone: it cites everything above, not only the last line.
export function remarkInlineCitations() {
  return (tree: Nodes) => joinMarkers(tree);
}

function joinMarkers(node: Nodes) {
  if (!("children" in node)) return;
  const parent = node as Parents;
  parent.children = parent.children.map((child, i) =>
    child.type === "break" && isMarker(parent.children[i + 1]) ? { type: "text", value: " " } : child,
  ) as Parents["children"];
  parent.children.forEach(joinMarkers);
}

// remark-gfm: tables, which the agent often uses for lists of rules or courses.
// remarkInlineCitations runs last, so a "<br>" before a marker is joined too.
export const ANSWER_REMARK_PLUGINS = [remarkGfm, remarkHtmlBreaks, remarkInlineCitations];
