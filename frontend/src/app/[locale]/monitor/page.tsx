"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, ChevronDown, Loader2, RefreshCw, WifiOff } from "lucide-react";
import { Button, Card, Container, ProgressBar, SectionTitle, Semaphore, cx } from "@/components/ui";
import { UNIDAD } from "@/modelo/entrada";
import {
  cancelarRecalibracion,
  useAhora,
  iniciarRecalibracion,
  useMediciones,
  useRecalibracion,
} from "@/modelo/cliente";
import type { MetricaMedicion, RedMedicion } from "@/modelo/tipos";
import { colorSalud, edadCorta, etiquetaMetrica, razonBase, resumenRed, trabajoActivo } from "@/lib/monitor";
import { networkLabel as label, useFmt } from "@/lib/format";

function Etiqueta({ m }: { m: MetricaMedicion }) {
  const t = useTranslations("liveData.tag");
  const e = etiquetaMetrica(m);
  const estilo = {
    vivo: "bg-brand text-ink",
    base: "border border-line text-muted",
    sin_dato: "border border-dashed border-grey text-grey",
  }[e];
  return (
    <span className={cx("rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide", estilo)}>
      {e === "vivo" ? t("live") : e === "base" ? t("base") : t("none")}
    </span>
  );
}

function FilaMetrica({ m }: { m: MetricaMedicion }) {
  const t = useTranslations("liveData");
  const tm = useTranslations("metrics");
  const fmt = useFmt();
  const razon = razonBase(m);
  return (
    <li className="grid items-start gap-x-6 gap-y-1 py-3 sm:grid-cols-[1fr_auto]">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 font-bold">
          <span className="rounded-md bg-surface px-1.5 py-0.5 text-xs">{m.id}</span>
          {tm(`${m.id}.name`)}
          <Etiqueta m={m} />
          {m.cota_inferior && (
            <span className="rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
              {t("lowerBound")}
            </span>
          )}
        </p>
        <p className="mt-0.5 text-xs text-muted">
          {m.origen === "vivo" &&
            t("meta.live", { age: edadCorta(m.edad_s), n: m.n ?? 0, window: edadCorta(m.ventana_s) })}
          {m.origen === "base" && t("meta.base", { source: m.fuente ?? "—", age: edadCorta(m.edad_s) })}
          {razon && ` · ${t(`why.${razon}`)}`}
        </p>
        {m.razon_solo_base && (
          <p className="mt-0.5 text-xs text-muted" lang="es">
            {m.razon_solo_base}
          </p>
        )}
        {m.vivo && m.origen !== "vivo" && m.vivo.nota && (
          <p className="mt-0.5 text-xs text-muted" lang="es">
            {m.vivo.nota}
          </p>
        )}
      </div>
      <p className="text-xl font-extrabold tabular-nums sm:text-right">
        {m.valor === null ? <span className="text-grey">—</span> : fmt.metricValue(m.valor, UNIDAD[m.id])}
      </p>
    </li>
  );
}

function TarjetaRed({ red }: { red: RedMedicion }) {
  const t = useTranslations("liveData");
  const { vivas, esperadas, sinDato, total } = resumenRed(red);
  const comps = red.salud.componentes;
  return (
    <Card className="p-5 sm:p-6">
      <details className="group" open={red.salud.estado !== "ok"}>
        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-4">
          <Semaphore light={colorSalud[red.salud.estado]} size="lg" />
          <span className="min-w-0 flex-1">
            <span className="block text-xl font-extrabold">{label(red.id)}</span>
            <span className="block text-xs text-muted">
              {t("owner", { name: red.responsable })} · {red.fuente}
            </span>
          </span>
          <span className="text-right text-sm">
            <span className="block font-extrabold">{t("liveCount", { n: vivas, total: esperadas })}</span>
            <span className="block text-xs text-muted">{t(`health.${red.salud.estado}`)}</span>
          </span>
          <ChevronDown size={20} className="shrink-0 text-grey transition-transform group-open:rotate-180" aria-hidden />
        </summary>

        <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {comps.length === 0 && <p className="text-sm text-muted">{t("noCollector")}</p>}
          {comps.map((c) => (
            <div key={c.componente} className="rounded-xl bg-surface p-3 text-xs">
              <p className="flex items-center gap-2 font-extrabold uppercase tracking-wide">
                <Semaphore light={c.fallos_consecutivos > 0 ? "red" : "green"} size="xs" />
                {t(`component.${c.componente}`)}
              </p>
              <p className="mt-1 text-muted">
                {c.ultimo_ok ? t("lastOk", { age: edadCorta(c.edad_ok_s) }) : t("neverOk")}
                {c.latencia_ms ? ` · ${Math.round(c.latencia_ms)} ms` : ""}
              </p>
              {c.fallos_consecutivos > 0 && (
                <p className="mt-1 text-bad" lang="en">
                  {t("failures", { n: c.fallos_consecutivos })} {c.error}
                </p>
              )}
            </div>
          ))}
        </div>

        <p className="mt-4 text-xs text-muted">
          {t("samples", {
            blocks: red.muestras.muestras_bloque ?? 0,
            txs: red.muestras.muestras_tx ?? 0,
            finality: red.muestras.muestras_finalidad ?? 0,
          })}{" "}
          · {t("coverage", { live: vivas, base: total - vivas - sinDato, none: sinDato })}
        </p>

        <ul className="mt-2 divide-y divide-line/70">
          {red.metricas.map((m) => (
            <FilaMetrica key={m.id} m={m} />
          ))}
        </ul>
      </details>
    </Card>
  );
}

function Recalibrar() {
  const t = useTranslations("liveData.recalibrate");
  const [activo, setActivo] = useState(false);
  const estado = useRecalibracion(activo);
  const [error, setError] = useState<string | null>(null);
  const trabajo = estado.data?.trabajo ?? null;
  const corriendo = trabajoActivo(trabajo?.estado) || (estado.data?.ocupado ?? false);
  if (activo !== corriendo) setActivo(corriendo);
  const alcance = estado.data?.alcance;

  async function lanzar() {
    setError(null);
    try {
      await iniciarRecalibracion();
      setActivo(true);
      estado.recargar();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function cancelar() {
    setError(null);
    try {
      await cancelarRecalibracion();
      estado.recargar();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <Card tone="surface" className="mb-10">
      <h2 className="text-xl font-extrabold">{t("title")}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">{t("desc")}</p>

      {alcance && (
        <ul className="mt-3 space-y-1 text-xs text-muted">
          <li>{t("scopeDoes", { nets: alcance.recalibra.map(label).join(", ") })}</li>
          {alcance.rellena.length > 0 && (
            <li>
              {t("scopeFills", { nets: alcance.rellena.map(label).join(", ") })} <span lang="es">{alcance.nota_rellena}</span>
            </li>
          )}
          {alcance.no_disponible.length > 0 && (
            <li>
              {t("scopeNot", { nets: alcance.no_disponible.map(label).join(", ") })} <span lang="es">{alcance.motivo_no_disponible}</span>
            </li>
          )}
          <li>
            {t("scopeCannot")} <span lang="es">{alcance.no_resuelve.join("; ")}</span>
          </li>
        </ul>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button onClick={lanzar} disabled={corriendo || estado.loading}>
          {corriendo ? <Loader2 size={16} className="mr-2 animate-spin" aria-hidden /> : <RefreshCw size={16} className="mr-2" aria-hidden />}
          {corriendo ? t("running") : t("run")}
        </Button>
        {corriendo && (
          <Button variant="secondary" onClick={cancelar}>
            {t("cancel")}
          </Button>
        )}
      </div>

      {error && (
        <p className="mt-3 flex items-center gap-2 text-sm font-bold text-bad" role="alert">
          <AlertTriangle size={16} aria-hidden /> {error}
        </p>
      )}
      {estado.error && !estado.data && <p className="mt-3 text-sm text-bad">{estado.error}</p>}

      {trabajo && (
        <div className="mt-5">
          <p className="mb-2 text-sm font-bold">
            {t(`state.${trabajo.estado}`)} · {Math.round(trabajo.progreso * 100)} %
            {trabajo.etapa ? ` · ${trabajo.etapa}` : ""}
          </p>
          <ProgressBar value={trabajo.progreso} />
          {trabajo.log_tail && (
            <pre className="mt-3 max-h-48 overflow-auto rounded-xl bg-ink p-3 text-[11px] leading-snug text-white">{trabajo.log_tail}</pre>
          )}
        </div>
      )}
    </Card>
  );
}

export default function MonitorPage() {
  const t = useTranslations("liveData");
  const { data, error, loading, stale, actualizado } = useMediciones();
  const fmt = useFmt();
  const ahora = useAhora(5000);

  return (
    <Container className="max-w-5xl py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>

      {loading && (
        <p className="flex items-center gap-3 text-lg font-bold" role="status">
          <Loader2 size={22} className="animate-spin" aria-hidden /> {t("loading")}
        </p>
      )}

      {error && !data && (
        <Card className="text-center">
          <AlertTriangle size={32} className="mx-auto mb-3 text-bad" aria-hidden />
          <p className="font-bold">{t("error")}</p>
          <p className="mt-1 text-sm text-muted">{error}</p>
        </Card>
      )}

      {data && (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <span className="font-bold">
              {t("versionLine", {
                version: data.version_perfil,
                live: data.frescura.metricas_vivo,
                total: data.frescura.metricas_total,
              })}
            </span>
            <span className="text-muted">
              {t("updated", { age: edadCorta(actualizado ? (ahora - actualizado) / 1000 : null) })} ·{" "}
              {t("staleAfter", { time: fmt.seconds(data.obsolescencia_s) })}
            </span>
            {stale && (
              <span className="flex items-center gap-2 font-bold text-warn" role="status">
                <WifiOff size={16} aria-hidden /> {t("staleBackend")}
              </span>
            )}
          </div>

          <Recalibrar />

          {data.redes.length === 0 ? (
            <p className="text-muted">{t("empty")}</p>
          ) : (
            <div className="space-y-4">
              {data.redes.map((r) => (
                <TarjetaRed key={r.id} red={r} />
              ))}
            </div>
          )}
          <p className="mt-6 text-xs text-muted">{t("legend")}</p>
        </>
      )}
    </Container>
  );
}
