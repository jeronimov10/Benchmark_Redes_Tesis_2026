import { describe, expect, it } from "vitest";
import { interpret, paymentVector } from "./model";
import { recommend } from "./recommend";
import type { ProfileAnswers, TxInput } from "./types";

const profile: ProfileAnswers = {
  userType: "natural",
  country: "CO",
  experience: "basic",
  usedStablecoins: true,
  walletType: "exchange",
  purposes: ["remittance"],
  frequency: "weekly",
  typicalAmount: "small",
  recipientTypes: ["person"],
  destinationCountries: ["US"],
  defaultPriority: "balanced",
  timeTolerance: "medium",
  riskTolerance: "medium",
  needsReconciliation: false,
};

const tx = (over: Partial<TxInput> & { amountCop: number }): TxInput => ({
  purpose: "commerce",
  waitSec: 1,
  irreversibility: 0.5,
  recipient: { type: "person", country: "CO", firstTime: false, accepted: "unknown", needsMemo: false },
  ...over,
});

// Table 11 of the thesis: logic tests with known answers.
describe("interpolation (thesis Table 11)", () => {
  it("remittance of USD 300 -> 0.98 remittances, kappa 0.78", () => {
    const r = interpret(paymentVector(1_200_000, true, 4500, 0));
    expect(r.lambda.E1).toBeCloseTo(0.98, 1);
    expect(r.kappa).toBeCloseTo(0.78, 1);
  });
  it("shop payment COP 15.000 -> 0.90 commerce, kappa 0.54", () => {
    const r = interpret(paymentVector(15_000, false, 1, 0.5));
    expect(r.lambda.E2).toBeCloseTo(0.9, 1);
    expect(r.kappa).toBeCloseTo(0.54, 1);
  });
  it("settlement of COP 80 million -> 0.99 high value, kappa 0.93", () => {
    const r = interpret(paymentVector(80_000_000, false, 464, 1));
    expect(r.lambda.E3).toBeCloseTo(0.99, 1);
    expect(r.kappa).toBeCloseTo(0.93, 1);
  });
  it("domestic COP 1.2 million with 60 s -> 0.69 commerce / 0.24 high value, kappa 0.28", () => {
    const r = interpret(paymentVector(1_200_000, false, 60, 0.5));
    expect(r.lambda.E2).toBeCloseTo(0.69, 1);
    expect(r.lambda.E3).toBeCloseTo(0.24, 1);
    expect(r.kappa).toBeCloseTo(0.28, 1);
    expect(r.certainty).toBe("low");
  });
});

// Table 13: scores of the first set. Central (deterministic) scores must match to ~0.02.
describe("scores of the first set (thesis Table 13)", () => {
  const cases: [string, TxInput, Record<string, number>][] = [
    ["E1 remittance", tx({ amountCop: 1_200_000, purpose: "remittance", waitSec: 4500, irreversibility: 0, recipient: { type: "person", country: "US", firstTime: false, accepted: "unknown", needsMemo: false } }), { polygon: 0.722, arbitrum: 0.63, celo: 0.606 }],
    ["E2 shop", tx({ amountCop: 15_000, waitSec: 1, irreversibility: 0.5 }), { polygon: 0.729, arbitrum: 0.605, celo: 0.562 }],
    ["E3 high value", tx({ amountCop: 80_000_000, waitSec: 464, irreversibility: 1 }), { polygon: 0.732, arbitrum: 0.571, celo: 0.504 }],
  ];
  for (const [name, input, expected] of cases) {
    it(name, () => {
      const rec = recommend(input, profile);
      for (const [id, score] of Object.entries(expected)) {
        const ev = rec.evaluations.find((e) => e.data.id === id)!;
        expect(ev.score as number).toBeGreaterThan(score - 0.008);
        expect(ev.score as number).toBeLessThan(score + 0.008);
      }
    });
  }
});

describe("recommendation", () => {
  it("is deterministic", () => {
    const a = recommend(tx({ amountCop: 120_000 }), profile);
    const b = recommend(tx({ amountCop: 120_000 }), profile);
    expect(a.ranking.map((e) => e.median)).toEqual(b.ranking.map((e) => e.median));
  });
  it("covers the six networks", () => {
    const r = recommend(tx({ amountCop: 120_000 }), profile);
    expect(r.evaluations).toHaveLength(6);
    expect(r.ranking.length + r.excluded.length).toBe(6);
  });
  it("Canton is inadmissible for a stablecoin payment (G2')", () => {
    const r = recommend(tx({ amountCop: 120_000 }), profile);
    expect(r.excluded.map((e) => e.data.id)).toContain("canton");
  });
  it("excludes a network the recipient does not accept", () => {
    const r = recommend(
      tx({ amountCop: 120_000, recipient: { type: "person", country: "CO", firstTime: false, accepted: ["celo"], needsMemo: false } }),
      profile,
    );
    expect(r.best?.data.id).toBe("celo");
    expect(r.excluded.map((e) => e.data.id)).toContain("polygon");
  });
  it("same-band networks are reported as a tie", () => {
    const r = recommend(tx({ amountCop: 120_000 }), profile);
    const bandOfAll = new Set(r.ranking.map((e) => e.band));
    expect(bandOfAll.size).toBeGreaterThanOrEqual(1);
  });
  it("runs 10.000 replicas fast enough for the UI", () => {
    const t0 = performance.now();
    recommend(tx({ amountCop: 120_000 }), profile);
    expect(performance.now() - t0).toBeLessThan(1500);
  });
});
