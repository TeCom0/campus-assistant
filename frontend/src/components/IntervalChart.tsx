import { CI_SCALE_MAX, FAITHFULNESS_RUNS } from "../about";

// The faithfulness result as two 95% intervals on one 0–60% scale, so a
// reader sees both the drop and how much the intervals overlap. Drawn in a
// 480-wide viewBox that scales to the column; colors are theme tokens (CSS).
const TICKS = [0, 10, 20, 30, 40, 50, 60];
const x = (percent: number) => 20 + (percent / CI_SCALE_MAX) * 420; // 0% at 20, 60% at 440
const ROW_TOP = [0, 58]; // each run: its label, then its interval 22 below
const formatPercent = (value: number) => `${value.toFixed(1)}%`;

export function IntervalChart() {
  const [before, after] = FAITHFULNESS_RUNS;
  // The range both intervals cover.
  const overlapLow = Math.max(before.low, after.low);
  const overlapHigh = Math.min(before.high, after.high);
  const summary = FAITHFULNESS_RUNS.map(
    (run) =>
      `${run.label}: ${run.count} of ${run.total} answers, ${formatPercent(run.percent)} ` +
      `(95% interval ${formatPercent(run.low)} to ${formatPercent(run.high)})`,
  ).join(". ");

  return (
    <figure className="figure">
      <h3>Answers with an unsupported cited claim, with 95% intervals</h3>
      <svg className="ci-chart" viewBox="0 0 480 146" role="img" aria-label={`${summary}.`}>
        {overlapLow < overlapHigh && (
          <rect
            className="ci-overlap"
            x={x(overlapLow)}
            y={28}
            width={x(overlapHigh) - x(overlapLow)}
            height={82}
          />
        )}
        {TICKS.map((tick) => (
          <g key={tick}>
            <line className="ci-grid" x1={x(tick)} x2={x(tick)} y1={28} y2={114} />
            <text className="ci-tick" x={x(tick)} y={132} textAnchor="middle">
              {tick}%
            </text>
          </g>
        ))}
        {FAITHFULNESS_RUNS.map((run, i) => {
          const top = ROW_TOP[i];
          const y = top + 40;
          return (
            <g key={run.label} className={i === 0 ? "ci-run before" : "ci-run after"}>
              <title>
                {`${run.label} (${run.run}): ${run.count}/${run.total} = ` +
                  `${formatPercent(run.percent)}, ` +
                  `95% CI ${formatPercent(run.low)}–${formatPercent(run.high)}`}
              </title>
              <text className="ci-label" x={20} y={top + 18}>
                {run.label}
                <tspan className="ci-label-note" dx={6}>
                  {`${run.count} of ${run.total} answers`}
                </tspan>
              </text>
              <line className="ci-range" x1={x(run.low)} x2={x(run.high)} y1={y} y2={y} />
              <line className="ci-range" x1={x(run.low)} x2={x(run.low)} y1={y - 6} y2={y + 6} />
              <line className="ci-range" x1={x(run.high)} x2={x(run.high)} y1={y - 6} y2={y + 6} />
              <circle className="ci-dot" cx={x(run.percent)} cy={y} r={5} />
              <text className="ci-value" x={x(run.high) + 10} y={y + 4.5}>
                {formatPercent(run.percent)}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption>
        Share of answers with at least one cited claim the judge found unsupported. The shaded band
        is where the two intervals overlap ({formatPercent(overlapLow)}–
        {formatPercent(overlapHigh)}): with {before.total} and {after.total} answers, the drop is
        suggestive, not proven.
      </figcaption>
    </figure>
  );
}

