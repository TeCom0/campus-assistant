import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ArchitectureSvg } from "./components/ArchitectureDiagram";

// On a phone the drawing is on the page twice (column + enlarged view), so
// each copy must define its own ids and only point at those.
describe("ArchitectureSvg", () => {
  it("defines only prefixed ids and references only ids it defines", () => {
    const html = renderToStaticMarkup(<ArchitectureSvg idPrefix="zoom" />);
    const defined = [...html.matchAll(/ id="([^"]+)"/g)].map((m) => m[1]);
    const referenced = [
      ...[...html.matchAll(/url\(#([^)]+)\)/g)].map((m) => m[1]),
      ...[...html.matchAll(/aria-labelledby="([^"]+)"/g)].flatMap((m) => m[1].split(" ")),
    ];

    expect(defined).toEqual(["zoom-title", "zoom-desc", "zoom-head"]);
    expect(referenced.length).toBeGreaterThan(10); // the label pair and every arrow
    for (const id of referenced) expect(defined).toContain(id);
  });
});
