import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TTL_MS, keyOf, pedirJson, pedirRecomendacion } from "./cliente";
import { esCompleta, type EntradaModelo, type RespuestaRecomendar } from "./tipos";

const entrada: EntradaModelo = {
  monto_cop: 1_200_000,
  transfronterizo: true,
  espera_s: 3600,
  irrevocabilidad: "baja",
  trm: 4000,
};

const respuesta = (version: string, extra: Partial<RespuestaRecomendar> = {}): RespuestaRecomendar => ({
  estado: "ok",
  motivo: null,
  resultado: { bandas: [], inadmisibles: {}, advertencias: [], certidumbre: 0.9 } as never,
  nivel_certidumbre: "alta",
  detalle: {},
  medicion: "x",
  trm: 4000,
  modo: "vivo",
  version_perfil: version,
  decidido_en: "2026-10-19T00:00:00Z",
  decidido_ts: 0,
  frescura: { metricas_vivo: 3, metricas_total: 90, edad_vivo_max_s: 20, edad_vivo_min_s: 2 },
  procedencia: {},
  ...extra,
});

const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
const fail = (status: number, body: unknown) => Promise.resolve({ ok: false, status, json: () => Promise.resolve(body) });

describe("cliente del backend", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-19T12:00:00Z"));
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("envia la accion y los parametros al backend y devuelve la respuesta", async () => {
    fetchMock.mockReturnValueOnce(ok(respuesta("v1")));
    const e = { ...entrada, monto_cop: 111_111 };
    const r = await pedirRecomendacion(e);
    expect(r.version_perfil).toBe("v1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/modelo");
    expect(JSON.parse(init.body)).toMatchObject({ accion: "recomendar", monto_cop: 111_111, irrevocabilidad: "baja", trm: 4000 });
  });

  it("reutiliza la respuesta dentro del TTL y la renueva despues", async () => {
    fetchMock.mockReturnValueOnce(ok(respuesta("v1"))).mockReturnValueOnce(ok(respuesta("v2")));
    const e = { ...entrada, monto_cop: 222_222 };
    expect((await pedirRecomendacion(e)).version_perfil).toBe("v1");
    vi.advanceTimersByTime(TTL_MS - 1000);
    expect((await pedirRecomendacion(e)).version_perfil).toBe("v1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(2000);
    expect((await pedirRecomendacion(e)).version_perfil).toBe("v2");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("une peticiones identicas en vuelo en una sola llamada", async () => {
    fetchMock.mockReturnValueOnce(ok(respuesta("v1")));
    const e = { ...entrada, monto_cop: 333_333 };
    const [a, b] = await Promise.all([pedirRecomendacion(e), pedirRecomendacion(e)]);
    expect(a).toBe(b);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("propaga el mensaje de error del backend y permite reintentar", async () => {
    const e = { ...entrada, monto_cop: 444_444 };
    fetchMock.mockReturnValueOnce(fail(500, { error: "ErrorFuente: caido" })).mockReturnValueOnce(ok(respuesta("v1")));
    await expect(pedirRecomendacion(e)).rejects.toThrow("ErrorFuente: caido");
    expect((await pedirRecomendacion(e)).version_perfil).toBe("v1");
  });

  it("usa un mensaje HTTP cuando el cuerpo no trae error", async () => {
    fetchMock.mockReturnValueOnce(fail(502, {}));
    await expect(pedirJson("/api/x")).rejects.toThrow("HTTP 502");
  });

  it("distingue el modo en la clave de cache", () => {
    expect(keyOf("recomendar", entrada)).not.toBe(keyOf("recomendar", { ...entrada, modo: "medicion" }));
    expect(keyOf("recomendar", entrada)).toBe(keyOf("recomendar", { ...entrada, modo: "vivo" }));
  });
});

describe("esCompleta", () => {
  it("solo acepta respuestas con resultado y certidumbre", () => {
    expect(esCompleta(respuesta("v"))).toBe(true);
    expect(esCompleta(respuesta("v", { estado: "datos_insuficientes", resultado: null, nivel_certidumbre: null }))).toBe(false);
    expect(esCompleta(null)).toBe(false);
  });

  it("una respuesta sin redes admisibles sigue siendo completa para poder mostrar las exclusiones", () => {
    expect(esCompleta(respuesta("v", { estado: "sin_redes_admisibles" }))).toBe(true);
  });
});
