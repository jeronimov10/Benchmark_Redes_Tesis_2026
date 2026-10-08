import type { MetricValue, NetworkData, NetworkId } from "@/engine/types";

/**
 * MEASURED DATA.
 *
 * Set 1 (Polygon PoS, Celo, Arbitrum One): Table 12 of the thesis, 90-day window,
 *   one node provider per network (docs/tesis-apa7.pdf).
 * Set 2 (Tempo, Aptos, Canton): preliminary pass of the benchmark in this repo
 *   (resultados/metrics.csv). Reduced samples of minutes/seconds, not the 14-day window.
 *   Metrics that are not comparable with the thesis definition are left out (value null).
 *
 * `sigmaRel` is a demo assumption for the Monte Carlo (the thesis uses per-metric
 * bootstrap errors that are not published yet): 8% for set 1, 25% for set 2.
 */

const S1 = 0.08;
const S2 = 0.25;

const ok = (value: number, sigmaRel: number, note?: string): MetricValue => ({
  value,
  status: "computed",
  sigmaRel,
  note,
});
const partial = (value: number, sigmaRel: number, note?: string): MetricValue => ({
  value,
  status: "partial",
  sigmaRel,
  note,
});
const none = (status: "missing" | "inconclusive", note?: string): MetricValue => ({
  value: null,
  status,
  note,
});

const DAY = 86_400;

export const NETWORK_DATA: Record<NetworkId, NetworkData> = {
  polygon: {
    id: "polygon",
    set: 1,
    source: "thesis",
    observability: { result: "pass" },
    capacityIsLowerBound: true,
    metrics: {
      A1: ok(0.0043, S1),
      A2: ok(9.1, S1),
      A3: none("inconclusive", "noCongestion"),
      A4: ok(7.0e-6, S1, "anchorSplit"),
      B1: ok(1.5, S1),
      B2: ok(492, S1),
      B2b: ok(492, S1, "noDisputeWindow"),
      B3: ok(7.83, S1, "lowerBound"),
      C1: ok(0.197, S1),
      C2: ok(3, S1),
      C3: ok(99.965, S1, "documentary"),
      C4: ok(0, S1),
      C5: ok(0, S1),
      D1: ok(38.6, S1, "signedAuth"),
      D2: ok(0.9, S1, "strictMemo"),
      D3: ok(30.1, S1),
    },
  },
  celo: {
    id: "celo",
    set: 1,
    source: "thesis",
    observability: { result: "pass" },
    capacityIsLowerBound: true,
    metrics: {
      A1: ok(0.0013, S1),
      A2: ok(9.8, S1),
      A3: none("inconclusive", "noCongestion"),
      A4: ok(3.5e-6, S1, "anchorSplit"),
      B1: ok(1.0, S1),
      B2: ok(960, S1),
      B2b: ok(3.52 * DAY, S1, "disputeWindow"),
      B3: ok(1.99, S1, "lowerBound"),
      C1: ok(1.0, S1, "singleSequencer"),
      C2: ok(1, S1, "singleSequencer"),
      C3: ok(99.936, S1, "documentary"),
      C4: ok(0.16, S1),
      C5: ok(0, S1),
      D1: ok(52.5, S1, "signedAuth"),
      D2: ok(0.56, S1, "strictMemo"),
      D3: ok(6.0, S1),
    },
  },
  arbitrum: {
    id: "arbitrum",
    set: 1,
    source: "thesis",
    observability: { result: "pass" },
    capacityIsLowerBound: true,
    metrics: {
      A1: ok(0.007, S1),
      A2: ok(10.7, S1),
      A3: none("inconclusive", "noCongestion"),
      A4: ok(2.9e-5, S1),
      B1: ok(0.25, S1, "roundedSeconds"),
      B2: ok(60, S1),
      B2b: ok(6.44 * DAY, S1, "disputeWindow"),
      B3: ok(6.42, S1, "lowerBound"),
      C1: ok(0.994, S1, "singleSequencer"),
      C2: ok(1, S1, "singleSequencer"),
      C3: ok(99.949, S1, "documentary"),
      C4: ok(0, S1),
      C5: ok(0, S1),
      D1: ok(10.1, S1, "paymasters"),
      D2: ok(0.71, S1, "strictMemo"),
      D3: ok(22.6, S1),
    },
  },
  tempo: {
    id: "tempo",
    set: 2,
    source: "benchmark",
    observability: { result: "pass" },
    capacityIsLowerBound: false,
    metrics: {
      // A2 of the benchmark is the p95 cost in USD: ratio = 0.0001785474 / 0.0000201522.
      A1: partial(2.01522e-5, S2, "reducedSample"),
      A2: partial(0.0001785474 / 0.0000201522, S2, "reducedSample"),
      A3: none("inconclusive", "unreliableRegression"),
      A4: none("missing", "noAnchor"),
      B1: ok(0.59, S2),
      B2: partial(0.6302, S2, "liveShortRun"),
      B2b: partial(0.6302, S2, "noDisputeWindow"),
      // H_cfg over 48 TPS in the benchmark, rescaled to the thesis requirement of 18 TPS.
      B3: partial((556.8040922656879 * 48) / 18, S2, "configuredCapacity"),
      C1: ok(0.068, S2, "permissioned"),
      C2: ok(8, S2),
      C3: none("missing", "notComparable"),
      C4: ok(0, S2),
      C5: ok(0, S2),
      D1: partial(100, S2, "degenerate"),
      D2: ok(45, S2),
      D3: partial(76.8, S2, "contaminated"),
    },
  },
  aptos: {
    id: "aptos",
    set: 2,
    source: "benchmark",
    observability: { result: "na", note: "finalityNotMeasured" },
    capacityIsLowerBound: false,
    metrics: {
      A1: partial(0.00028550510721, S2, "frozenOracle"),
      A2: partial(0.00066172626213 / 0.00028550510721, S2, "frozenOracle"),
      A3: none("inconclusive", "unreliableRegression"),
      A4: none("missing", "noAnchor"),
      B1: ok(0.086, S2),
      B2: none("missing", "finalityNotMeasured"),
      B2b: none("missing", "finalityNotMeasured"),
      B3: partial((593.2056033536903 * 48) / 18, S2, "configuredCapacity"),
      C1: ok(0.0206, S2),
      C2: ok(24, S2),
      C3: none("missing", "notComparable"),
      C4: ok(0, S2),
      C5: ok(0, S2),
      D1: ok(1.15, S2),
      D2: none("missing", "memoNotDefined"),
      D3: partial(100, S2, "contaminated"),
    },
  },
  canton: {
    id: "canton",
    set: 2,
    source: "benchmark",
    // E1 = 0 for USDCx (stablecoin under the token standard): a third party cannot verify the payment.
    observability: { result: "fail", note: "stablecoinNotObservable" },
    capacityIsLowerBound: false,
    assetNote: "cantonCoin",
    metrics: {
      A1: partial(0.89526, S2, "burstWindow"),
      A2: partial(2.75022 / 0.89526, S2, "burstWindow"),
      A3: none("inconclusive", "unreliableRegression"),
      A4: none("missing", "noAnchor"),
      B1: ok(1.061, S2),
      B2: ok(1.061, S2),
      B2b: ok(1.061, S2, "noDisputeWindow"),
      B3: partial((0.00023270707206100275 * 48) / 18, S2, "memberAllocation"),
      C1: ok(0.296, S2, "svWeights"),
      C2: ok(1, S2, "svWeights"),
      C3: none("missing", "notComparable"),
      C4: ok(0.4125, S2),
      C5: ok(11, S2),
      D1: partial(100, S2, "degenerate"),
      D2: ok(11.7, S2),
      D3: partial(0, S2, "contaminated"),
    },
  },
};
