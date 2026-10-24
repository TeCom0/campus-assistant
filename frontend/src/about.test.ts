import { describe, expect, it } from "vitest";
import README from "../../README.md?raw";
import { RESULTS } from "./about";

// The About page's results against the README they're copied from (?raw:
// Vite imports the file as a string; vite/client already declares the type).

// "85.7%", "17/47": the figures a reader would quote. Plain counts ("6 → 0")
// are covered by the README text check alone.
const FIGURE = /\d+(?:\.\d+)?%|\d+\/\d+/g;

describe.each(RESULTS)("$label", (result) => {
  it("is still in the README, word for word", () => {
    for (const text of result.readme) expect(README).toContain(text);
  });

  it("shows only figures the README text has, or a fraction of one of its percentages", () => {
    const source = result.readme.join("\n");
    const percents = (source.match(/\d+(?:\.\d+)?%/g) ?? []).map((p) => parseFloat(p));
    for (const figure of `${result.value} ${result.detail}`.match(FIGURE) ?? []) {
      if (source.includes(figure)) continue;
      // e.g. "12/14" next to "85.7%": 12 / 14 = 85.7%.
      const [n, d] = figure.split("/").map(Number);
      expect(d, `${figure} is not in the README text`).toBeDefined();
      const percent = Math.round((n / d) * 1000) / 10;
      expect(percents, `${figure} (= ${percent}%) matches no README percentage`).toContain(percent);
    }
  });
});
