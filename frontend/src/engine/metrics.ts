import type { BlockId, MetricDef, MetricId } from "./types";

/**
 * Catalog of the thesis (Table 7). t = target (score 1), w = unacceptable (score 0).
 * A1 thresholds apply to the fee as a fraction of the payment ticket.
 * B2/B2b in seconds. C3 is scored on the number of nines (see model.ts).
 * D1-D3 and C4 in percent.
 */
export const METRICS: MetricDef[] = [
  { id: "A1", block: "A", dir: "lower", unit: "fraction", t: 0.001, w: 0.01, source: "chain" },
  { id: "A2", block: "A", dir: "lower", unit: "ratio", t: 1.5, w: 10, source: "chain" },
  { id: "A3", block: "A", dir: "lower", unit: "index", t: 0.2, w: 2, source: "chain" },
  { id: "A4", block: "A", dir: "lower", unit: "usd", t: 0.001, w: 0.1, source: "chain" },
  { id: "B1", block: "B", dir: "lower", unit: "seconds", t: 3, w: 20, source: "chain" },
  { id: "B2", block: "B", dir: "lower", unit: "seconds", t: 20, w: 86_400, source: "chain" },
  { id: "B2b", block: "B", dir: "lower", unit: "seconds", t: 20, w: 86_400, source: "chain" },
  { id: "B3", block: "B", dir: "higher", unit: "ratio", t: 5, w: 1, source: "chain" },
  { id: "C1", block: "C", dir: "lower", unit: "index", t: 0.1, w: 1, source: "chain" },
  { id: "C2", block: "C", dir: "higher", unit: "count", t: 15, w: 1, source: "chain" },
  { id: "C3", block: "C", dir: "higher", unit: "percent", t: 99.999, w: 99.9, source: "doc" },
  { id: "C4", block: "C", dir: "lower", unit: "percent", t: 0.1, w: 5, source: "chain" },
  { id: "C5", block: "C", dir: "lower", unit: "count", t: 0, w: 5, source: "chain" },
  { id: "D1", block: "D", dir: "higher", unit: "percent", t: 50, w: 1, source: "chain" },
  { id: "D2", block: "D", dir: "higher", unit: "percent", t: 20, w: 0.1, source: "chain" },
  { id: "D3", block: "D", dir: "higher", unit: "percent", t: 10, w: 0.1, source: "chain" },
];

export const METRIC_BY_ID = Object.fromEntries(METRICS.map((m) => [m.id, m])) as Record<MetricId, MetricDef>;
export const BLOCKS: BlockId[] = ["A", "B", "C", "D"];

/** Pix-derived peak factor and Bre-B figures that fix the capacity requirement (thesis 5.3.3). */
export const REQUIRED_TPS = 18;
