// Cliente de la API del backend con cache, refresco periodico y estados de error.
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  EntradaModelo,
  EstadoRecalibracion,
  EstadoSimulacion,
  Instantanea,
  RespuestaInfo,
  RespuestaInterpretar,
  RespuestaRecomendar,
  ResultadosSimulacion,
} from "./tipos";

export const TTL_MS = 30_000;
export const REFRESCO_MEDICIONES_MS = 15_000;
export const REFRESCO_RECALIBRACION_MS = 3_000;
export const REFRESCO_SIMULACION_MS = 15_000;
export const REFRESCO_SIMULACION_RAPIDO_MS = 3_000;

type Accion = "recomendar" | "interpretar";

interface Entrada<T> {
  data: T;
  at: number;
}

const pending = new Map<string, Promise<unknown>>();
const done = new Map<string, Entrada<unknown>>();

export const keyOf = (accion: Accion, e: EntradaModelo) =>
  JSON.stringify([accion, e.monto_cop, e.transfronterizo, e.espera_s, e.irrevocabilidad, e.trm, e.modo ?? "vivo"]);

export async function pedirJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  return body as T;
}

function post(accion: Accion, e: EntradaModelo): Promise<unknown> {
  return pedirJson("/api/modelo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion, ...e }),
  });
}

function request<T>(accion: Accion, e: EntradaModelo, forzar = false): Promise<T> {
  const key = keyOf(accion, e);
  const hit = done.get(key);
  if (hit && !forzar && Date.now() - hit.at < TTL_MS) return Promise.resolve(hit.data as T);
  let p = pending.get(key);
  if (!p) {
    p = post(accion, e).then(
      (r) => {
        done.set(key, { data: r, at: Date.now() });
        pending.delete(key);
        return r;
      },
      (err) => {
        pending.delete(key);
        throw err;
      },
    );
    pending.set(key, p);
  }
  return p as Promise<T>;
}

export const pedirRecomendacion = (e: EntradaModelo) => request<RespuestaRecomendar>("recomendar", e);

export interface Estado<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  stale: boolean;
  actualizado: number | null;
}

const VACIO: Estado<never> = { data: null, error: null, loading: false, stale: false, actualizado: null };

function useReloj(ms: number): { n: number; ahora: number } {
  const [estado, setEstado] = useState(() => ({ n: 0, ahora: Date.now() }));
  useEffect(() => {
    const id = setInterval(() => setEstado((x) => ({ n: x.n + 1, ahora: Date.now() })), ms);
    return () => clearInterval(id);
  }, [ms]);
  return estado;
}

export const useAhora = (ms: number): number => useReloj(ms).ahora;

function useModel<T>(accion: Accion, e: EntradaModelo | null): Estado<T> {
  const key = e ? keyOf(accion, e) : null;
  const { n: tick, ahora } = useReloj(TTL_MS);
  const [settled, setSettled] = useState<{ key: string; error: string | null } | null>(null);
  const ultimoTick = useRef(0);

  useEffect(() => {
    if (!e || !key) return;
    let alive = true;
    const forzar = tick !== ultimoTick.current;
    ultimoTick.current = tick;
    request<T>(accion, e, forzar).then(
      () => alive && setSettled({ key, error: null }),
      (err: Error) => alive && setSettled({ key, error: err.message }),
    );
    return () => {
      alive = false;
    };
  }, [accion, key, tick]);

  if (!key) return VACIO;
  const hit = done.get(key);
  const data = (hit?.data as T | undefined) ?? null;
  const error = settled?.key === key ? settled.error : null;
  const stale = data !== null && (error !== null || ahora - (hit?.at ?? 0) > 2 * TTL_MS);
  return { data, error: data === null ? error : null, loading: data === null && error === null, stale, actualizado: hit?.at ?? null };
}

export const useRecomendacion = (e: EntradaModelo | null) => useModel<RespuestaRecomendar>("recomendar", e);
export const useInterpretacion = (e: EntradaModelo | null) => useModel<RespuestaInterpretar>("interpretar", e);

export function useRecomendaciones(entradas: EntradaModelo[]): (RespuestaRecomendar | null)[] {
  const keys = entradas.map((e) => keyOf("recomendar", e));
  const joined = keys.join("|");
  const { n: tick } = useReloj(TTL_MS);
  const [, bump] = useState(0);

  useEffect(() => {
    let alive = true;
    for (const e of entradas) {
      request("recomendar", e, tick > 0).then(
        () => alive && bump((n) => n + 1),
        () => alive && bump((n) => n + 1),
      );
    }
    return () => {
      alive = false;
    };
  }, [joined, tick]);

  return keys.map((k) => (done.get(k)?.data as RespuestaRecomendar | undefined) ?? null);
}

export function usePolling<T>(url: string, cadaMs: number, activo = true): Estado<T> & { recargar: () => void } {
  const [estado, setEstado] = useState<Estado<T>>({ ...VACIO, loading: true });
  const [version, setVersion] = useState(0);
  const recargar = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (!activo) return;
    let alive = true;
    const cargar = () =>
      pedirJson<T>(url).then(
        (data) => alive && setEstado({ data, error: null, loading: false, stale: false, actualizado: Date.now() }),
        (err: Error) =>
          alive &&
          setEstado((prev) => ({ ...prev, error: err.message, loading: false, stale: prev.data !== null })),
      );
    cargar();
    const id = setInterval(cargar, cadaMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [url, cadaMs, activo, version]);

  return { ...estado, recargar };
}

export const useInfoModelo = (): RespuestaInfo | null => usePolling<RespuestaInfo>("/api/modelo", 60_000).data;

export const useMediciones = () => usePolling<Instantanea>("/api/mediciones", REFRESCO_MEDICIONES_MS);

export const useRecalibracion = (rapido: boolean) =>
  usePolling<EstadoRecalibracion>("/api/recalibracion", rapido ? REFRESCO_RECALIBRACION_MS : 20_000);

export const iniciarRecalibracion = () =>
  pedirJson<{ id: string }>("/api/recalibracion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

export const cancelarRecalibracion = () => pedirJson<{ cancelando: boolean }>("/api/recalibracion", { method: "DELETE" });

export const useSimulacionEstado = (rapido: boolean) =>
  usePolling<EstadoSimulacion>("/api/simulacion", rapido ? REFRESCO_SIMULACION_RAPIDO_MS : REFRESCO_SIMULACION_MS);

export const useSimulacionResultados = (rapido: boolean) =>
  usePolling<ResultadosSimulacion>("/api/simulacion/resultados", rapido ? REFRESCO_SIMULACION_RAPIDO_MS * 2 : REFRESCO_SIMULACION_MS);

export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export function useEntrada(e: EntradaModelo | null): EntradaModelo | null {
  const key = e ? keyOf("recomendar", e) : null;
  return useMemo(() => e, [key]);
}
