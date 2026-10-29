import { describe, expect, it } from "vitest";
import README from "../../README.md?raw";
import {
  CI_SCALE_MAX,
  DATA_COUNTS, DATA_COUNTS_README,
  FAITHFULNESS_ROW,
  FAITHFULNESS_RUNS,
  RESULTS,
} from "./about";

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

describe("the interval chart", () => {
  it.each(FAITHFULNESS_RUNS)("draws $label with the README's count, share and interval", (run) => {
    expect(README).toContain(FAITHFULNESS_ROW);
    const { count, total, percent, low, high } = run;
    expect(FAITHFULNESS_ROW).toContain(
      `${count}/${total} = ${percent}% (95% CI ${low.toFixed(1)}–${high.toFixed(1)}%)`,
    );
  });

  it("fits every interval on its 0–60% scale", () => {
    for (const run of FAITHFULNESS_RUNS) expect(run.high).toBeLessThanOrEqual(CI_SCALE_MAX);
  });

  it("only says the intervals overlap while they do", () => {
    const [before, after] = FAITHFULNESS_RUNS;
    expect(before.low).toBeLessThan(after.high);
  });
});

describe("the architecture diagram's counts", () => {
  it("are the README's", () => {
    for (const text of DATA_COUNTS_README) expect(README).toContain(text);
    const source = DATA_COUNTS_README.join(" ");
    for (const count of Object.values(DATA_COUNTS)) expect(source).toContain(String(count));
  });
});
