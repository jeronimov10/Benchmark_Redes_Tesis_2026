// Pruebas de los ayudantes del monitor.
import { describe, expect, it } from "vitest";
import { colorSalud, edadCorta, etiquetaMetrica, razonBase, resumenRed, trabajoActivo } from "./monitor";
import type { MetricaMedicion, RedMedicion } from "@/modelo/tipos";

const base: MetricaMedicion = {
  id: "B1",
  bloque: "B",
  valor: 1.5,
  sigma: null,
  cota_inferior: false,
  origen: "base",
  fuente: "perfiles.json",
  ts: null,
  edad_s: 100,
  n: null,
  ventana_s: null,
  nota: null,
  vivo: null,
  razon_solo_base: null,
  estado_vivo_esperado: true,
};

describe("edadCorta", () => {
  it("formatea segundos, minutos, horas y dias", () => {
    expect(edadCorta(0)).toBe("0s");
    expect(edadCorta(45)).toBe("45s");
    expect(edadCorta(300)).toBe("5m");
    expect(edadCorta(7200)).toBe("2h");
    expect(edadCorta(3 * 86_400)).toBe("3d");
  });

  it("devuelve un guion cuando no hay dato", () => {
    expect(edadCorta(null)).toBe("—");
    expect(edadCorta(undefined)).toBe("—");
    expect(edadCorta(Number.NaN)).toBe("—");
  });
});

describe("etiquetas de procedencia", () => {
  it("distingue vivo, base y sin dato", () => {
    expect(etiquetaMetrica({ ...base, origen: "vivo" })).toBe("vivo");
    expect(etiquetaMetrica(base)).toBe("base");
    expect(etiquetaMetrica({ ...base, origen: "base", valor: null })).toBe("sin_dato");
  });

  it("explica por que una metrica sigue en la base", () => {
    expect(razonBase({ ...base, origen: "vivo" })).toBeNull();
    expect(razonBase({ ...base, razon_solo_base: "no reproducible" })).toBe("solo_base");
    expect(
      razonBase({ ...base, vivo: { estado: "insuficiente", valor: 1, n: 3, ts: "", edad_s: 1, nota: "", unidad: "s" } }),
    ).toBe("insuficiente");
    expect(razonBase(base)).toBe("sin_intento");
    expect(razonBase({ ...base, estado_vivo_esperado: false })).toBe("solo_base");
  });
});

describe("resumen de red y salud", () => {
  const red = {
    id: "tempo",
    metricas: [
      { ...base, origen: "vivo" },
      { ...base },
      { ...base, valor: null, origen: null, estado_vivo_esperado: false },
    ],
  } as unknown as RedMedicion;

  it("cuenta metricas vivas, esperadas y sin dato", () => {
    expect(resumenRed(red)).toEqual({ total: 3, vivas: 1, esperadas: 2, sinDato: 1 });
  });

  it("asigna colores a la salud y detecta trabajos activos", () => {
    expect(colorSalud.ok).toBe("green");
    expect(colorSalud.caida).toBe("red");
    expect(colorSalud.degradada).toBe("yellow");
    expect(trabajoActivo("en_curso")).toBe(true);
    expect(trabajoActivo("completado")).toBe(false);
    expect(trabajoActivo(undefined)).toBe(false);
  });
});
