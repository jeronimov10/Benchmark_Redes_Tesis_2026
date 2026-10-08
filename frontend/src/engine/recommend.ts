import { COUNTRIES } from "@/data/countries";
import { NETWORK_DATA } from "@/data/profiles";
import { copToUsdt, DEMO_TRM } from "./fx";
import { BLOCKS, METRIC_BY_ID, METRICS, REQUIRED_TPS } from "./metrics";
import {
  aggregate,
  blockMean,
  interpret,
  lightFromScore,
  lightOfValue,
  paymentVector,
  scoreMetric,
} from "./model";
import { formBands, runMonteCarlo, summarize, REPLICAS, type NetworkSamples } from "./montecarlo";
import {
  NETWORK_IDS,
  type BlockId,
  type BlockResult,
  type GateOutcome,
  type Light,
  type MetricId,
  type MetricResult,
  type NetworkData,
  type NetworkEvaluation,
  type ProfileAnswers,
  type Recommendation,
  type RecipientCheck,
  type TxInput,
} from "./types";

const RECIPIENT_BASE = { person: 10, business: 5, exchange: 0, ownWallet: 5, unknown: 30 } as const;

/** Demo risk score of the recipient, 0-100 (lower is better). Independent of the network. */
export function recipientRisk(tx: TxInput): number {
  const points =
    RECIPIENT_BASE[tx.recipient.type] +
    (tx.recipient.firstTime ? 25 : 0) +
    (COUNTRIES[tx.recipient.country] ?? COUNTRIES.OTHER);
  return Math.min(100, points);
}

function recipientCheck(tx: TxInput, id: NetworkData["id"]): RecipientCheck {
  const risk = recipientRisk(tx);
  return {
    accepted: tx.recipient.accepted === "unknown" ? null : tx.recipient.accepted.includes(id),
    risk,
    riskLight: risk <= 25 ? "green" : risk >= 60 ? "red" : "yellow",
  };
}

function evaluateMetrics(data: NetworkData, ticketUsd: number): MetricResult[] {
  return METRICS.map((def) => {
    const mv = data.metrics[def.id as MetricId];
    if (!mv || mv.value === null) {
      return { def, value: null, score: null, light: null, status: mv?.status ?? "missing", note: mv?.note };
    }
    // A1 is expressed as a fraction of the ticket of this payment.
    const value = def.id === "A1" ? mv.value / ticketUsd : mv.value;
    return {
      def,
      value,
      score: scoreMetric(def, value),
      light: lightOfValue(def, value),
      status: mv.status,
      note: mv.note,
    };
  });
}

function buildBlocks(metrics: MetricResult[]): BlockResult[] {
  return BLOCKS.map((id) => {
    const ms = metrics.filter((m) => m.def.block === id);
    const scored = ms.filter((m) => m.score !== null);
    const score = blockMean(scored.map((m) => m.score as number));
    return {
      id,
      score,
      light: score === null ? null : lightFromScore(score),
      n: scored.length,
      excluded: ms.length - scored.length,
      metrics: ms,
    };
  });
}

function evaluateGates(
  data: NetworkData,
  metrics: MetricResult[],
  lambda: Record<"E1" | "E2" | "E3", number>,
): GateOutcome[] {
  const raw = (id: MetricId) => data.metrics[id]?.value ?? null;
  const out: GateOutcome[] = [];

  const b1 = raw("B1");
  const g1Applies = lambda.E2 > 0.5;
  out.push({
    id: "G1",
    applies: g1Applies,
    measured: b1,
    result: !g1Applies ? "na" : b1 === null ? "na" : b1 <= 20 ? "pass" : "fail",
  });

  out.push({
    id: "G2",
    applies: true,
    measured: raw("B2b") ?? raw("B2"),
    result: data.observability.result,
    note: data.observability.note,
  });

  const d2 = raw("D2");
  out.push({
    id: "G3",
    applies: true,
    measured: d2,
    result: d2 === null ? "na" : d2 > 0 ? "pass" : "fail",
  });

  const b3 = raw("B3");
  const g4Applies = lambda.E1 < 0.5 && !data.capacityIsLowerBound;
  out.push({
    id: "G4",
    applies: g4Applies,
    measured: b3,
    result: !g4Applies ? "na" : b3 === null ? "na" : b3 >= 1 ? "pass" : "fail",
    note: g4Applies && b3 !== null && b3 < 1 ? data.metrics.B3?.note : undefined,
  });
  void metrics;
  return out;
}

export interface RecommendOptions {
  trm?: number;
  replicas?: number;
}

/** The whole pipeline of the thesis for one payment. Deterministic for the same input. */
export function recommend(
  tx: TxInput,
  profile: ProfileAnswers,
  opts: RecommendOptions = {},
): Recommendation {
  const trm = opts.trm ?? DEMO_TRM;
  const amountUsd = copToUsdt(tx.amountCop, trm);
  const crossBorder = tx.recipient.country !== profile.country;
  const vector = paymentVector(tx.amountCop, crossBorder, tx.waitSec, tx.irreversibility);
  const { lambda, weights, dMin, kappa, certainty } = interpret(vector);

  const evaluations: NetworkEvaluation[] = NETWORK_IDS.map((id) => {
    const data = NETWORK_DATA[id];
    const metrics = evaluateMetrics(data, amountUsd);
    const blocks = buildBlocks(metrics);
    const gates = evaluateGates(data, metrics, lambda);
    const recipient = recipientCheck(tx, id);

    const excludedBy: string[] = gates.filter((g) => g.result === "fail").map((g) => g.id);
    if (recipient.accepted === false) excludedBy.push("recipient");
    const admissible = excludedBy.length === 0;

    const score = aggregate(
      Object.fromEntries(blocks.map((b) => [b.id, b.score])) as Record<BlockId, number | null>,
      weights,
    );
    return {
      data,
      metrics,
      blocks,
      gates,
      recipient,
      admissible,
      excludedBy,
      score,
      median: null,
      p5: null,
      p95: null,
      light: "yellow" as Light,
      band: null,
      feeUsd: data.metrics.A1?.value ?? null,
      inclusionSec: data.metrics.B1?.value ?? null,
      finalitySec: data.metrics.B2b?.value ?? data.metrics.B2?.value ?? null,
      excludedMetrics: metrics.filter((m) => m.score === null).length,
    };
  });

  // Monte Carlo over the admissible networks.
  const admissible = evaluations.filter((e) => e.admissible && e.score !== null);
  const samples: NetworkSamples[] = admissible.map((e) => ({
    id: e.data.id,
    metrics: e.metrics
      .filter((m) => m.value !== null)
      .map((m) => {
        const sigmaRel = e.data.metrics[m.def.id]?.sigmaRel ?? 0;
        return {
          def: m.def,
          block: m.def.block,
          mean: m.value as number,
          sd: Math.abs(m.value as number) * sigmaRel,
          t: m.def.t,
          w: m.def.w,
        };
      }),
  }));
  const mc = runMonteCarlo(samples, weights, opts.replicas ?? REPLICAS);

  for (const e of admissible) {
    const s = summarize(mc.scores[e.data.id]);
    e.median = s.median;
    e.p5 = s.p5;
    e.p95 = s.p95;
  }
  // Order by the central score (the one the thesis tables report); the Monte Carlo only decides the bands.
  const ranking = [...admissible].sort((a, b) => (b.score as number) - (a.score as number));
  const { bands, pi } = formBands(
    ranking.map((e) => e.data.id),
    mc.scores,
  );
  const byId = new Map(evaluations.map((e) => [e.data.id, e]));
  bands.forEach((ids, i) => ids.forEach((id) => (byId.get(id as never)!.band = i + 1)));

  // Traffic light of each network.
  for (const e of evaluations) {
    if (!e.admissible || e.score === null) {
      e.light = "red";
      continue;
    }
    const base = lightFromScore(e.score);
    const hasNa = e.gates.some((g) => g.applies && g.result === "na");
    e.light = base === "green" && hasNa ? "yellow" : base;
  }

  const bandGroups = bands.map((ids) => ids.map((id) => byId.get(id as never)!));
  const best = ranking[0] ?? null;
  const separation = ranking.length > 1 ? pi[ranking[0].data.id][ranking[1].data.id] : null;

  return {
    amountUsd,
    trm,
    vector,
    crossBorder,
    lambda,
    dMin,
    kappa,
    certainty,
    weights,
    evaluations,
    ranking,
    bands: bandGroups,
    pi,
    excluded: evaluations.filter((e) => !e.admissible),
    best,
    determinant: determinant(bandGroups, weights),
    separation,
  };
}

/** Metric that most separates band 1 from band 2, among metrics available in every admissible network. */
function determinant(
  bands: NetworkEvaluation[][],
  weights: Record<BlockId, number>,
): { metric: MetricId; delta: number } | null {
  if (bands.length < 2) return null;
  const all = bands.flat();
  const common = METRICS.filter((def) =>
    all.every((e) => e.metrics.find((m) => m.def.id === def.id)?.score !== null),
  );
  if (common.length === 0) return null;
  const nd = (b: BlockId) => common.filter((m) => m.block === b).length;
  const mean = (group: NetworkEvaluation[], id: MetricId) =>
    group.reduce((s, e) => s + (e.metrics.find((m) => m.def.id === id)!.score as number), 0) / group.length;

  let best: { metric: MetricId; delta: number } | null = null;
  for (const def of common) {
    const delta = (weights[def.block] / nd(def.block)) * (mean(bands[0], def.id) - mean(bands[1], def.id));
    if (best === null || delta > best.delta) best = { metric: def.id, delta };
  }
  return best;
}

export { METRIC_BY_ID, REQUIRED_TPS };
