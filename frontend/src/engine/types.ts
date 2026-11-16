// Tipos y constantes de visualizacion: redes, escenarios y bloques.
export const NETWORK_IDS = ["polygon", "celo", "arbitrum", "tempo", "aptos", "canton"] as const;
export type NetworkId = (typeof NETWORK_IDS)[number];

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
  timeTolerance: Tolerance;
  riskTolerance: Tolerance;
  needsReconciliation: boolean;
}

export type Irreversibility = 0 | 0.5 | 1;

export interface TxInput {
  amountCop: number;
  purpose: Purpose;
  waitSec: number;
  irreversibility: Irreversibility;
  recipient: {
    type: RecipientType;
    country: string;
    firstTime: boolean;
    accepted: NetworkId[] | "unknown";
    needsMemo: boolean;
  };
}

export type GateId = "G1" | "G2" | "G3" | "G4";

export interface MetricMeta {
  id: MetricId;
  block: BlockId;
  unit: "fraction" | "ratio" | "seconds" | "usd" | "count" | "nines" | "percent" | "index";
  source: "chain" | "doc";
}

export type Unit = MetricMeta["unit"];
