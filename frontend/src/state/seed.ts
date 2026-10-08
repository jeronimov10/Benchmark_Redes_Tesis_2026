import { COUNTRY_CODES } from "@/data/countries";
import { defaultsFor } from "@/lib/attrs";
import type { AmountBracket, Frequency, NetworkId, Purpose, RecipientType, TxInput } from "@/engine/types";
import { NETWORK_IDS } from "@/engine/types";
import type { HistoryEntry, User } from "./store";

const DAY = 86_400_000;

const BRACKET_RANGE: Record<AmountBracket, [number, number]> = {
  micro: [1_000, 15_000],
  small: [15_000, 200_000],
  medium: [200_000, 2_000_000],
  large: [2_000_000, 100_000_000],
  xlarge: [100_000_000, 500_000_000],
};

const COUNT: Record<Frequency, number> = { daily: 8, weekly: 6, monthly: 4, occasional: 3 };

function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(rand: () => number, xs: T[], fallback: T): T {
  return xs.length ? xs[Math.floor(rand() * xs.length)] : fallback;
}

/**
 * Deterministic, demo-only past activity derived from the onboarding answers,
 * so a new user starts with a believable history. Marked `seeded`.
 */
export function seedHistory(user: User, makeId: () => string): HistoryEntry[] {
  const a = user.answers;
  const rand = mulberry32(hash(user.id + user.alias));
  const [lo, hi] = BRACKET_RANGE[a.typicalAmount];
  const n = COUNT[a.frequency];
  const entries: HistoryEntry[] = [];

  for (let i = 0; i < n; i++) {
    const amount = Math.round(Math.exp(Math.log(lo) + rand() * (Math.log(hi) - Math.log(lo))) / 100) * 100 || 1;
    const purpose = pick<Purpose>(rand, a.purposes, "p2p");
    const type = pick<RecipientType>(rand, a.recipientTypes, "person");
    const country = pick(rand, a.destinationCountries.length ? a.destinationCountries : ["CO"], "CO");
    const accepted: NetworkId[] | "unknown" =
      rand() < 0.4 ? [pick<NetworkId>(rand, [...NETWORK_IDS], "polygon")] : "unknown";
    const preset = defaultsFor(purpose, a);
    const tx: TxInput = {
      amountCop: Math.max(1, amount),
      purpose,
      waitSec: preset.waitSec,
      irreversibility: preset.irreversibility,
      recipient: {
        type,
        country: COUNTRY_CODES.includes(country) ? country : "OTHER",
        firstTime: rand() < 0.3,
        accepted,
        needsMemo: a.needsReconciliation && rand() < 0.5,
      },
    };
    entries.push({
      id: makeId(),
      userId: user.id,
      createdAt: user.createdAt - Math.round((i + 1) * (60 / n) * DAY * (0.7 + rand() * 0.6)),
      tx,
      answers: a,
      seeded: true,
    });
  }
  return entries;
}
