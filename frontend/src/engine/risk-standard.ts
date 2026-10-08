import { NETWORKS } from "@/data/networks";
import { COUNTRIES } from "@/data/countries";
import {
  FEE_THRESHOLDS,
  FINALITY_THRESHOLDS,
  LATENCY_THRESHOLDS,
} from "./scenarios";
import type {
  BlockId,
  BlockResult,
  DimensionId,
  DimensionResult,
  Light,
  MetricDef,
  MetricResult,
  NetworkProfile,
  ProfileAnswers,
  ScenarioId,
  Tolerance,
  TxInput,
} from "./types";

/**
 * THE QUALIFICATION STANDARD.
 *
 * Every metric has a target (t) and an unacceptable (w) threshold. A value
 * that meets t is green, a value beyond w is red, in between is yellow.
 * Metrics roll up into the four benchmark blocks (A, B, C, D) and, for the
 * comparison view, into five dimensions. The same evaluation feeds both views.
 *
 * Rollup rule (blocks and dimensions):
 *   - a red *critical* metric makes the block red;
 *   - otherwise a red metric caps the block at yellow;
 *   - otherwise mean score >= 0.8 green, <= 0.4 red, else yellow.
 * Network rule: any red block => red (excluded); 2+ yellow blocks => yellow;
 * otherwise green.
 */

export const METRICS: MetricDef[] = [
  { id: "A1", block: "A", dimension: "cost", dir: "lower", unit: "fraction" },
  { id: "A2", block: "A", dimension: "liquidity", dir: "lower", unit: "ratio" },
  { id: "A3", block: "A", dimension: "cost", dir: "lower", unit: "index" },
  { id: "B1", block: "B", dimension: "speed", dir: "lower", unit: "seconds" },
  { id: "B2", block: "B", dimension: "speed", dir: "lower", unit: "seconds" },
  { id: "B3", block: "B", dimension: "liquidity", dir: "higher", unit: "ratio" },
  { id: "C1b", block: "C", dimension: "security", dir: "lower", unit: "index" },
  { id: "C2", block: "C", dimension: "security", dir: "higher", unit: "count" },
  { id: "C3", block: "C", dimension: "security", dir: "higher", unit: "nines" },
  { id: "C4", block: "C", dimension: "security", dir: "lower", unit: "percent" },
  { id: "C5", block: "C", dimension: "security", dir: "lower", unit: "count" },
  { id: "D1", block: "D", dimension: "cost", dir: "higher", unit: "percent" },
  { id: "D2", block: "D", dimension: "destination", dir: "higher", unit: "score" },
  { id: "D3", block: "D", dimension: "destination", dir: "higher", unit: "percent" },
  { id: "E1", block: "D", dimension: "security", dir: "higher", unit: "score" },
  { id: "X1", block: "D", dimension: "destination", dir: "lower", unit: "score", extension: true },
  { id: "X2", block: "D", dimension: "destination", dir: "higher", unit: "score", extension: true },
];

export const BLOCKS: BlockId[] = ["A", "B", "C", "D"];
export const DIMENSIONS: DimensionId[] = ["cost", "speed", "security", "liquidity", "destination"];

/** Static thresholds [target, unacceptable] for metrics that do not depend on the scenario. */
export const STATIC_THRESHOLDS: Record<string, [number, number]> = {
  A2: [1.5, 10],
  A3: [0.2, 2],
  B3: [5, 1],
  C1b: [0.1, 1],
  C2: [15, 1],
  C3: [5, 3],
  C4: [0.1, 5],
  C5: [0, 5],
  D1: [50, 1],
  D2: [0.5, 0.01],
  D3: [10, 0.1],
  E1: [0.5, 0.05],
  X1: [25, 60],
  X2: [0.7, 0.1],
};

export const REQUIRED_TPS = 48;
const URGENCY_FACTOR = { low: 4, normal: 1, urgent: 0.5 } as const;
const RECIPIENT_BASE = { person: 10, business: 5, exchange: 0, ownWallet: 5, unknown: 30 } as const;
const TOLERANCE_FACTOR: Record<Tolerance, number> = { low: 0.8, medium: 1, high: 1.2 };

export function normalize(x: number, t: number, w: number, dir: "lower" | "higher"): number {
  if (dir === "lower") {
    if (x <= t) return 1;
    if (x >= w) return 0;
    if (x > 0 && t > 0) return (Math.log(w) - Math.log(x)) / (Math.log(w) - Math.log(t));
    return (w - x) / (w - t);
  }
  if (x >= t) return 1;
  if (x <= w) return 0;
  if (x > 0 && w > 0) return (Math.log(x) - Math.log(w)) / (Math.log(t) - Math.log(w));
  return (x - w) / (t - w);
}

export function lightOf(x: number, t: number, w: number, dir: "lower" | "higher"): Light {
  if (dir === "lower") return x <= t ? "green" : x >= w ? "red" : "yellow";
  return x >= t ? "green" : x <= w ? "red" : "yellow";
}

function lightFromScore(score: number): Light {
  return score >= 0.8 ? "green" : score <= 0.4 ? "red" : "yellow";
}

export interface EvalContext {
  scenario: ScenarioId;
  amountUsd: number;
  tx: TxInput;
  profile: ProfileAnswers;
}

export function feeUsdOf(net: NetworkProfile, amountUsd: number): number {
  return net.feeFixedUsd + net.feePct * amountUsd;
}

function auditNeeded(ctx: EvalContext): boolean {
  if (ctx.profile.privacyPref === "auditable") return true;
  return ctx.scenario === "high_value" && ctx.profile.privacyPref !== "private";
}

export function evaluateMetrics(net: NetworkProfile, ctx: EvalContext): MetricResult[] {
  const { scenario, amountUsd, tx, profile } = ctx;
  const urgency = URGENCY_FACTOR[tx.urgency];
  const tol = TOLERANCE_FACTOR[profile.riskTolerance];
  const audit = auditNeeded(ctx);
  const known = tx.recipient.accepted !== "unknown";

  const raw: Record<string, { value: number; t: number; w: number; critical?: boolean; note?: string }> = {};
  const set = (id: string, value: number, extra: Partial<{ t: number; w: number; critical: boolean; note: string }> = {}) => {
    const [t, w] = STATIC_THRESHOLDS[id] ?? [0, 0];
    raw[id] = { value, t: extra.t ?? t, w: extra.w ?? w, critical: extra.critical, note: extra.note };
  };

  const [ft, fw] = FEE_THRESHOLDS[scenario];
  set("A1", feeUsdOf(net, amountUsd) / amountUsd, { t: ft, w: fw });
  set("A2", net.feeDispersion * (1 + (5 * amountUsd) / net.usdtDepthUsd), {
    note: amountUsd > net.usdtDepthUsd * 0.5 ? "depth" : undefined,
  });
  set("A3", net.congestionBeta);

  const [lt, lw] = LATENCY_THRESHOLDS[scenario];
  set("B1", net.inclusionSec, {
    t: lt * urgency,
    w: lw * urgency,
    critical: scenario === "micro" || scenario === "commerce" || tx.urgency === "urgent",
  });
  const [it, iw] = FINALITY_THRESHOLDS[scenario];
  set("B2", net.irreversibilitySec, {
    t: it,
    w: iw,
    critical: scenario === "high_value",
    note: net.irreversibilitySec > 60 ? "softFinality" : undefined,
  });
  set("B3", net.tps / REQUIRED_TPS, { critical: scenario === "high_value" || scenario === "commerce" });

  set("C1b", net.hhi);
  set("C2", net.minOperators, { critical: scenario === "high_value" });
  set("C3", net.uptimeNines);
  set("C4", net.failPct);
  set("C5", net.upgrades);

  set("D1", net.sponsoredPct);
  const memoNeeded = tx.recipient.needsMemo;
  set("D2", net.memo ? 1 : memoNeeded ? 0 : 0.3, {
    critical: memoNeeded,
    note: memoNeeded && !net.memo ? "noMemo" : undefined,
  });
  set("D3", net.multiTransferPct);

  let e1: number;
  if (net.publicLedger) e1 = profile.privacyPref === "private" ? 0.3 : 1;
  else e1 = audit ? 0 : profile.privacyPref === "private" ? 1 : 0.1;
  set("E1", e1, {
    critical: audit && !net.publicLedger,
    note: !net.publicLedger ? "privateLedger" : profile.privacyPref === "private" ? "publicLedger" : undefined,
  });

  const traceMod = net.publicLedger ? -5 : 10;
  const x1 =
    RECIPIENT_BASE[tx.recipient.type] +
    (tx.recipient.firstTime ? 25 : 0) +
    (COUNTRIES[tx.recipient.country] ?? COUNTRIES.OTHER) +
    traceMod;
  set("X1", Math.max(0, Math.min(100, x1)), {
    t: STATIC_THRESHOLDS.X1[0] * tol,
    w: STATIC_THRESHOLDS.X1[1] * tol,
    note: tx.recipient.firstTime ? "firstTime" : undefined,
  });

  let x2: number;
  let x2Note: string | undefined;
  if (tx.recipient.accepted === "unknown") {
    x2 = net.rampCo >= 85 ? 0.8 : net.rampCo >= 50 ? 0.5 : 0.3;
    x2Note = "unknownAccepted";
  } else if (tx.recipient.accepted.includes(net.id)) {
    x2 = 1;
  } else {
    x2 = 0;
    x2Note = "notAccepted";
  }
  set("X2", x2, { critical: known, note: x2Note });

  return METRICS.map((def) => {
    const r = raw[def.id];
    return {
      def,
      value: r.value,
      t: r.t,
      w: r.w,
      light: lightOf(r.value, r.t, r.w, def.dir),
      score: normalize(r.value, r.t, r.w, def.dir),
      critical: Boolean(r.critical),
      noteKey: r.note,
    };
  });
}

interface Rollup {
  light: Light;
  score: number;
}

export function rollup(metrics: MetricResult[]): Rollup {
  if (metrics.length === 0) return { light: "green", score: 1 };
  const score = metrics.reduce((s, m) => s + m.score, 0) / metrics.length;
  if (metrics.some((m) => m.critical && m.light === "red")) return { light: "red", score };
  const base = lightFromScore(score);
  if (base === "green" && metrics.some((m) => m.light === "red")) return { light: "yellow", score };
  if (base === "red" && !metrics.some((m) => m.light === "red")) return { light: "yellow", score };
  return { light: base, score };
}

export function buildBlocks(metrics: MetricResult[]): BlockResult[] {
  return BLOCKS.map((id) => {
    const ms = metrics.filter((m) => m.def.block === id);
    return { id, metrics: ms, ...rollup(ms) };
  });
}

export function buildDimensions(metrics: MetricResult[]): DimensionResult[] {
  return DIMENSIONS.map((id) => ({
    id,
    ...rollup(metrics.filter((m) => m.def.dimension === id)),
  }));
}

export function networkLight(blocks: BlockResult[]): Light {
  if (blocks.some((b) => b.light === "red")) return "red";
  if (blocks.filter((b) => b.light === "yellow").length >= 2) return "yellow";
  return "green";
}

export function getNetwork(id: NetworkProfile["id"]): NetworkProfile {
  return NETWORKS[id];
}
