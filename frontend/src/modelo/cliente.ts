"use client";

import { useEffect, useMemo, useState } from "react";
import type { EntradaModelo, RespuestaInfo, RespuestaInterpretar, RespuestaRecomendar } from "./tipos";

/**
 * Browser side of the bridge to the model. Every call goes to /api/modelo; results
 * are kept in memory by input, so a page that asks again (result, detail, history)
 * gets the same answer without running the model twice.
 */

type Accion = "recomendar" | "interpretar";

const pending = new Map<string, Promise<unknown>>();
const done = new Map<string, unknown>();

export const keyOf = (accion: Accion, e: EntradaModelo) =>
  JSON.stringify([accion, e.monto_cop, e.transfronterizo, e.espera_s, e.irrevocabilidad, e.trm]);

async function post(accion: Accion, e: EntradaModelo): Promise<unknown> {
  const res = await fetch("/api/modelo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion, ...e }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  return body;
}

function request<T>(accion: Accion, e: EntradaModelo): Promise<T> {
  const key = keyOf(accion, e);
  if (done.has(key)) return Promise.resolve(done.get(key) as T);
  let p = pending.get(key);
  if (!p) {
    p = post(accion, e).then(
      (r) => {
        done.set(key, r);
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
}

function useModel<T>(accion: Accion, e: EntradaModelo | null): Estado<T> {
  const key = e ? keyOf(accion, e) : null;
  const [settled, setSettled] = useState<{ key: string; error: string | null } | null>(null);

  useEffect(() => {
    if (!e || !key || done.has(key)) return;
    let alive = true;
    request<T>(accion, e).then(
      () => alive && setSettled({ key, error: null }),
      (err: Error) => alive && setSettled({ key, error: err.message }),
    );
    return () => {
      alive = false;
    };
    // `key` covers every field of `e`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accion, key]);

  if (!key) return { data: null, error: null, loading: false };
  const data = (done.get(key) as T | undefined) ?? null;
  const error = settled?.key === key ? settled.error : null;
  return { data, error, loading: data === null && error === null };
}

export const useRecomendacion = (e: EntradaModelo | null) => useModel<RespuestaRecomendar>("recomendar", e);
export const useInterpretacion = (e: EntradaModelo | null) => useModel<RespuestaInterpretar>("interpretar", e);

/** Several recommendations at once (home, history). Entries without an answer yet map to null. */
export function useRecomendaciones(entradas: EntradaModelo[]): (RespuestaRecomendar | null)[] {
  const keys = entradas.map((e) => keyOf("recomendar", e));
  const joined = keys.join("|");
  const [, bump] = useState(0);

  useEffect(() => {
    let alive = true;
    for (const e of entradas) {
      if (done.has(keyOf("recomendar", e))) continue;
      request("recomendar", e).then(
        () => alive && bump((n) => n + 1),
        () => alive && bump((n) => n + 1),
      );
    }
    return () => {
      alive = false;
    };
    // `joined` covers every entry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [joined]);

  return keys.map((k) => (done.get(k) as RespuestaRecomendar | undefined) ?? null);
}

let infoPromise: Promise<RespuestaInfo> | null = null;

/** Networks that have a measured profile in perfiles.json, and the date of the measurement. */
export function useInfoModelo(): RespuestaInfo | null {
  const [info, setInfo] = useState<RespuestaInfo | null>(null);
  useEffect(() => {
    let alive = true;
    infoPromise ??= fetch("/api/modelo")
      .then((r) => (r.ok ? (r.json() as Promise<RespuestaInfo>) : Promise.reject(new Error(`HTTP ${r.status}`))))
      .catch((err) => {
        infoPromise = null;
        throw err;
      });
    infoPromise.then((i) => alive && setInfo(i)).catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return info;
}

/** Value that follows `value` after it stops changing for `ms`. */
export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

/** Stable object identity for an input built during render. */
export function useEntrada(e: EntradaModelo | null): EntradaModelo | null {
  const key = e ? keyOf("recomendar", e) : null;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => e, [key]);
}
