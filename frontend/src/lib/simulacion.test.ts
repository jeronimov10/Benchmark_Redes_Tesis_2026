// Pruebas de los ayudantes de la pagina de simulacion.
import { describe, expect, it } from "vitest";
import { atributoMasSensible, bandaLegible, nivelCambio, porcentaje, resumenPanel } from "./simulacion";
import type { CicloPanel, FilaSensibilidad } from "@/modelo/tipos";

const ciclo = (valido: boolean, usuarios: number | null, cambios: number | null, distintos: number | null): CicloPanel => ({
  id: 1,
  ts: 0,
  valido,
  vivas: 10,
  esperadas: 20,
  usuarios,
  cambios,
  distintos_de_base: distintos,
  causa: null,
});

describe("simulacion helpers", () => {
  it("formats percentages and empty values", () => {
    expect(porcentaje(0.256)).toBe("26 %");
    expect(porcentaje(0.256, 1)).toBe("25.6 %");
    expect(porcentaje("")).toBe("—");
    expect(porcentaje(null)).toBe("—");
  });

  it("classifies the heat of a change share", () => {
    expect([nivelCambio(""), nivelCambio(0), nivelCambio(0.1), nivelCambio(0.3), nivelCambio(0.9)]).toEqual([0, 0, 1, 2, 3]);
  });

  it("prettifies a band", () => {
    expect(bandaLegible("polygon+tempo")).toBe("Polygon + Tempo");
  });

  it("finds the most sensitive attribute and ignores empty shares", () => {
    const f = (atributo: string, c: number | ""): FilaSensibilidad => ({
      fuente: "base",
      perfil: 2,
      atributo,
      n: 10,
      cambios_banda1: 0,
      cuota_cambio: c,
    });
    expect(atributoMasSensible([f("monto_x2", 0.1), f("espera_x4", 0.6), f("irrev_arriba", "")], 2)?.atributo).toBe("espera_x4");
    expect(atributoMasSensible([], 2)).toBeNull();
  });

  it("summarizes the continuous panel ignoring invalid cycles", () => {
    const r = resumenPanel([ciclo(true, 100, 10, 20), ciclo(true, 100, 0, 0), ciclo(false, null, null, null)]);
    expect(r).toMatchObject({ ciclos: 3, validos: 2, invalidos: 1 });
    expect(r.estabilidad).toBeCloseTo(0.95);
    expect(r.distintosDeBase).toBeCloseTo(0.1);
    expect(resumenPanel([ciclo(false, null, null, null)]).estabilidad).toBeNull();
  });
});
