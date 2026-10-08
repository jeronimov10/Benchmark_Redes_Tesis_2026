import type { MetricResult, NetworkEvaluation, Recommendation } from "./types";

export type Axis = "cost" | "speed" | "security";
const AXES: Axis[] = ["cost", "speed", "security"];
const EPS = 0.01;

export interface Comparison {
  network: NetworkEvaluation;
  /** Axes where the recommended network is ahead of this alternative. */
  winnerAhead: Axis[];
  /** Axes where this alternative is ahead of the recommended one. */
  altAhead: Axis[];
}

export interface Explanation {
  /** Axes ordered by how much they contributed to the winner's score. */
  determinants: { axis: Axis; share: number }[];
  comparisons: Comparison[];
}

/** Structured explanation. The UI turns these ids into translated sentences. */
export function explain(rec: Recommendation): Explanation | null {
  const best = rec.best;
  if (!best) return null;
  const total = AXES.reduce((s, a) => s + best.contributions[a], 0) || 1;
  const determinants = AXES.map((axis) => ({ axis, share: best.contributions[axis] / total })).sort(
    (a, b) => b.share - a.share,
  );
  const comparisons = rec.ranking.slice(1).map((alt) => ({
    network: alt,
    winnerAhead: AXES.filter((a) => best.contributions[a] - alt.contributions[a] > EPS),
    altAhead: AXES.filter((a) => alt.contributions[a] - best.contributions[a] > EPS),
  }));
  return { determinants, comparisons };
}

/** Why a network is a red (excluded) one: red metrics, critical ones first. */
export function redReasons(e: NetworkEvaluation): MetricResult[] {
  return e.blocks
    .flatMap((b) => b.metrics)
    .filter((m) => m.light === "red")
    .sort((a, b) => Number(b.critical) - Number(a.critical));
}

export function yellowReasons(e: NetworkEvaluation): MetricResult[] {
  return e.blocks.flatMap((b) => b.metrics).filter((m) => m.light === "yellow");
}
