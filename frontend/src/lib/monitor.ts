// Ayudantes del monitor: edad, etiquetas de metrica, razon de solo base y resumen por red.
import type { EstadoMetricaVivo, MetricaMedicion, RedMedicion, SaludRed } from "@/modelo/tipos";

export function edadCorta(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || !Number.isFinite(segundos)) return "—";
  const s = Math.max(0, Math.round(segundos));
  if (s < 90) return `${s}s`;
  if (s < 5400) return `${Math.round(s / 60)}m`;
  if (s < 129_600) return `${Math.round(s / 3600)}h`;
  return `${Math.round(s / 86_400)}d`;
}

export type EtiquetaMetrica = "vivo" | "base" | "sin_dato";

export function etiquetaMetrica(m: MetricaMedicion): EtiquetaMetrica {
  if (m.origen === "vivo") return "vivo";
  if (m.valor === null) return "sin_dato";
  return "base";
}

export type RazonBase = EstadoMetricaVivo | "solo_base" | "sin_intento";

export function razonBase(m: MetricaMedicion): RazonBase | null {
  if (m.origen === "vivo") return null;
  if (m.razon_solo_base) return "solo_base";
  if (m.vivo) return m.vivo.estado;
  return m.estado_vivo_esperado ? "sin_intento" : "solo_base";
}

export function resumenRed(red: RedMedicion) {
  const total = red.metricas.length;
  const vivas = red.metricas.filter((m) => m.origen === "vivo").length;
  const esperadas = red.metricas.filter((m) => m.estado_vivo_esperado).length;
  const sinDato = red.metricas.filter((m) => m.valor === null).length;
  return { total, vivas, esperadas, sinDato };
}

export const colorSalud: Record<SaludRed["estado"], "green" | "yellow" | "red"> = {
  ok: "green",
  degradada: "yellow",
  sin_datos: "yellow",
  caida: "red",
};

export function trabajoActivo(estado: string | undefined): boolean {
  return estado === "en_curso";
}
