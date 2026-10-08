export const NETWORK_IDS = [
  "tempo",
  "aptos",
  "canton",
  "polygon",
  "arbitrum",
  "celo",
] as const;
export type NetworkId = (typeof NETWORK_IDS)[number];

export type ScenarioId = "micro" | "commerce" | "remittance" | "high_value";
export type Light = "green" | "yellow" | "red";
export type BlockId = "A" | "B" | "C" | "D";
export type DimensionId = "cost" | "speed" | "security" | "liquidity" | "destination";

export type UserType = "natural" | "business" | "institution";
export type Experience = "none" | "basic" | "intermediate" | "advanced";
export type WalletType = "none" | "exchange" | "selfcustody";
export type Purpose = "remittance" | "commerce" | "payroll" | "treasury" | "p2p";
export type Frequency = "daily" | "weekly" | "monthly" | "occasional";
export type AmountBracket = "micro" | "small" | "medium" | "large" | "xlarge";
export type PriorityKey = "cost" | "speed" | "security" | "balanced";
export type Tolerance = "low" | "medium" | "high";
export type PrivacyPref = "auditable" | "private" | "indifferent";
export type RecipientType = "person" | "business" | "exchange" | "ownWallet" | "unknown";
export type Urgency = "low" | "normal" | "urgent";

/** Answers captured by the onboarding. Stable traits of the user. */
export interface ProfileAnswers {
  userType: UserType;
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
  costTolerance: Tolerance;
  timeTolerance: Tolerance;
  riskTolerance: Tolerance;
  needsReconciliation: boolean;
  privacyPref: PrivacyPref;
}

export interface Weights {
  cost: number;
  speed: number;
  security: number;
}

/** Details of one hypothetical transaction. Origin is always the user. */
export interface TxInput {
  amountCop: number;
  purpose: Purpose;
  urgency: Urgency;
  priorities: Weights;
  recipient: {
    type: RecipientType;
    country: string;
    firstTime: boolean;
    /** Networks the recipient accepts; "unknown" when the user does not know. */
    accepted: NetworkId[] | "unknown";
    needsMemo: boolean;
  };
}

/** Every number in a NetworkProfile is invented for the demo. */
export interface NetworkProfile {
  id: NetworkId;
  feeFixedUsd: number;
  feePct: number;
  inclusionSec: number;
  irreversibilitySec: number;
  feeDispersion: number;
  congestionBeta: number;
  tps: number;
  usdtDepthUsd: number;
  hhi: number;
  minOperators: number;
  uptimeNines: number;
  failPct: number;
  upgrades: number;
  sponsoredPct: number;
  memo: boolean;
  multiTransferPct: number;
  publicLedger: boolean;
  rampCo: number;
}

export type Unit =
  | "fraction"
  | "ratio"
  | "seconds"
  | "index"
  | "count"
  | "nines"
  | "percent"
  | "score";

export interface MetricDef {
  id: string;
  block: BlockId;
  dimension: DimensionId;
  dir: "lower" | "higher";
  unit: Unit;
  /** Extension of this app, not part of the benchmark catalog. */
  extension?: boolean;
}

export interface MetricResult {
  def: MetricDef;
  value: number;
  t: number;
  w: number;
  light: Light;
  /** 0..1 normalized score. */
  score: number;
  critical: boolean;
  /** i18n key suffix describing the situation, if any. */
  noteKey?: string;
}

export interface BlockResult {
  id: BlockId;
  light: Light;
  score: number;
  metrics: MetricResult[];
}

export interface DimensionResult {
  id: DimensionId;
  light: Light;
  score: number;
}

export interface NetworkEvaluation {
  network: NetworkProfile;
  blocks: BlockResult[];
  dimensions: DimensionResult[];
  light: Light;
  /** Final ranking score 0..1 (only meaningful when light !== "red"). */
  total: number;
  feeUsd: number;
  feeCop: number;
  timeSec: number;
  /** Weighted contribution per priority axis, used by the explanation. */
  contributions: Weights;
}

export interface Recommendation {
  scenario: ScenarioId;
  amountUsd: number;
  trm: number;
  weights: Weights;
  evaluations: NetworkEvaluation[];
  /** Admissible (non-red) networks sorted best first. */
  ranking: NetworkEvaluation[];
  excluded: NetworkEvaluation[];
  best: NetworkEvaluation | null;
}
