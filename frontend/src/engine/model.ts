import type { BlockId, Certainty, MetricDef, ScenarioId } from "./types";

/**
 * The mathematical model of the thesis (section 5.4), step by step.
 * Nothing here reads data or React: pure functions.
 */

/* ---------- Step 1: common scale ---------- */

/** Number of nines of an availability given in percent. */
export function nines(percent: number): number {
  const a = Math.min(percent, 99.99999);
  return -Math.log10(1 - a / 100);
}

const clip01 = (z: number) => Math.min(1, Math.max(0, z));

/**
 * Score of one measurement against the thresholds, 0..1.
 * Logarithmic scale; falls back to linear when a threshold is 0 (C5), and handles
 * x = 0 explicitly (the limit of the formula is 1 when lower is better, 0 otherwise).
 */
export function normalize(x: number, t: number, w: number, dir: "lower" | "higher"): number {
  if (dir === "lower") {
    if (x <= t) return 1;
    if (x >= w) return 0;
    if (x > 0 && t > 0) return clip01((Math.log(w) - Math.log(x)) / (Math.log(w) - Math.log(t)));
    return clip01((w - x) / (w - t));
  }
  if (x >= t) return 1;
  if (x <= w) return 0;
  if (x > 0 && w > 0) return clip01((Math.log(x) - Math.log(w)) / (Math.log(t) - Math.log(w)));
  return clip01((x - w) / (t - w));
}

/** Score of a catalog metric. C3 is normalized over the number of nines. */
export function scoreMetric(def: MetricDef, x: number, t = def.t, w = def.w): number {
  if (def.id === "C3") return normalize(nines(x), nines(t), nines(w), "higher");
  return normalize(x, t, w, def.dir);
}

/* ---------- Step 3: aggregation ---------- */

export const EPSILON = 0.05;

export function blockMean(scores: number[]): number | null {
  return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
}

/** Weighted geometric mean over blocks with floor epsilon. Blocks without data are dropped. */
export function aggregate(
  blockScores: Record<BlockId, number | null>,
  weights: Record<BlockId, number>,
): number | null {
  const ids = (Object.keys(weights) as BlockId[]).filter((b) => blockScores[b] !== null);
  if (ids.length === 0) return null;
  const wsum = ids.reduce((s, b) => s + weights[b], 0);
  let log = 0;
  for (const b of ids) log += (weights[b] / wsum) * Math.log(Math.max(blockScores[b] as number, EPSILON));
  return Math.exp(log);
}

/* ---------- Step 4: weights of an arbitrary payment ---------- */

export const M_MIN = 1e4;
export const M_MAX = 1e9;
export const L_MIN = 1;
export const L_MAX = 86_400;

/** Reference scenarios as points of (amount, crosses border, wait, irreversibility). Thesis 5.4. */
export const SCENARIO_POINTS: Record<ScenarioId, [number, number, number, number]> = {
  E1: [0.53, 1, 0.74, 0],
  E2: [0.26, 0, 0, 0.5],
  E3: [0.8, 0, 0.54, 1],
};

export const SCENARIO_WEIGHTS: Record<ScenarioId, Record<BlockId, number>> = {
  E1: { A: 0.45, B: 0.15, C: 0.15, D: 0.25 },
  E2: { A: 0.35, B: 0.35, C: 0.15, D: 0.15 },
  E3: { A: 0.1, B: 0.3, C: 0.4, D: 0.2 },
};

const GAMMA = [1.0, 1.5, 1.0, 1.2];
const P = 2;
const D0 = 0.6;
const SCENARIOS: ScenarioId[] = ["E1", "E2", "E3"];

export function paymentVector(
  amountCop: number,
  crossBorder: boolean,
  waitSec: number,
  irreversibility: number,
): [number, number, number, number] {
  const m = clip01((Math.log(Math.max(amountCop, 1)) - Math.log(M_MIN)) / (Math.log(M_MAX) - Math.log(M_MIN)));
  const l = clip01((Math.log(Math.max(waitSec, 1)) - Math.log(L_MIN)) / (Math.log(L_MAX) - Math.log(L_MIN)));
  return [m, crossBorder ? 1 : 0, l, irreversibility];
}

export function distance(a: number[], b: number[]): number {
  return Math.sqrt(a.reduce((s, ak, k) => s + GAMMA[k] * (ak - b[k]) ** 2, 0));
}

export interface Interpretation {
  lambda: Record<ScenarioId, number>;
  weights: Record<BlockId, number>;
  dMin: number;
  kappa: number;
  certainty: Certainty;
}

/** Steps 4 and 5: interpolate scenario weights and report how well the scenarios represent the case. */
export function interpret(a: number[]): Interpretation {
  const d = Object.fromEntries(SCENARIOS.map((e) => [e, distance(a, SCENARIO_POINTS[e])])) as Record<ScenarioId, number>;
  const raw = Object.fromEntries(SCENARIOS.map((e) => [e, (d[e] + EPSILON) ** -P])) as Record<ScenarioId, number>;
  const total = SCENARIOS.reduce((s, e) => s + raw[e], 0);
  const lambda = Object.fromEntries(SCENARIOS.map((e) => [e, raw[e] / total])) as Record<ScenarioId, number>;

  const weights = { A: 0, B: 0, C: 0, D: 0 } as Record<BlockId, number>;
  for (const e of SCENARIOS) for (const b of Object.keys(weights) as BlockId[]) weights[b] += lambda[e] * SCENARIO_WEIGHTS[e][b];

  const dMin = Math.min(...SCENARIOS.map((e) => d[e]));
  const H = -SCENARIOS.reduce((s, e) => s + (lambda[e] > 0 ? lambda[e] * Math.log(lambda[e]) : 0), 0);
  const kappa = Math.exp(-dMin / D0) * Math.sqrt(Math.max(0, 1 - H / Math.log(3)));
  const certainty: Certainty = kappa >= 0.75 ? "high" : kappa >= 0.45 ? "medium" : "low";
  return { lambda, weights, dMin, kappa, certainty };
}

/* ---------- traffic light (Redfacil rule, not part of the thesis) ---------- */

export function lightFromScore(score: number): "green" | "yellow" | "red" {
  return score >= 0.7 ? "green" : score < 0.45 ? "red" : "yellow";
}

/** Light of a single measurement: meets target, beyond unacceptable, or in between. */
export function lightOfValue(
  def: MetricDef,
  x: number,
  t = def.t,
  w = def.w,
): "green" | "yellow" | "red" {
  const v = def.id === "C3" ? nines(x) : x;
  const tt = def.id === "C3" ? nines(t) : t;
  const ww = def.id === "C3" ? nines(w) : w;
  if (def.dir === "lower") return v <= tt ? "green" : v >= ww ? "red" : "yellow";
  return v >= tt ? "green" : v <= ww ? "red" : "yellow";
}
