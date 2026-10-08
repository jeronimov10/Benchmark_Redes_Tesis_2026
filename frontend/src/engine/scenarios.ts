import type { Purpose, ScenarioId, Weights } from "./types";

/** Scenario cut-offs in COP. Editable; documented in the standard page. */
export const MICRO_MAX_COP = 15_000;
export const COMMERCE_MAX_COP = 800_000;
export const HIGH_VALUE_MIN_COP = 100_000_000;
export const MIN_AMOUNT_COP = 1;

export const SCENARIOS: ScenarioId[] = ["micro", "commerce", "remittance", "high_value"];

export function classifyScenario(amountCop: number, purpose: Purpose): ScenarioId {
  if (amountCop >= HIGH_VALUE_MIN_COP) return "high_value";
  if (amountCop <= MICRO_MAX_COP) return "micro";
  if (purpose === "remittance") return "remittance";
  if (purpose === "commerce") return "commerce";
  return amountCop <= COMMERCE_MAX_COP ? "commerce" : "remittance";
}

/** Base weights per scenario: what dominates in that kind of payment. */
export const SCENARIO_WEIGHTS: Record<ScenarioId, Weights> = {
  micro: { cost: 0.6, speed: 0.25, security: 0.15 },
  commerce: { cost: 0.3, speed: 0.5, security: 0.2 },
  remittance: { cost: 0.55, speed: 0.15, security: 0.3 },
  high_value: { cost: 0.1, speed: 0.2, security: 0.7 },
};

/** Fee over ticket thresholds per scenario: [target, unacceptable]. */
export const FEE_THRESHOLDS: Record<ScenarioId, [number, number]> = {
  micro: [0.05, 0.5],
  commerce: [0.005, 0.03],
  remittance: [0.001, 0.03],
  high_value: [0.0001, 0.005],
};

/** Inclusion latency thresholds in seconds: [target, unacceptable]. */
export const LATENCY_THRESHOLDS: Record<ScenarioId, [number, number]> = {
  micro: [5, 20],
  commerce: [5, 20],
  remittance: [60, 3600],
  high_value: [30, 600],
};

/** Irreversibility thresholds in seconds: [target, unacceptable]. */
export const FINALITY_THRESHOLDS: Record<ScenarioId, [number, number]> = {
  micro: [60, 3600],
  commerce: [60, 1800],
  remittance: [60, 3600],
  high_value: [30, 900],
};
