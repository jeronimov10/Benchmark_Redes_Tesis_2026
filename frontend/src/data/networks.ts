import type { NetworkId, NetworkProfile } from "@/engine/types";

/**
 * DEMO DATA. Every value is invented for the prototype and is NOT a
 * measurement of the real networks. Replace this file to plug in real data.
 */
export const NETWORKS: Record<NetworkId, NetworkProfile> = {
  tempo: {
    id: "tempo", feeFixedUsd: 0.0005, feePct: 0, inclusionSec: 0.6, irreversibilitySec: 0.6,
    feeDispersion: 1.3, congestionBeta: 0.2, tps: 5000, usdtDepthUsd: 60_000,
    hhi: 0.4, minOperators: 3, uptimeNines: 3.9, failPct: 0.2, upgrades: 5,
    sponsoredPct: 100, memo: true, multiTransferPct: 80, publicLedger: true, rampCo: 35,
  },
  aptos: {
    id: "aptos", feeFixedUsd: 0.0008, feePct: 0, inclusionSec: 0.9, irreversibilitySec: 0.9,
    feeDispersion: 1.6, congestionBeta: 0.4, tps: 10000, usdtDepthUsd: 500_000,
    hhi: 0.06, minOperators: 25, uptimeNines: 4.0, failPct: 0.3, upgrades: 1,
    sponsoredPct: 30, memo: false, multiTransferPct: 60, publicLedger: true, rampCo: 60,
  },
  canton: {
    id: "canton", feeFixedUsd: 0.4, feePct: 0, inclusionSec: 1.5, irreversibilitySec: 1.5,
    feeDispersion: 1.4, congestionBeta: 0.05, tps: 150, usdtDepthUsd: 20_000,
    hhi: 0.1, minOperators: 7, uptimeNines: 4.3, failPct: 0.05, upgrades: 1,
    sponsoredPct: 90, memo: true, multiTransferPct: 40, publicLedger: false, rampCo: 20,
  },
  polygon: {
    id: "polygon", feeFixedUsd: 0.015, feePct: 0, inclusionSec: 2.5, irreversibilitySec: 6,
    feeDispersion: 2.2, congestionBeta: 0.8, tps: 1000, usdtDepthUsd: 5_000_000,
    hhi: 0.08, minOperators: 20, uptimeNines: 3.8, failPct: 0.5, upgrades: 0,
    sponsoredPct: 20, memo: false, multiTransferPct: 50, publicLedger: true, rampCo: 90,
  },
  arbitrum: {
    id: "arbitrum", feeFixedUsd: 0.05, feePct: 0, inclusionSec: 1, irreversibilitySec: 900,
    feeDispersion: 2.8, congestionBeta: 1.0, tps: 4000, usdtDepthUsd: 8_000_000,
    hhi: 0.45, minOperators: 1, uptimeNines: 4.0, failPct: 0.3, upgrades: 1,
    sponsoredPct: 10, memo: false, multiTransferPct: 55, publicLedger: true, rampCo: 80,
  },
  celo: {
    id: "celo", feeFixedUsd: 0.002, feePct: 0, inclusionSec: 1.5, irreversibilitySec: 5,
    feeDispersion: 1.9, congestionBeta: 0.5, tps: 1500, usdtDepthUsd: 300_000,
    hhi: 0.35, minOperators: 1, uptimeNines: 3.9, failPct: 0.4, upgrades: 2,
    sponsoredPct: 40, memo: false, multiTransferPct: 40, publicLedger: true, rampCo: 55,
  },
};
