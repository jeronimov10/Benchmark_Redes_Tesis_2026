import type { CicloPanel, EstadoAjuste, FilaContrafactual, FilaPersonas, FilaSensibilidad } from "@/modelo/tipos";

export const ESTADOS_AJUSTE: EstadoAjuste[] = ["cumple", "parcial", "brecha", "sin_solucion", "no_evaluable"];

export const COLOR_AJUSTE: Record<EstadoAjuste, string> = {
  cumple: "bg-ok",
  parcial: "bg-brand",
  brecha: "bg-bad",
  sin_solucion: "bg-ink",
  no_evaluable: "bg-line",
};

export type Lectura = "preferencia" | "requisito";

/** Share of users in each fit state for one reading of the wait, in display order. */
export function segmentosAjuste(f: FilaPersonas, lectura: Lectura): { estado: EstadoAjuste; valor: number }[] {
  return ESTADOS_AJUSTE.map((estado) => ({ estado, valor: f[`${lectura}_${estado}`] ?? 0 }));
}

export const porcentaje = (x: number | "" | null | undefined, decimales = 0): string =>
  x === "" || x === null || x === undefined ? "—" : `${(x * 100).toFixed(decimales)} %`;

/** Heat level 0-3 for a change share: none, low, medium, high. */
export function nivelCambio(x: number | ""): 0 | 1 | 2 | 3 {
  if (x === "" || x <= 0) return 0;
  if (x < 0.25) return 1;
  if (x < 0.5) return 2;
  return 3;
}

export function bandaLegible(banda: string): string {
  return banda
    .split("+")
    .map((r) => r.charAt(0).toUpperCase() + r.slice(1))
    .join(" + ");
}

/** Most sensitive attribute per profile: the one that flips the first band most often. */
export function atributoMasSensible(filas: FilaSensibilidad[], perfil: number): FilaSensibilidad | null {
  const propias = filas.filter((f) => f.perfil === perfil && f.cuota_cambio !== "");
  if (propias.length === 0) return null;
  return propias.reduce((a, b) => ((b.cuota_cambio as number) > (a.cuota_cambio as number) ? b : a));
}

export function cambioPorEscenario(filas: FilaContrafactual[], prueba: "P3" | "P4", perfil: number): Map<string, FilaContrafactual> {
  return new Map(filas.filter((f) => f.prueba === prueba && f.perfil === perfil).map((f) => [f.escenario, f]));
}

export function escenarios(filas: FilaContrafactual[], prueba: "P3" | "P4"): string[] {
  return [...new Set(filas.filter((f) => f.prueba === prueba && f.escenario !== "aptos_sombra").map((f) => f.escenario))];
}

export function resumenPanel(serie: CicloPanel[]) {
  const validos = serie.filter((c) => c.valido);
  const usuarios = validos.reduce((a, c) => a + (c.usuarios ?? 0), 0);
  const cambios = validos.reduce((a, c) => a + (c.cambios ?? 0), 0);
  const distintos = validos.reduce((a, c) => a + (c.distintos_de_base ?? 0), 0);
  return {
    ciclos: serie.length,
    validos: validos.length,
    invalidos: serie.length - validos.length,
    estabilidad: usuarios > 0 ? 1 - cambios / usuarios : null,
    distintosDeBase: usuarios > 0 ? distintos / usuarios : null,
  };
}
