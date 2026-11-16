// Tipos de las peticiones y respuestas de la API del backend.
import type { BlockId, GateId, MetricId } from "@/engine/types";

export type Irrevocabilidad = "baja" | "media" | "alta";
export type NivelCertidumbre = "alta" | "media" | "baja";
export type ModoDatos = "vivo" | "medicion";

export interface EntradaModelo {
  monto_cop: number;
  transfronterizo: boolean;
  espera_s: number;
  irrevocabilidad: Irrevocabilidad;
  trm: number;
  modo?: ModoDatos;
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
  caso: Omit<EntradaModelo, "trm" | "modo"> & { ticket_usd: number };
  composicion: Record<string, number>;
  pesos: Record<BlockId, number>;
  certidumbre: number;
  inadmisibles: Record<string, [GateId, string][]>;
  advertencias: string[];
  bandas: Banda[];
  determinante?: { metrica: MetricId; contribucion: number } | null;
}

export interface Procedencia {
  origen: "vivo" | "base";
  fuente: string;
  ts: number;
  edad_s: number;
  estado: string;
  n: number | null;
  ventana_s: number | null;
  vivo_descartado?: { estado: string; ts: number; edad_s: number; nota: string | null };
}

export interface MetricaDetalle {
  id: MetricId;
  bloque: BlockId;
  direccion: "menor" | "mayor" | "nueves";
  objetivo: number;
  inaceptable: number;
  valor: number | null;
  sigma: number | null;
  nota: string | null;
  cota_inferior: boolean;
  puntaje: number | null;
  procedencia: Procedencia | null;
}

export interface DetalleRed {
  metricas: MetricaDetalle[];
  bloques: Record<BlockId, number | null>;
  puntaje_central: number;
  compuertas_falladas: { compuerta: GateId; motivo: string }[];
}

export interface Frescura {
  metricas_vivo: number;
  metricas_total: number;
  edad_vivo_max_s: number | null;
  edad_vivo_min_s: number | null;
}

export type EstadoRecomendacion = "ok" | "datos_insuficientes" | "sin_redes_admisibles";

export interface RespuestaRecomendar {
  estado: EstadoRecomendacion;
  motivo: string | null;
  resultado: ResultadoModelo | null;
  nivel_certidumbre: NivelCertidumbre | null;
  detalle: Record<string, DetalleRed>;
  medicion: string;
  trm: number;
  modo: ModoDatos;
  version_perfil: string;
  decidido_en: string;
  decidido_ts: number;
  frescura: Frescura;
  procedencia: Record<string, Record<string, Procedencia>>;
  redes_sin_datos?: string[];
}

export type RespuestaCompleta = RespuestaRecomendar & { resultado: ResultadoModelo; nivel_certidumbre: NivelCertidumbre };

export function esCompleta(r: RespuestaRecomendar | null | undefined): r is RespuestaCompleta {
  return !!r && r.resultado !== null && r.nivel_certidumbre !== null;
}

export interface RespuestaInterpretar {
  redes: string[];
  composicion: Record<string, number>;
  pesos: Record<BlockId, number>;
  certidumbre: number;
  nivel_certidumbre: NivelCertidumbre;
  ticket_usd: number;
  version_perfil: string;
}

export interface UmbralModelo {
  bloque: BlockId;
  direccion: "menor" | "mayor" | "nueves";
  objetivo: number | { fraccion_ticket: number };
  inaceptable: number | { fraccion_ticket: number };
}

export interface RespuestaInfo {
  redes: string[];
  medicion: string;
  version_perfil: string;
  frescura: Frescura;
  metricas: Record<MetricId, UmbralModelo>;
  escenarios: Record<"remesas" | "comercio" | "altovalor", { punto: number[]; pesos: Record<BlockId, number> }>;
  gamma: number[];
}

export type EstadoMetricaVivo = "valida" | "insuficiente" | "obsoleta" | "fallida" | "no_computable";

export interface MetricaMedicion {
  id: MetricId;
  bloque: BlockId;
  valor: number | null;
  sigma: number | null;
  cota_inferior: boolean;
  origen: "vivo" | "base" | null;
  fuente: string | null;
  ts: string | null;
  edad_s: number | null;
  n: number | null;
  ventana_s: number | null;
  nota: string | null;
  vivo: { estado: EstadoMetricaVivo; valor: number | null; n: number; ts: string; edad_s: number; nota: string; unidad: string } | null;
  razon_solo_base: string | null;
  estado_vivo_esperado: boolean;
}

export interface ComponenteSalud {
  componente: string;
  ultimo_ok: string | null;
  edad_ok_s: number | null;
  ultimo_error: string | null;
  error: string | null;
  fallos_consecutivos: number;
  latencia_ms: number | null;
}

export interface SaludRed {
  estado: "ok" | "degradada" | "caida" | "sin_datos";
  componentes: ComponenteSalud[];
}

export interface RedMedicion {
  id: string;
  nombre: string;
  responsable: string;
  fuente: string;
  salud: SaludRed;
  muestras: Record<string, number>;
  metricas: MetricaMedicion[];
  metricas_vivo_activas: number;
}

export interface Instantanea {
  generado_en: string;
  version_perfil: string;
  frescura: Frescura;
  obsolescencia_s: number;
  redes: RedMedicion[];
}

export interface TrabajoRecalibracion {
  id: string;
  estado: "en_curso" | "completado" | "fallido" | "cancelado" | "interrumpido";
  redes: string[];
  inicio: number;
  fin: number | null;
  progreso: number;
  etapa: string | null;
  log_tail: string | null;
}

export interface EstadoRecalibracion {
  trabajo: TrabajoRecalibracion | null;
  ocupado: boolean;
  alcance: {
    recalibra: string[];
    rellena: string[];
    no_disponible: string[];
    motivo_no_disponible: string;
    nota_rellena: string;
    no_resuelve: string[];
  };
}

export type EstadoAjuste = "cumple" | "parcial" | "brecha" | "sin_solucion" | "no_evaluable";
export type FuenteSimulacion = "base" | "vivo";
export type EstadoLote = "en_curso" | "completado" | "fallido" | "cancelado" | "interrumpido";

export interface EstadoSimulacion {
  lote: {
    id: string;
    estado: EstadoLote;
    etapa: string;
    progreso?: number;
    evaluaciones?: number;
    inicio: number;
    fin: number | null;
    log: string[];
  } | null;
  ocupado: boolean;
  continuo: {
    activo: boolean;
    ciclos: number;
    ciclos_validos: number;
    intervalo_s: number;
    ultimo_ciclo_ts: number | null;
    ultimo_error: string | null;
  };
}

export interface PerfilSimulado {
  id: number;
  nombre: string;
  tipo: string;
  necesidad: string;
}

export type FilaPersonas = {
  fuente: FuenteSimulacion;
  perfil: number;
  nombre: string;
  tipo: string;
  n: number;
  banda1_modal: string;
  cuota_modal: number;
  semiancho_wilson: number;
  llego_al_tope: boolean;
  certidumbre_media: number | "";
  cuota_certidumbre_baja: number;
  empates_banda1: number;
} & Record<`${"preferencia" | "requisito"}_${EstadoAjuste}`, number>;

export interface FilaContrafactual {
  fuente: FuenteSimulacion;
  prueba: "P3" | "P4";
  escenario: string;
  perfil: number;
  n: number;
  cambios_banda1: number | "";
  cuota_cambio: number | "";
  aptos_supera_a_la_mejor: number | "";
  perdida_puntaje_media: number | "";
  empeora_ajuste_req: number | "";
}

export interface FilaSensibilidad {
  fuente: FuenteSimulacion;
  perfil: number;
  atributo: string;
  n: number;
  cambios_banda1: number;
  cuota_cambio: number | "";
}

export interface FilaConvergencia {
  fuente: FuenteSimulacion;
  replicas: number;
  referencia: number;
  n: number;
  coincide_banda1: number | "";
  coincide_orden: number | "";
}

export interface CicloPanel {
  id: number;
  ts: number;
  valido: boolean;
  vivas: number;
  esperadas: number;
  usuarios: number | null;
  cambios: number | null;
  distintos_de_base: number | null;
  causa: string | null;
}

export interface ResultadosSimulacion {
  generado_en: number;
  corrida: {
    id: string;
    estado: EstadoLote;
    inicio: number;
    fin: number | null;
    config: { fuente: string; replicas: number; semilla: number; tope: number; panel_por_perfil: number };
    notas: string[];
    evaluaciones: number | null;
  } | null;
  perfiles: PerfilSimulado[];
  personas: FilaPersonas[];
  contrafactuales: FilaContrafactual[];
  sensibilidad: FilaSensibilidad[];
  convergencia: FilaConvergencia[];
  alertas: string[];
  vivo: { ciclos_total: number; ciclos_validos: number; serie: CicloPanel[] };
}
