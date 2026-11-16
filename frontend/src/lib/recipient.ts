// Riesgo del destinatario de un pago segun el pais.
import { COUNTRIES } from "@/data/countries";
import type { TxInput } from "@/engine/types";

const RECIPIENT_BASE = { person: 10, business: 5, exchange: 0, ownWallet: 5, unknown: 30 } as const;

export function recipientRisk(tx: TxInput): number {
  const points =
    RECIPIENT_BASE[tx.recipient.type] +
    (tx.recipient.firstTime ? 25 : 0) +
    (COUNTRIES[tx.recipient.country] ?? COUNTRIES.OTHER);
  return Math.min(100, points);
}
