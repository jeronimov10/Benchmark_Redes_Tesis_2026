import { aggregate, blockMean, scoreMetric } from "./model";
import type { BlockId, MetricDef } from "./types";

/** Step 6 of the thesis: propagate measurement and weight uncertainty with N replicas. */

export const REPLICAS = 10_000;
export const KAPPA_W = 50;
export const SEPARATION = 0.85;
const SEED = 20_261_007;

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeNormal(rand: () => number) {
  let spare: number | null = null;
  return () => {
    if (spare !== null) {
      const s = spare;
      spare = null;
      return s;
    }
    let u = 0;
    while (u === 0) u = rand();
    const v = rand();
    const r = Math.sqrt(-2 * Math.log(u));
    spare = r * Math.sin(2 * Math.PI * v);
    return r * Math.cos(2 * Math.PI * v);
  };
}

/** Marsaglia-Tsang gamma sampler (shape > 0, scale 1). */
function makeGamma(rand: () => number, normal: () => number) {
  const draw = (shape: number): number => {
    if (shape < 1) {
      let u = 0;
      while (u === 0) u = rand();
      return draw(shape + 1) * u ** (1 / shape);
    }
    const d = shape - 1 / 3;
    const c = 1 / Math.sqrt(9 * d);
    for (;;) {
      let x: number;
      let v: number;
      do {
        x = normal();
        v = 1 + c * x;
      } while (v <= 0);
      v = v * v * v;
      const u = rand();
      if (u < 1 - 0.0331 * x ** 4 || Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
    }
  };
  return draw;
}

export interface MetricSample {
  def: MetricDef;
  block: BlockId;
  mean: number;
  /** Absolute standard deviation. */
  sd: number;
  /** Thresholds already specialised for this payment (A1 uses the ticket-independent fraction). */
  t: number;
  w: number;
}

export interface NetworkSamples {
  id: string;
  metrics: MetricSample[];
}

export interface MonteCarloResult {
  /** scores[networkId] -> Float64Array of length N (NaN when the network has no data at all). */
  scores: Record<string, Float64Array>;
}

export function runMonteCarlo(
  networks: NetworkSamples[],
  weights: Record<BlockId, number>,
  n: number = REPLICAS,
): MonteCarloResult {
  const rand = mulberry32(SEED);
  const normal = makeNormal(rand);
  const gamma = makeGamma(rand, normal);
  const blocks = Object.keys(weights) as BlockId[];

  const scores: Record<string, Float64Array> = {};
  for (const net of networks) scores[net.id] = new Float64Array(n);

  for (let r = 0; r < n; r++) {
    // Dirichlet(KAPPA_W * W): same weights for every network in the replica.
    const g = blocks.map((b) => gamma(Math.max(KAPPA_W * weights[b], 1e-6)));
    const gs = g.reduce((a, b) => a + b, 0);
    const wr = Object.fromEntries(blocks.map((b, i) => [b, g[i] / gs])) as Record<BlockId, number>;

    for (const net of networks) {
      const per: Record<BlockId, number[]> = { A: [], B: [], C: [], D: [] };
      for (const m of net.metrics) {
        const x = m.sd > 0 ? Math.max(0, m.mean + m.sd * normal()) : m.mean;
        per[m.block].push(scoreMetric(m.def, x, m.t, m.w));
      }
      const bs = Object.fromEntries(blocks.map((b) => [b, blockMean(per[b])])) as Record<BlockId, number | null>;
      scores[net.id][r] = aggregate(bs, wr) ?? Number.NaN;
    }
  }
  return { scores };
}

export function quantile(sorted: Float64Array, q: number): number {
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function summarize(samples: Float64Array): { median: number; p5: number; p95: number } {
  const sorted = Float64Array.from(samples).sort();
  return { median: quantile(sorted, 0.5), p5: quantile(sorted, 0.05), p95: quantile(sorted, 0.95) };
}

/** P(A > B) over paired replicas. */
export function probability(a: Float64Array, b: Float64Array): number {
  let c = 0;
  for (let i = 0; i < a.length; i++) if (a[i] > b[i]) c++;
  return c / a.length;
}

/**
 * Bands: walk networks from highest to lowest median, opening a new band whenever the
 * next network is separated (pi >= 0.85) from every network of the current band.
 */
export function formBands(
  orderedIds: string[],
  samples: Record<string, Float64Array>,
): { bands: string[][]; pi: Record<string, Record<string, number>> } {
  const pi: Record<string, Record<string, number>> = {};
  for (const i of orderedIds) {
    pi[i] = {};
    for (const j of orderedIds) if (i !== j) pi[i][j] = probability(samples[i], samples[j]);
  }
  const bands: string[][] = [];
  for (const id of orderedIds) {
    const current = bands[bands.length - 1];
    if (current && !current.every((member) => pi[member][id] >= SEPARATION)) current.push(id);
    else bands.push([id]);
  }
  return { bands, pi };
}
