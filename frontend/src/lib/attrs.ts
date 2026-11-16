// Opciones y conversion de los atributos del pago desde y hacia la URL.
import type { Irreversibility, ProfileAnswers, Purpose, TxInput } from "@/engine/types";

export const WAIT_OPTIONS = [2, 20, 300, 3600, 86_400] as const;
export const IRR_OPTIONS: Irreversibility[] = [0, 0.5, 1];

const PRESET: Record<Purpose, { waitSec: number; irreversibility: Irreversibility }> = {
  remittance: { waitSec: 3600, irreversibility: 0 },
  commerce: { waitSec: 2, irreversibility: 0.5 },
  p2p: { waitSec: 20, irreversibility: 0.5 },
  payroll: { waitSec: 300, irreversibility: 0.5 },
  treasury: { waitSec: 300, irreversibility: 1 },
};

function shiftWait(sec: number, steps: number): number {
  const i = WAIT_OPTIONS.findIndex((w) => w === sec);
  const base = i === -1 ? 2 : i;
  return WAIT_OPTIONS[Math.min(WAIT_OPTIONS.length - 1, Math.max(0, base + steps))];
}

function shiftIrr(value: Irreversibility, steps: number): Irreversibility {
  const i = IRR_OPTIONS.indexOf(value);
  return IRR_OPTIONS[Math.min(IRR_OPTIONS.length - 1, Math.max(0, i + steps))];
}

export function defaultsFor(
  purpose: Purpose,
  profile: Pick<ProfileAnswers, "timeTolerance" | "riskTolerance">,
): { waitSec: number; irreversibility: Irreversibility } {
  const base = PRESET[purpose];
  const waitShift = profile.timeTolerance === "low" ? -1 : profile.timeTolerance === "high" ? 1 : 0;
  const irrShift = profile.riskTolerance === "low" ? 1 : profile.riskTolerance === "high" ? -1 : 0;
  return {
    waitSec: shiftWait(base.waitSec, waitShift),
    irreversibility: shiftIrr(base.irreversibility, irrShift),
  };
}

export function nearestWait(sec: number): number {
  return WAIT_OPTIONS.reduce((best, w) => (Math.abs(Math.log(w) - Math.log(sec)) < Math.abs(Math.log(best) - Math.log(sec)) ? w : best));
}

export function txQuery(tx: Pick<TxInput, "amountCop" | "waitSec" | "irreversibility">): string {
  return `a=${tx.amountCop}&w=${tx.waitSec}&i=${tx.irreversibility}`;
}

export function applyQuery(
  tx: TxInput,
  params: { get(name: string): string | null },
): TxInput {
  const a = Number(params.get("a"));
  const w = Number(params.get("w"));
  const i = Number(params.get("i"));
  return {
    ...tx,
    amountCop: Number.isFinite(a) && a >= 1 ? a : tx.amountCop,
    waitSec: Number.isFinite(w) && w >= 1 ? w : tx.waitSec,
    irreversibility: i === 0 || i === 0.5 || i === 1 ? i : tx.irreversibility,
  };
}
