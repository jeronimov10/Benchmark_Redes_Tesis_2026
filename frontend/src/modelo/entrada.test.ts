// Pruebas de la construccion de la entrada del modelo.
import { describe, expect, it } from "vitest";
import { composicionPorEscenario, entradaModelo, luzMetrica, luzRed } from "./entrada";
import type { ResultadoModelo } from "./tipos";

const tx = (country: string, irreversibility: 0 | 0.5 | 1) => ({
  amountCop: 1_200_000,
  waitSec: 3600,
  irreversibility,
  recipient: { country },
});

describe("app payment -> parameters of modelo.recomendar()", () => {
  it("maps amount, border, wait and irreversibility", () => {
    expect(entradaModelo(tx("US", 0), "CO")).toEqual({
      monto_cop: 1_200_000,
      transfronterizo: true,
      espera_s: 3600,
      irrevocabilidad: "baja",
      trm: 4000,
    });
    expect(entradaModelo(tx("CO", 0.5), "CO").transfronterizo).toBe(false);
    expect(entradaModelo(tx("CO", 0.5), "CO").irrevocabilidad).toBe("media");
    expect(entradaModelo(tx("CO", 1), "CO").irrevocabilidad).toBe("alta");
  });

  it("reads the model's scenario labels", () => {
    expect(composicionPorEscenario({ remesas: 0.9, "comercio doméstico": 0.06, "alto valor": 0.04 })).toEqual({
      E1: 0.9,
      E2: 0.06,
      E3: 0.04,
    });
  });
});

describe("traffic lights from the model's scores", () => {
  it("metric: target met, unacceptable, in between, excluded", () => {
    expect(luzMetrica(1)).toBe("green");
    expect(luzMetrica(0)).toBe("red");
    expect(luzMetrica(0.4)).toBe("yellow");
    expect(luzMetrica(null)).toBeNull();
  });

  it("network: red when a gate excludes it, else from the median", () => {
    const r = {
      inadmisibles: { celo: [["G3", "sin referencia"]] },
      bandas: [{ banda: 1, redes: ["polygon"], puntajes: { polygon: { mediana: 0.72, p05: 0.7, p95: 0.74 } } }],
    } as unknown as ResultadoModelo;
    expect(luzRed(r, "polygon")).toBe("green");
    expect(luzRed(r, "celo")).toBe("red");
  });
});
