import { describe, expect, it } from "vitest";
import { recommend, defaultPriorities } from "./scoring";
import { classifyScenario } from "./scenarios";
import type { ProfileAnswers, TxInput } from "./types";

const profile: ProfileAnswers = {
  userType: "natural",
  country: "CO",
  experience: "basic",
  usedStablecoins: true,
  walletType: "exchange",
  purposes: ["remittance", "commerce"],
  frequency: "weekly",
  typicalAmount: "small",
  recipientTypes: ["person"],
  destinationCountries: ["US"],
  defaultPriority: "balanced",
  costTolerance: "medium",
  timeTolerance: "medium",
  riskTolerance: "medium",
  needsReconciliation: false,
  privacyPref: "indifferent",
};

const tx = (over: Partial<TxInput> & { amountCop: number }): TxInput => ({
  purpose: "commerce",
  urgency: "normal",
  priorities: defaultPriorities("balanced"),
  recipient: {
    type: "person",
    country: "CO",
    firstTime: false,
    accepted: "unknown",
    needsMemo: false,
  },
  ...over,
});

describe("scenario classification", () => {
  it("covers the micro band from 1 peso to 15.000", () => {
    expect(classifyScenario(1, "p2p")).toBe("micro");
    expect(classifyScenario(15_000, "commerce")).toBe("micro");
    expect(classifyScenario(15_001, "commerce")).toBe("commerce");
    expect(classifyScenario(1_500_000, "remittance")).toBe("remittance");
    expect(classifyScenario(150_000_000, "treasury")).toBe("high_value");
  });
});

describe("recommendation engine", () => {
  it("is deterministic", () => {
    const a = recommend(tx({ amountCop: 120_000 }), profile);
    const b = recommend(tx({ amountCop: 120_000 }), profile);
    expect(a.best?.network.id).toBe(b.best?.network.id);
    expect(a.ranking.map((e) => e.total)).toEqual(b.ranking.map((e) => e.total));
  });

  it("evaluates the six networks", () => {
    const r = recommend(tx({ amountCop: 120_000 }), profile);
    expect(r.evaluations).toHaveLength(6);
    expect(r.ranking.length + r.excluded.length).toBe(6);
  });

  it("excludes a network the recipient does not accept", () => {
    const r = recommend(
      tx({
        amountCop: 120_000,
        recipient: { type: "person", country: "CO", firstTime: false, accepted: ["polygon"], needsMemo: false },
      }),
      profile,
    );
    expect(r.best?.network.id).toBe("polygon");
    expect(r.excluded.map((e) => e.network.id)).toContain("tempo");
  });

  it("excludes networks without memo support when a memo is required", () => {
    const r = recommend(
      tx({
        amountCop: 120_000,
        recipient: { type: "business", country: "CO", firstTime: false, accepted: "unknown", needsMemo: true },
      }),
      profile,
    );
    for (const e of r.ranking) expect(e.network.memo).toBe(true);
  });

  it("changing priorities can change the winner", () => {
    const base = tx({ amountCop: 1_500_000, purpose: "remittance" });
    const winners = new Set<string>();
    for (const key of ["cost", "speed", "security"] as const) {
      const r = recommend({ ...base, priorities: defaultPriorities(key) }, profile);
      winners.add(r.best?.network.id ?? "none");
    }
    expect(winners.size).toBeGreaterThan(1);
  });

  it("prints the demo table", () => {
    const cases: [string, number, TxInput["purpose"]][] = [
      ["micro", 8_000, "p2p"],
      ["commerce", 120_000, "commerce"],
      ["remittance", 1_500_000, "remittance"],
      ["high_value", 150_000_000, "treasury"],
    ];
    for (const [name, amountCop, purpose] of cases) {
      const r = recommend(tx({ amountCop, purpose }), profile);
      const rows = r.evaluations.map(
        (e) =>
          `${e.network.id.padEnd(9)} ${e.light.padEnd(6)} ${e.total.toFixed(2)} ` +
          e.blocks.map((b) => `${b.id}:${b.light[0]}`).join(" "),
      );
      console.log(`\n${name} -> best ${r.best?.network.id}\n${rows.join("\n")}`);
    }
  });
});
