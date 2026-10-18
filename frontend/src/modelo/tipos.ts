import type { BlockId, GateId, MetricId } from "@/engine/types";

/**
 * Shapes of what servicio_modelo/recomendar.py returns. `resultado` is the dict of
 * modelo.recomendar() unchanged (see modelo/INTEGRACION.md, "Qué devuelve").
 */

export type Irrevocabilidad = "baja" | "media" | "alta";
export type NivelCertidumbre = "alta" | "media" | "baja";

/** Parameters of modelo.recomendar(), except `replicas`, which the server fixes at 10.000. */
export interface EntradaModelo {
  monto_cop: number;
  transfronterizo: boolean;
  espera_s: number;
  irrevocabilidad: Irrevocabilidad;
  trm: number;
}

export interface PuntajeRed {
  mediana: number;
  p05: number;
  p95: number;
}

export interface Banda {
  banda: number;
  redes: string[];
  puntajes: Record<string, PuntajeRed>;
  separacion_con_siguiente?: number;
  no_distinguibles?: string;
}

export interface ResultadoModelo {
  caso: EntradaModelo & { ticket_usd: number };
  /** Keyed by the model's scenario labels: "remesas", "comercio doméstico", "alto valor". */
  composicion: Record<string, number>;
  pesos: Record<BlockId, number>;
  certidumbre: number;
  /** Network -> list of [gate, reason]. */
  inadmisibles: Record<string, [GateId, string][]>;
  advertencias: string[];
  bandas: Banda[];
  /** Absent when no network is admissible; null when there is a single band. */
  determinante?: { metrica: MetricId; contribucion: number } | null;
}

export interface MetricaDetalle {
  id: MetricId;
  bloque: BlockId;
  direccion: "menor" | "mayor" | "nueves";
  /** Thresholds already resolved for this payment (A1 is a fraction of the ticket, in USD). */
  objetivo: number;
  inaceptable: number;
  valor: number | null;
  sigma: number | null;
  nota: string | null;
  cota_inferior: boolean;
  /** modelo.normalizar() at the measured value; null when the metric is not conclusive. */
  puntaje: number | null;
}

export interface DetalleRed {
  metricas: MetricaDetalle[];
  /** Block means from modelo.puntuar() at the measured values; null when the block has no data. */
  bloques: Record<BlockId, number | null>;
  puntaje_central: number;
  compuertas_falladas: { compuerta: GateId; motivo: string }[];
}

export interface RespuestaRecomendar {
  resultado: ResultadoModelo;
  nivel_certidumbre: NivelCertidumbre;
  detalle: Record<string, DetalleRed>;
  /** "perfiles medidos en 90 días, octubre de 2026" */
  medicion: string;
  trm: number;
}

export interface RespuestaInterpretar {
  redes: string[];
  composicion: Record<string, number>;
  pesos: Record<BlockId, number>;
  certidumbre: number;
  nivel_certidumbre: NivelCertidumbre;
  ticket_usd: number;
}

export interface RespuestaInfo {
  redes: string[];
  medicion: string;
}
