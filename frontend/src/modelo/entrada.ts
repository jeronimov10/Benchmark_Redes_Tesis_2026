import { DEMO_TRM } from "@/engine/fx";
import { lightFromScore } from "@/engine/model";
import { BLOCKS } from "@/engine/metrics";
import type { BlockId, Irreversibility, Light, MetricId, ScenarioId, TxInput, Unit } from "@/engine/types";
import type { DetalleRed, EntradaModelo, Irrevocabilidad, ResultadoModelo } from "./tipos";

/** App irreversibility (0 / 0.5 / 1) -> the model's "baja" / "media" / "alta". */
export function irrevocabilidad(i: Irreversibility): Irrevocabilidad {
  if (i === 0) return "baja";
  if (i === 0.5) return "media";
  return "alta";
}

/**
 * How a payment of the app becomes the parameters of modelo.recomendar().
 * The amount is already in COP; the payment crosses a border when the recipient
 * lives in another country than the user.
 */
export function entradaModelo(
  tx: Pick<TxInput, "amountCop" | "waitSec" | "irreversibility"> & { recipient: Pick<TxInput["recipient"], "country"> },
  originCountry: string,
  trm: number = DEMO_TRM,
): EntradaModelo {
  return {
    monto_cop: tx.amountCop,
    transfronterizo: tx.recipient.country !== originCountry,
    espera_s: tx.waitSec,
    irrevocabilidad: irrevocabilidad(tx.irreversibility),
    trm,
  };
}

/** The model labels its scenarios in Spanish; the app translates them by id. */
const ESCENARIO: Record<string, ScenarioId> = {
  remesas: "E1",
  "comercio doméstico": "E2",
  "alto valor": "E3",
};

export function composicionPorEscenario(composicion: Record<string, number>): Record<ScenarioId, number> {
  const out = { E1: 0, E2: 0, E3: 0 } as Record<ScenarioId, number>;
  for (const [etiqueta, v] of Object.entries(composicion)) {
    const id = ESCENARIO[etiqueta];
    if (id) out[id] = v;
  }
  return out;
}

export function escenarioDominante(composicion: Record<string, number>): ScenarioId {
  const c = composicionPorEscenario(composicion);
  return (Object.keys(c) as ScenarioId[]).reduce((a, b) => (c[a] >= c[b] ? a : b));
}

/** Band of each network (1-based), or null when it is not admissible. */
export function bandaDe(r: ResultadoModelo, red: string): number | null {
  return r.bandas.find((b) => b.redes.includes(red))?.banda ?? null;
}

/** Admissible networks in band order, then by median inside the band (the model's order). */
export function redesEnOrden(r: ResultadoModelo): string[] {
  return r.bandas.flatMap((b) => b.redes);
}

/** Measured value of a metric in a network, as perfiles.json stores it. */
export const valueOf = (d: DetalleRed | undefined, id: MetricId) => d?.metricas.find((m) => m.id === id)?.valor ?? null;

/** Blocks where one network's central score beats the other's by more than 0.02. */
export function blocksAhead(a: DetalleRed | undefined, b: DetalleRed | undefined) {
  const out = { a: [] as BlockId[], b: [] as BlockId[] };
  if (!a || !b) return out;
  for (const blk of BLOCKS) {
    const x = a.bloques[blk];
    const y = b.bloques[blk];
    if (x === null || y === null) continue;
    if (x - y > 0.02) out.a.push(blk);
    else if (y - x > 0.02) out.b.push(blk);
  }
  return out;
}

/* ---------- traffic lights: a reading of the model's scores, not new scores ---------- */

/**
 * Light of one metric from its normalized score (modelo.normalizar):
 * 1 means it meets the target, 0 that it is at or beyond the unacceptable threshold.
 */
export function luzMetrica(puntaje: number | null): Light | null {
  if (puntaje === null) return null;
  if (puntaje >= 1) return "green";
  if (puntaje <= 0) return "red";
  return "yellow";
}

/** Light of a block or network score, with the app's existing cut-offs (0.70 / 0.45). */
export function luzPuntaje(puntaje: number | null): Light | null {
  return puntaje === null ? null : lightFromScore(puntaje);
}

/** Light of a network: red when a gate excludes it, otherwise from its Monte Carlo median. */
export function luzRed(r: ResultadoModelo, red: string): Light {
  if (r.inadmisibles[red]) return "red";
  const banda = r.bandas.find((b) => b.redes.includes(red));
  const p = banda?.puntajes[red];
  return p ? lightFromScore(p.mediana) : "red";
}

/** Display unit of each metric as perfiles.json stores it (shares as fractions, A1/A4 in USD). */
export const UNIDAD: Record<MetricId, Unit> = {
  A1: "usd",
  A2: "ratio",
  A3: "index",
  A4: "usd",
  B1: "seconds",
  B2: "seconds",
  B2b: "seconds",
  B3: "ratio",
  C1: "index",
  C2: "count",
  C3: "percent",
  C4: "fraction",
  C5: "count",
  D1: "fraction",
  D2: "fraction",
  D3: "fraction",
};
