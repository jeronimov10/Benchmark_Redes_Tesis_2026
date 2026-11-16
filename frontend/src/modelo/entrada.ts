// Construye la entrada del modelo desde los atributos del pago y lee su salida (escenario dominante, bandas, orden de redes).
import { DEMO_TRM } from "@/engine/fx";
import { lightFromScore } from "@/engine/model";
import { BLOCKS } from "@/engine/metrics";
import type { BlockId, Irreversibility, Light, MetricId, ScenarioId, TxInput, Unit } from "@/engine/types";
import type { DetalleRed, EntradaModelo, Irrevocabilidad, ResultadoModelo } from "./tipos";

export function irrevocabilidad(i: Irreversibility): Irrevocabilidad {
  if (i === 0) return "baja";
  if (i === 0.5) return "media";
  return "alta";
}

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

export function bandaDe(r: ResultadoModelo, red: string): number | null {
  return r.bandas.find((b) => b.redes.includes(red))?.banda ?? null;
}

export function redesEnOrden(r: ResultadoModelo): string[] {
  return r.bandas.flatMap((b) => b.redes);
}

export const valueOf = (d: DetalleRed | undefined, id: MetricId) => d?.metricas.find((m) => m.id === id)?.valor ?? null;

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

export function luzMetrica(puntaje: number | null): Light | null {
  if (puntaje === null) return null;
  if (puntaje >= 1) return "green";
  if (puntaje <= 0) return "red";
  return "yellow";
}

export function luzPuntaje(puntaje: number | null): Light | null {
  return puntaje === null ? null : lightFromScore(puntaje);
}

export function luzRed(r: ResultadoModelo, red: string): Light {
  if (r.inadmisibles[red]) return "red";
  const banda = r.bandas.find((b) => b.redes.includes(red));
  const p = banda?.puntajes[red];
  return p ? lightFromScore(p.mediana) : "red";
}

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
