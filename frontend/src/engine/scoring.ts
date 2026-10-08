import { NETWORKS } from "@/data/networks";
import { DEMO_TRM, copToUsdt } from "./fx";
import { classifyScenario, SCENARIO_WEIGHTS } from "./scenarios";
import {
  buildBlocks,
  buildDimensions,
  evaluateMetrics,
  feeUsdOf,
  networkLight,
  type EvalContext,
} from "./risk-standard";
import {
  NETWORK_IDS,
  type MetricResult,
  type NetworkEvaluation,
  type PriorityKey,
  type ProfileAnswers,
  type Recommendation,
  type TxInput,
  type Weights,
} from "./types";

const LIGHT_ORDER = { green: 0, yellow: 1, red: 2 } as const;

function normalizeWeights(w: Weights): Weights {
  const sum = w.cost + w.speed + w.security || 1;
  return { cost: w.cost / sum, speed: w.speed / sum, security: w.security / sum };
}

/** Starting priorities for the transaction form, taken from the profile. */
export function defaultPriorities(key: PriorityKey): Weights {
  switch (key) {
    case "cost":
      return { cost: 0.6, speed: 0.2, security: 0.2 };
    case "speed":
      return { cost: 0.2, speed: 0.6, security: 0.2 };
    case "security":
      return { cost: 0.2, speed: 0.2, security: 0.6 };
    default:
      return { cost: 1 / 3, speed: 1 / 3, security: 1 / 3 };
  }
}

/** Blend scenario base, per-transaction priorities and the profile tolerances. */
export function computeWeights(
  scenarioWeights: Weights,
  priorities: Weights,
  profile: ProfileAnswers,
): Weights {
  const p = normalizeWeights(priorities);
  const blended = {
    cost: 0.4 * scenarioWeights.cost + 0.6 * p.cost,
    speed: 0.4 * scenarioWeights.speed + 0.6 * p.speed,
    security: 0.4 * scenarioWeights.security + 0.6 * p.security,
  };
  if (profile.costTolerance === "low") blended.cost += 0.08;
  if (profile.timeTolerance === "low") blended.speed += 0.08;
  if (profile.riskTolerance === "low") blended.security += 0.08;
  return normalizeWeights(blended);
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 1);

/**
 * Ranking score of a metric: half absolute (distance to thresholds) and half
 * relative (position among the six networks). The relative half keeps networks
 * that all pass a threshold ordered instead of tied at 1.
 */
function rankScores(all: MetricResult[][]): Map<MetricResult, number> {
  const out = new Map<MetricResult, number>();
  const count = all[0]?.length ?? 0;
  for (let i = 0; i < count; i++) {
    const col = all.map((ms) => ms[i]);
    const vals = col.map((m) => m.value);
    const positive = vals.every((v) => v > 0);
    const f = (v: number) => (positive ? Math.log(v) : v);
    const lo = Math.min(...vals.map(f));
    const hi = Math.max(...vals.map(f));
    for (const m of col) {
      let rel = hi === lo ? 1 : (f(m.value) - lo) / (hi - lo);
      if (m.def.dir === "lower") rel = 1 - rel;
      out.set(m, 0.5 * m.score + 0.5 * rel);
    }
  }
  return out;
}

function axisScore(metrics: MetricResult[], ids: string[], rank: Map<MetricResult, number>): number {
  return mean(metrics.filter((m) => ids.includes(m.def.id)).map((m) => rank.get(m) ?? m.score));
}

export function recommend(
  tx: TxInput,
  profile: ProfileAnswers,
  trm: number = DEMO_TRM,
): Recommendation {
  const scenario = classifyScenario(tx.amountCop, tx.purpose);
  const amountUsd = copToUsdt(tx.amountCop, trm);
  const weights = computeWeights(SCENARIO_WEIGHTS[scenario], tx.priorities, profile);
  const ctx: EvalContext = { scenario, amountUsd, tx, profile };

  const allMetrics = NETWORK_IDS.map((id) => evaluateMetrics(NETWORKS[id], ctx));
  const rank = rankScores(allMetrics);

  const evaluations: NetworkEvaluation[] = NETWORK_IDS.map((id, idx) => {
    const network = NETWORKS[id];
    const metrics = allMetrics[idx];
    const blocks = buildBlocks(metrics);
    const dimensions = buildDimensions(metrics);

    const cost = axisScore(metrics, ["A1", "A2", "A3"], rank);
    const speed = axisScore(metrics, ["B1", "B2"], rank);
    const security = axisScore(metrics, ["C1b", "C2", "C3", "C4", "C5", "E1"], rank);
    const fit = axisScore(metrics, ["B3", "D1", "D2", "D3", "X1", "X2"], rank);
    const contributions: Weights = {
      cost: weights.cost * cost,
      speed: weights.speed * speed,
      security: weights.security * security,
    };
    const total =
      (contributions.cost + contributions.speed + contributions.security) * (0.5 + 0.5 * fit);
    const feeUsd = feeUsdOf(network, amountUsd);

    return {
      network,
      blocks,
      dimensions,
      light: networkLight(blocks),
      total,
      feeUsd,
      feeCop: feeUsd * trm,
      timeSec: network.inclusionSec,
      contributions,
    };
  });

  const bySecurity = (e: NetworkEvaluation) => e.contributions.security / (weights.security || 1);
  const ranking = evaluations
    .filter((e) => e.light !== "red")
    .sort(
      (a, b) =>
        b.total - a.total ||
        LIGHT_ORDER[a.light] - LIGHT_ORDER[b.light] ||
        bySecurity(b) - bySecurity(a),
    );
  const excluded = evaluations
    .filter((e) => e.light === "red")
    .sort((a, b) => b.total - a.total);

  return {
    scenario,
    amountUsd,
    trm,
    weights,
    evaluations,
    ranking,
    excluded,
    best: ranking[0] ?? null,
  };
}
