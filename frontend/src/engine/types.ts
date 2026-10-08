export const NETWORK_IDS = ["polygon", "celo", "arbitrum", "tempo", "aptos", "canton"] as const;
export type NetworkId = (typeof NETWORK_IDS)[number];

/** Thesis reference scenarios: E1 remittances, E2 domestic commerce, E3 high value. */
export const SCENARIO_IDS = ["E1", "E2", "E3"] as const;
export type ScenarioId = (typeof SCENARIO_IDS)[number];

export type Light = "green" | "yellow" | "red";
export type BlockId = "A" | "B" | "C" | "D";

export type MetricId =
  | "A1" | "A2" | "A3" | "A4"
  | "B1" | "B2" | "B2b" | "B3"
  | "C1" | "C2" | "C3" | "C4" | "C5"
  | "D1" | "D2" | "D3";

export type UserType = "natural" | "business" | "institution";
export type Experience = "none" | "basic" | "intermediate" | "advanced";
export type WalletType = "none" | "exchange" | "selfcustody";
export type Purpose = "remittance" | "commerce" | "payroll" | "treasury" | "p2p";
export type Frequency = "daily" | "weekly" | "monthly" | "occasional";
export type AmountBracket = "micro" | "small" | "medium" | "large" | "xlarge";
export type PriorityKey = "cost" | "speed" | "security" | "balanced";
export type Tolerance = "low" | "medium" | "high";
export type RecipientType = "person" | "business" | "exchange" | "ownWallet" | "unknown";

/** Answers captured by the onboarding. Stable traits of the user. */
export interface ProfileAnswers {
  userType: UserType;
  /** Origin country of every payment: the user. */
  country: string;
  experience: Experience;
  usedStablecoins: boolean;
  walletType: WalletType;
  purposes: Purpose[];
  frequency: Frequency;
  typicalAmount: AmountBracket;
  recipientTypes: RecipientType[];
  destinationCountries: string[];
  defaultPriority: PriorityKey;
  timeTolerance: Tolerance;
  riskTolerance: Tolerance;
  needsReconciliation: boolean;
}

/** Irreversibility demanded: 0 low, 0.5 medium, 1 high (thesis, Table 10). */
export type Irreversibility = 0 | 0.5 | 1;

/** One hypothetical payment. Origin is always the user. */
export interface TxInput {
  amountCop: number;
  purpose: Purpose;
  /** Tolerable wait until confirmation, in seconds. */
  waitSec: number;
  irreversibility: Irreversibility;
  recipient: {
    type: RecipientType;
    country: string;
    firstTime: boolean;
    /** Networks the recipient accepts; "unknown" when the user does not know. */
    accepted: NetworkId[] | "unknown";
    needsMemo: boolean;
  };
}

/* ---------------- measured network data ---------------- */

export type MetricStatus = "computed" | "partial" | "inconclusive" | "missing";

export interface MetricValue {
  /** Null when the metric could not be computed. */
  value: number | null;
  status: MetricStatus;
  /** Relative standard error used by the Monte Carlo (demo assumption, see standard page). */
  sigmaRel?: number;
  /** i18n key under `data.notes` explaining a caveat. */
  note?: string;
}

export type GateId = "G1" | "G2" | "G3" | "G4";
export type GateResult = "pass" | "fail" | "na";

export interface NetworkData {
  id: NetworkId;
  /** Which part of the study measured it. */
  set: 1 | 2;
  source: "thesis" | "benchmark";
  /** Measured values per metric, in the units of the thesis catalog (see metrics.ts). */
  metrics: Partial<Record<MetricId, MetricValue>>;
  /** Gate outcomes that do not depend on the payment. */
  observability: { result: GateResult; note?: string };
  capacityIsLowerBound: boolean;
  /** Whether the metrics describe the payment asset used in the app (a stablecoin). */
  assetNote?: string;
}

/* ---------------- evaluation results ---------------- */

export interface MetricDef {
  id: MetricId;
  block: BlockId;
  dir: "lower" | "higher";
  unit: "fraction" | "ratio" | "seconds" | "usd" | "count" | "nines" | "percent" | "index";
  /** Thesis threshold pair [target t, unacceptable w]. A1 is replaced per payment. */
  t: number;
  w: number;
  /** Source of the metric: chain or documentation. */
  source: "chain" | "doc";
}

export type Unit = MetricDef["unit"];

export interface MetricResult {
  def: MetricDef;
  /** Value on the metric scale (A1 as fraction of the ticket). Null when excluded. */
  value: number | null;
  score: number | null;
  light: Light | null;
  status: MetricStatus;
  note?: string;
}

export interface BlockResult {
  id: BlockId;
  score: number | null;
  light: Light | null;
  /** Number of metrics that entered the block average. */
  n: number;
  /** Metrics of the block that were excluded for lack of data. */
  excluded: number;
  metrics: MetricResult[];
}

export interface GateOutcome {
  id: GateId;
  result: GateResult;
  /** Measured value behind the verdict (seconds, margin...). */
  measured?: number | null;
  applies: boolean;
  note?: string;
}

export interface RecipientCheck {
  /** Recipient accepts this network: true, false, or null when unknown. */
  accepted: boolean | null;
  /** Demo risk score 0-100 (lower is better), same for all networks. */
  risk: number;
  riskLight: Light;
}

export interface NetworkEvaluation {
  data: NetworkData;
  metrics: MetricResult[];
  blocks: BlockResult[];
  gates: GateOutcome[];
  recipient: RecipientCheck;
  admissible: boolean;
  /** Why it is not admissible: gate ids and/or "recipient". */
  excludedBy: string[];
  /** Deterministic score at central values. */
  score: number | null;
  /** Monte Carlo median and 5th/95th percentiles. */
  median: number | null;
  p5: number | null;
  p95: number | null;
  light: Light;
  /** 1-based band, or null when not admissible. */
  band: number | null;
  /** Median cost in USD, inclusion time and irreversibility time in seconds. */
  feeUsd: number | null;
  inclusionSec: number | null;
  finalitySec: number | null;
  excludedMetrics: number;
}

export type Certainty = "high" | "medium" | "low";

export interface Recommendation {
  amountUsd: number;
  trm: number;
  /** Payment vector (normalized amount, crosses border, normalized wait, irreversibility). */
  vector: [number, number, number, number];
  crossBorder: boolean;
  /** Composition of the case over E1, E2, E3. */
  lambda: Record<ScenarioId, number>;
  dMin: number;
  kappa: number;
  certainty: Certainty;
  /** Weights per block for this payment. */
  weights: Record<BlockId, number>;
  evaluations: NetworkEvaluation[];
  /** Admissible networks, best median first. */
  ranking: NetworkEvaluation[];
  bands: NetworkEvaluation[][];
  /** pi[i][j] = P(score_i > score_j) keyed by network ids. */
  pi: Record<string, Record<string, number>>;
  excluded: NetworkEvaluation[];
  best: NetworkEvaluation | null;
  /** Metric that most separates band 1 from band 2. */
  determinant: { metric: MetricId; delta: number } | null;
  /** Probability that the best network beats the runner-up. */
  separation: number | null;
}
