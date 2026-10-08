import { METRIC_BY_ID } from "./metrics";
import type { BlockId, MetricId, MetricResult, NetworkEvaluation, Recommendation } from "./types";

export interface BlockContribution {
  block: BlockId;
  /** Share of the weight carried by this block in the best network's score. */
  weight: number;
  score: number | null;
}

export interface Explanation {
  /** Blocks of the winner, ordered by weight x score contribution. */
  blocks: BlockContribution[];
  determinant: { metric: MetricId; delta: number } | null;
  /** Blocks where the runner-up beats the winner, and vice versa. */
  vsRunnerUp: { network: NetworkEvaluation; winnerAhead: BlockId[]; runnerAhead: BlockId[] } | null;
}

/** Structured explanation: the UI turns these ids into translated sentences. */
export function explain(rec: Recommendation): Explanation | null {
  const best = rec.best;
  if (!best) return null;
  const blocks = best.blocks
    .map((b) => ({ block: b.id, weight: rec.weights[b.id], score: b.score }))
    .sort((a, b) => rec.weights[b.block] * (b.score ?? 0) - rec.weights[a.block] * (a.score ?? 0));

  const runner = rec.ranking[1];
  let vsRunnerUp: Explanation["vsRunnerUp"] = null;
  if (runner) {
    const winnerAhead: BlockId[] = [];
    const runnerAhead: BlockId[] = [];
    for (const b of best.blocks) {
      const other = runner.blocks.find((x) => x.id === b.id);
      if (b.score === null || !other || other.score === null) continue;
      if (b.score - other.score > 0.02) winnerAhead.push(b.id);
      else if (other.score - b.score > 0.02) runnerAhead.push(b.id);
    }
    vsRunnerUp = { network: runner, winnerAhead, runnerAhead };
  }
  return { blocks, determinant: rec.determinant, vsRunnerUp };
}

/** Metrics that sink a network: red ones first. */
export function redMetrics(e: NetworkEvaluation): MetricResult[] {
  return e.metrics.filter((m) => m.light === "red");
}

export function metricName(id: MetricId): string {
  return METRIC_BY_ID[id].id;
}
