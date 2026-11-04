"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, CheckCircle2, Loader2, WifiOff } from "lucide-react";
import { Card, Container, ProgressBar, SectionTitle, cx } from "@/components/ui";
import { REFRESCO_SIMULACION_MS, useAhora, useSimulacionEstado, useSimulacionResultados } from "@/modelo/cliente";
import type { CicloPanel, EstadoSimulacion, FilaPersonas, FuenteSimulacion, ResultadosSimulacion } from "@/modelo/tipos";
import { edadCorta } from "@/lib/monitor";
import { networkLabel } from "@/lib/format";
import {
  COLOR_AJUSTE,
  atributoMasSensible,
  bandaLegible,
  cambioPorEscenario,
  escenarios,
  nivelCambio,
  porcentaje,
  resumenPanel,
  segmentosAjuste,
  type Lectura,
} from "@/lib/simulacion";

const ATRIBUTOS = ["monto_x2", "monto_div2", "espera_x4", "espera_div4", "irrev_arriba", "irrev_abajo", "transfronterizo_inverso"];
const CALOR = ["text-grey", "bg-light-green", "bg-light-yellow", "bg-light-red"] as const;

const Tabla = ({ children }: { children: React.ReactNode }) => (
  <div className="overflow-x-auto">
    <table className="w-full min-w-[640px] border-collapse text-sm">{children}</table>
  </div>
);
const Th = ({ children, className }: { children?: React.ReactNode; className?: string }) => (
  <th className={cx("px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-muted", className)}>{children}</th>
);
const Td = ({ children, className, title }: { children?: React.ReactNode; className?: string; title?: string }) => (
  <td className={cx("border-t border-line/70 px-3 py-2", className)} title={title}>
    {children}
  </td>
);

function Bloque({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <Card className="mb-6 p-5 sm:p-6">
      <h2 className="text-xl font-extrabold">{title}</h2>
      {sub && <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">{sub}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function Celda({ x }: { x: number | "" | undefined }) {
  const v = x === undefined ? "" : x;
  return <Td className={cx("text-center font-bold tabular-nums", CALOR[nivelCambio(v)])}>{porcentaje(v)}</Td>;
}

function BarraAjuste({ f, lectura }: { f: FilaPersonas; lectura: Lectura }) {
  const t = useTranslations("simulation.fit");
  const segs = segmentosAjuste(f, lectura);
  const texto = segs.filter((s) => s.valor > 0).map((s) => `${t(`states.${s.estado}`)} ${porcentaje(s.valor)}`).join(" · ");
  return (
    <div title={texto} aria-label={texto} role="img">
      <div className="flex h-3 w-full min-w-[120px] overflow-hidden rounded-full bg-line/60">
        {segs
          .filter((s) => s.valor > 0)
          .map((s) => (
            <div key={s.estado} className={COLOR_AJUSTE[s.estado]} style={{ width: `${s.valor * 100}%` }} />
          ))}
      </div>
      <p className="mt-1 text-[11px] text-muted">{texto}</p>
    </div>
  );
}

function Estado({ data }: { data: EstadoSimulacion | null }) {
  const t = useTranslations("simulation.status");
  const ahora = useAhora(5000) / 1000;
  const lote = data?.lote ?? null;
  const panel = data?.continuo;
  return (
    <div className="mb-6 grid gap-4 md:grid-cols-2">
      <Card tone="surface" className="p-5">
        <h2 className="text-sm font-extrabold uppercase tracking-wide text-muted">{t("batch")}</h2>
        {!lote ? (
          <p className="mt-2 text-sm text-muted">{t("noBatch")}</p>
        ) : (
          <>
            <p className="mt-2 flex items-center gap-2 text-lg font-extrabold">
              {lote.estado === "en_curso" ? (
                <Loader2 size={18} className="animate-spin" aria-hidden />
              ) : lote.estado === "completado" ? (
                <CheckCircle2 size={18} className="text-ok" aria-hidden />
              ) : (
                <AlertTriangle size={18} className="text-warn" aria-hidden />
              )}
              {t(`state.${lote.estado}`)}
            </p>
            {lote.estado === "en_curso" && <div className="mt-2"><ProgressBar value={lote.progreso ?? 0} /></div>}
            <p className="mt-2 text-xs text-muted">
              {t("stage", { stage: lote.etapa })}
              {lote.evaluaciones !== undefined && ` · ${t("evaluations", { n: lote.evaluaciones })}`}
              {" · "}
              {lote.estado === "en_curso"
                ? t("elapsed", { age: edadCorta(ahora - lote.inicio) })
                : lote.fin
                  ? t("finished", { age: edadCorta(ahora - lote.fin) })
                  : ""}
            </p>
          </>
        )}
      </Card>
      <Card tone="surface" className="p-5">
        <h2 className="text-sm font-extrabold uppercase tracking-wide text-muted">{t("panel")}</h2>
        {!panel ? (
          <p className="mt-2 text-sm text-muted">—</p>
        ) : (
          <>
            <p className="mt-2 flex items-center gap-2 text-lg font-extrabold">
              <span className={cx("inline-block h-3 w-3 rounded-full", panel.activo ? "bg-ok" : "bg-grey")} aria-hidden />
              {panel.activo ? t("panelActive") : t("panelStopped")}
            </p>
            <p className="mt-2 text-xs text-muted">
              {panel.ciclos === 0
                ? t("noCycles")
                : `${t("cycles", { valid: panel.ciclos_validos, total: panel.ciclos })}${
                    panel.ultimo_ciclo_ts ? ` · ${t("lastCycle", { age: edadCorta(ahora - panel.ultimo_ciclo_ts) })}` : ""
                  }`}
              {" · "}
              {t("every", { time: edadCorta(panel.intervalo_s) })}
            </p>
            {panel.ultimo_error && <p className="mt-1 text-xs text-bad">{t("lastError", { error: panel.ultimo_error })}</p>}
          </>
        )}
      </Card>
    </div>
  );
}

function Cobertura({ filas }: { filas: FilaPersonas[] }) {
  const t = useTranslations("simulation.fit");
  return (
    <Bloque title={t("title")} sub={t("sub")}>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("profile")}</Th>
            <Th>{t("band")}</Th>
            <Th className="text-right">{t("users")}</Th>
            <Th className="text-right">{t("uncertain")}</Th>
            <Th className="text-right">{t("ties")}</Th>
            <Th>{t("preference")}</Th>
            <Th>{t("requirement")}</Th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.perfil}>
              <Td>
                <span className="font-bold">
                  {f.perfil}. {f.nombre}
                </span>
                <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase text-muted">
                  {t(`types.${f.tipo}`)}
                </span>
              </Td>
              <Td>
                <span className="font-bold">{f.banda1_modal.split("+").map((r) => networkLabel(r)).join(" + ") || bandaLegible(f.banda1_modal)}</span>
                <span className="ml-1 text-xs text-muted">{porcentaje(f.cuota_modal)}</span>
              </Td>
              <Td className="text-right tabular-nums" title={f.llego_al_tope ? t("cap") : undefined}>
                {f.n}
                {f.llego_al_tope && " ⚠"}
              </Td>
              <Td className="text-right tabular-nums">{porcentaje(f.cuota_certidumbre_baja)}</Td>
              <Td className="text-right tabular-nums">{porcentaje(f.empates_banda1)}</Td>
              <Td>
                <BarraAjuste f={f} lectura="preferencia" />
              </Td>
              <Td>
                <BarraAjuste f={f} lectura="requisito" />
              </Td>
            </tr>
          ))}
        </tbody>
      </Tabla>
      <p className="mt-3 text-xs leading-relaxed text-muted">{t("legend")}</p>
    </Bloque>
  );
}

function Contrafactuales({ datos, fuente }: { datos: ResultadosSimulacion; fuente: FuenteSimulacion }) {
  const t = useTranslations("simulation.counter");
  const filas = datos.contrafactuales.filter((f) => f.fuente === fuente);
  const medicion = escenarios(filas, "P3");
  const caidas = escenarios(filas, "P4");
  if (filas.length === 0) return null;
  return (
    <Bloque title={t("title")} sub={t("sub")}>
      <h3 className="mb-2 text-sm font-extrabold">{t("measurement")}</h3>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("profile")}</Th>
            {medicion.map((e) => (
              <Th key={e} className="text-center">
                {t(`scenarios.${e}`)}
              </Th>
            ))}
            <Th className="text-center">
              <span title={t("aptosHint")}>{t("aptos")}</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {datos.perfiles.map((p) => {
            const m = cambioPorEscenario(filas, "P3", p.id);
            return (
              <tr key={p.id}>
                <Td className="font-bold">
                  {p.id}. {p.nombre}
                </Td>
                {medicion.map((e) => (
                  <Celda key={e} x={m.get(e)?.cuota_cambio} />
                ))}
                <Td className="text-center tabular-nums" title={t("aptosHint")}>
                  {porcentaje(m.get("aptos_sombra")?.aptos_supera_a_la_mejor)}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </Tabla>
      <h3 className="mb-2 mt-6 text-sm font-extrabold">{t("drops")}</h3>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("profile")}</Th>
            {caidas.map((e) => (
              <Th key={e} className="text-center">
                {t("drop", { net: networkLabel(e.replace("sin_", "")) })}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {datos.perfiles.map((p) => {
            const m = cambioPorEscenario(filas, "P4", p.id);
            return (
              <tr key={p.id}>
                <Td className="font-bold">
                  {p.id}. {p.nombre}
                </Td>
                {caidas.map((e) => (
                  <Celda key={e} x={m.get(e)?.cuota_cambio} />
                ))}
              </tr>
            );
          })}
        </tbody>
      </Tabla>
    </Bloque>
  );
}

function Sensibilidad({ datos, fuente }: { datos: ResultadosSimulacion; fuente: FuenteSimulacion }) {
  const t = useTranslations("simulation.sens");
  const filas = datos.sensibilidad.filter((f) => f.fuente === fuente);
  if (filas.length === 0) return null;
  return (
    <Bloque title={t("title")} sub={t("sub")}>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("profile")}</Th>
            {ATRIBUTOS.map((a) => (
              <Th key={a} className="text-center">
                {t(`attrs.${a}`)}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {datos.perfiles.map((p) => {
            const mayor = atributoMasSensible(filas, p.id);
            const porAtributo = new Map(filas.filter((f) => f.perfil === p.id).map((f) => [f.atributo, f]));
            return (
              <tr key={p.id}>
                <Td className="font-bold">
                  {p.id}. {p.nombre}
                </Td>
                {ATRIBUTOS.map((a) => {
                  const f = porAtributo.get(a);
                  return (
                    <Td
                      key={a}
                      className={cx(
                        "text-center tabular-nums",
                        CALOR[nivelCambio(f?.cuota_cambio ?? "")],
                        mayor?.atributo === a && (mayor.cuota_cambio as number) > 0 && "font-extrabold",
                      )}
                    >
                      {porcentaje(f?.cuota_cambio)}
                    </Td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </Tabla>
    </Bloque>
  );
}

function Convergencia({ datos, fuente }: { datos: ResultadosSimulacion; fuente: FuenteSimulacion }) {
  const t = useTranslations("simulation.conv");
  const filas = datos.convergencia.filter((f) => f.fuente === fuente);
  if (filas.length === 0) return null;
  return (
    <Bloque title={t("title")} sub={t("sub")}>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("replicas")}</Th>
            <Th>{t("reference")}</Th>
            <Th className="text-right">{t("band1")}</Th>
            <Th className="text-right">{t("order")}</Th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.replicas}>
              <Td className="font-bold tabular-nums">{f.replicas.toLocaleString()}</Td>
              <Td className="tabular-nums">{f.referencia.toLocaleString()}</Td>
              <Td className="text-right tabular-nums">{porcentaje(f.coincide_banda1)}</Td>
              <Td className="text-right tabular-nums">{porcentaje(f.coincide_orden)}</Td>
            </tr>
          ))}
        </tbody>
      </Tabla>
    </Bloque>
  );
}

function colorCiclo(c: CicloPanel) {
  if (!c.valido) return "bg-line";
  return (c.cambios ?? 0) > 0 ? "bg-brand" : "bg-ok";
}

function Indicador({ etiqueta, valor, pista }: { etiqueta: string; valor: string; pista?: string }) {
  return (
    <div className="rounded-xl bg-surface p-4" title={pista}>
      <p className="text-xs font-bold uppercase tracking-wide text-muted">{etiqueta}</p>
      <p className="mt-1 text-2xl font-extrabold tabular-nums">{valor}</p>
    </div>
  );
}

function PanelContinuo({ serie, total }: { serie: CicloPanel[]; total: number }) {
  const t = useTranslations("simulation.panel");
  const ahora = useAhora(5000) / 1000;
  const r = resumenPanel(serie);
  if (serie.length === 0) {
    return (
      <Bloque title={t("title")} sub={t("sub")}>
        <p className="text-sm text-muted">{t("empty")}</p>
      </Bloque>
    );
  }
  const recientes = [...serie].reverse().slice(0, 12);
  return (
    <Bloque title={t("title")} sub={t("sub")}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Indicador etiqueta={t("stability")} valor={porcentaje(r.estabilidad, 1)} pista={t("stabilityHint")} />
        <Indicador etiqueta={t("differs")} valor={porcentaje(r.distintosDeBase, 1)} pista={t("differsHint")} />
        <Indicador etiqueta={t("valid")} valor={`${r.validos} / ${total}`} />
        <Indicador etiqueta={t("invalid")} valor={String(r.invalidos)} pista={t("invalidHint")} />
      </div>
      <div className="mt-5 flex flex-wrap items-end gap-[3px]" aria-hidden>
        {serie.slice(-120).map((c) => (
          <span key={c.id} className={cx("h-6 w-1.5 rounded-sm", colorCiclo(c))} title={`#${c.id} · ${c.valido ? `${c.cambios} cambios` : "inválido"}`} />
        ))}
      </div>
      <p className="mt-1 text-xs text-muted">{t("strip")}</p>
      <h3 className="mb-2 mt-5 text-sm font-extrabold">{t("recent")}</h3>
      <Tabla>
        <thead>
          <tr>
            <Th>{t("cycle")}</Th>
            <Th>{t("when")}</Th>
            <Th className="text-right">{t("live")}</Th>
            <Th className="text-right">{t("users")}</Th>
            <Th className="text-right">{t("changes")}</Th>
            <Th>{t("cause")}</Th>
          </tr>
        </thead>
        <tbody>
          {recientes.map((c) => (
            <tr key={c.id} className={cx(!c.valido && "text-grey")}>
              <Td className="tabular-nums">
                #{c.id}
                {!c.valido && <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase">{t("invalidTag")}</span>}
              </Td>
              <Td>{edadCorta(ahora - c.ts)}</Td>
              <Td className="text-right tabular-nums">
                {c.vivas} / {c.esperadas}
              </Td>
              <Td className="text-right tabular-nums">{c.usuarios ?? "—"}</Td>
              <Td className="text-right tabular-nums">{c.cambios ?? "—"}</Td>
              <Td className="text-xs">{c.causa ?? "—"}</Td>
            </tr>
          ))}
        </tbody>
      </Tabla>
    </Bloque>
  );
}

export default function SimulacionPage() {
  const t = useTranslations("simulation");
  const estado = useSimulacionEstado(false);
  const rapido = estado.data?.ocupado ?? false;
  const { data, error, loading, stale, actualizado } = useSimulacionResultados(rapido);
  const ahora = useAhora(5000);
  const [elegida, setElegida] = useState<FuenteSimulacion>("base");

  const fuentes = (["base", "vivo"] as FuenteSimulacion[]).filter((f) => data?.personas.some((p) => p.fuente === f));
  const fuente = fuentes.includes(elegida) ? elegida : (fuentes[0] ?? "base");
  const personas = data?.personas.filter((p) => p.fuente === fuente) ?? [];

  return (
    <Container className="max-w-6xl py-12">
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
          <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted">
            <span>{t("updated", { age: edadCorta(actualizado ? (ahora - actualizado) / 1000 : null) })}</span>
            <span>{t("refresh", { time: edadCorta((rapido ? 6_000 : REFRESCO_SIMULACION_MS) / 1000) })}</span>
            {stale && (
              <span className="flex items-center gap-2 font-bold text-warn" role="status">
                <WifiOff size={16} aria-hidden /> {t("staleBackend")}
              </span>
            )}
          </div>

          <Estado data={estado.data} />

          {!data.corrida ? (
            <Card tone="surface">
              <p className="text-muted">{t("empty")}</p>
            </Card>
          ) : (
            <>
              <p className="mb-4 text-xs text-muted">
                {t("run.line", {
                  id: data.corrida.id,
                  evals: data.corrida.evaluaciones ?? "—",
                  seed: data.corrida.config.semilla,
                  reps: data.corrida.config.replicas.toLocaleString(),
                  panel: data.corrida.config.panel_por_perfil,
                  age: edadCorta(data.corrida.fin ? ahora / 1000 - data.corrida.fin : null),
                })}
              </p>

              {fuentes.length > 1 && (
                <div className="mb-6 flex items-center gap-2" role="tablist" aria-label={t("source.label")}>
                  {fuentes.map((f) => (
                    <button
                      key={f}
                      role="tab"
                      aria-selected={f === fuente}
                      onClick={() => setElegida(f)}
                      className={cx(
                        "rounded-full border-[1.5px] border-ink px-4 py-1.5 text-sm font-semibold",
                        f === fuente ? "bg-brand" : "bg-paper hover:bg-surface",
                      )}
                    >
                      {t(`source.${f}`)}
                    </button>
                  ))}
                </div>
              )}

              <Bloque title={t("alerts.title")}>
                {data.alertas.length === 0 ? (
                  <p className="text-sm text-muted">{t("alerts.none")}</p>
                ) : (
                  <ul className="space-y-1.5 text-sm">
                    {data.alertas
                      .filter((a) => a.includes(`${fuente})`))
                      .map((a) => (
                        <li key={a} className="flex gap-2">
                          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn" aria-hidden />
                          <span lang="es">{a.replace(/^ALERTA /, "")}</span>
                        </li>
                      ))}
                  </ul>
                )}
              </Bloque>

              <Cobertura filas={personas} />
              <Contrafactuales datos={data} fuente={fuente} />
              <Sensibilidad datos={data} fuente={fuente} />
              <Convergencia datos={data} fuente={fuente} />
            </>
          )}

          <PanelContinuo serie={data.vivo.serie} total={data.vivo.ciclos_total} />
          <p className="mt-6 text-xs leading-relaxed text-muted">{t("disclaimer")}</p>
        </>
      )}
    </Container>
  );
}
