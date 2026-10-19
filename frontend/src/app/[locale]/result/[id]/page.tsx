"use client";

import { use, useState } from "react";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, ArrowRight, CalendarDays, Clock, Coins, Loader2, RotateCcw, Scale, ShieldAlert } from "lucide-react";
import {
  Button,
  ButtonLink,
  buttonClass,
  Card,
  Container,
  DemoBadge,
  Field,
  inputClass,
  Semaphore,
  cx,
} from "@/components/ui";
import { PaymentAttributes } from "@/components/result/PaymentAttributes";
import { Link } from "@/i18n/navigation";
import { BLOCKS } from "@/engine/metrics";
import { SCENARIO_IDS, type BlockId, type Irreversibility, type NetworkId, type TxInput } from "@/engine/types";
import { useDebounced, useEntrada, useRecomendacion } from "@/modelo/cliente";
import { AvisoDatos, SinRecomendacion } from "@/components/result/EstadoDatos";
import {
  blocksAhead,
  composicionPorEscenario,
  entradaModelo,
  escenarioDominante,
  luzPuntaje,
  luzRed,
  redesEnOrden,
  valueOf,
} from "@/modelo/entrada";
import { esCompleta, type DetalleRed, type RespuestaCompleta, type RespuestaRecomendar } from "@/modelo/tipos";
import { txQuery } from "@/lib/attrs";
import { networkLabel as label, useFmt } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

type Override = { amountCop?: number; waitSec?: number; irreversibility?: Irreversibility };

const LEVEL = { alta: "high", media: "medium", baja: "low" } as const;

export default function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useTranslations("result");
  const ts = useTranslations("scenarios");
  const tm = useTranslations("metrics");
  const tg = useTranslations("gates");
  const tb = useTranslations("detail.block");
  const tt = useTranslations("tx");
  const fmt = useFmt();
  const { ready } = useRequireUser();
  const store = useStore();
  const entry = store.history.find((h) => h.id === id);

  const [override, setOverride] = useState<Override | null>(null);
  const settledOverride = useDebounced(override, 400);
  const tx: TxInput | undefined = entry ? { ...entry.tx, ...override } : undefined;

  const original = useRecomendacion(useEntrada(entry ? entradaModelo(entry.tx, entry.answers.country) : null));
  const current = useRecomendacion(
    useEntrada(entry ? entradaModelo({ ...entry.tx, ...settledOverride }, entry.answers.country) : null),
  );
  // While a new what-if runs, keep showing the last answer instead of blanking the page.
  const [shown, setShown] = useState<RespuestaRecomendar | null>(null);
  if (current.data && current.data !== shown) setShown(current.data);
  const rec = current.data ?? shown;
  const stale = override !== settledOverride || current.loading;

  if (!ready) return <Container className="py-12" />;
  if (!entry || !tx) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{t("notFound")}</p>
        <ButtonLink href="/home">{t("backHome")}</ButtonLink>
      </Container>
    );
  }
  if (!rec) {
    return (
      <Container className="max-w-xl py-20 text-center">
        {current.error ? (
          <>
            <AlertTriangle size={32} className="mx-auto mb-4 text-bad" aria-hidden />
            <p className="mb-2 text-lg font-bold">{t("model.error")}</p>
            <p className="mb-6 text-sm text-muted">{current.error}</p>
            <Button onClick={() => window.location.reload()}>{t("model.retry")}</Button>
          </>
        ) : (
          <p className="flex items-center justify-center gap-3 text-lg font-bold" role="status">
            <Loader2 size={22} className="animate-spin" aria-hidden /> {t("model.loading")}
          </p>
        )}
      </Container>
    );
  }

  if (!esCompleta(rec)) return <SinRecomendacion rec={rec} />;

  const r = rec.resultado;
  const band1 = r.bandas[0];
  const winners = band1?.redes ?? [];
  const tied = winners.length > 1;
  const nextBand = r.bandas[1];
  const dominant = escenarioDominante(r.composicion);
  const composition = composicionPorEscenario(r.composicion);
  const ordered = [...redesEnOrden(r), ...Object.keys(r.inadmisibles)];
  const originalWinners = original.data?.resultado?.bandas[0]?.redes ?? [];
  const changed = override && original.data && winners.join() !== originalWinners.join();
  const accepted = tx.recipient.accepted;
  const notAccepted = (red: string) => accepted !== "unknown" && !accepted.includes(red as NetworkId);
  const q = txQuery(tx);
  const single = !tied && winners[0] ? winners[0] : null;
  const runnerUp = single && nextBand ? nextBand.redes[0] : null;

  return (
    <Container className={cx("py-12 transition-opacity", stale && "opacity-70")}>
      <p className="mb-4 flex flex-wrap items-center gap-2 text-sm font-bold uppercase tracking-[0.14em] text-muted">
        {fmt.cop(r.caso.monto_cop)} ≈ {fmt.usdt(r.caso.ticket_usd)} · {ts(`${dominant}.name`)}
        {stale && <Loader2 size={14} className="animate-spin" aria-label={t("model.loading")} />}
      </p>
      <AvisoDatos rec={rec} obsoleto={current.stale} />

      {band1 ? (
        <section className="animate-fade-up grid gap-5 lg:grid-cols-5">
          <div className="relative overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10 lg:col-span-3">
            <span aria-hidden className="absolute -right-12 -top-12 h-52 w-52 rounded-full bg-white/30" />
            <div className="relative">
              <p className="text-xs font-bold uppercase tracking-[0.14em]">{tied ? t("best.kickerTie") : t("best.kicker")}</p>
              <h1 className="mt-3 text-5xl font-extrabold tracking-tight sm:text-6xl">
                {winners.map(label).join(" · ")}
              </h1>
              <p className="mt-4 max-w-lg leading-relaxed">
                {tied
                  ? t("best.tied", { scenario: ts(`${dominant}.name`) })
                  : t("best.summary", { network: label(winners[0]), scenario: ts(`${dominant}.name`) })}
              </p>
              {band1.no_distinguibles && (
                <p className="mt-2 max-w-lg rounded-2xl bg-paper/70 px-4 py-2 text-sm font-semibold">
                  {t("best.notDistinguishable", { detail: band1.no_distinguibles })}
                </p>
              )}

              {winners.map((red) => {
                const d = rec.detalle[red];
                const fee = valueOf(d, "A1");
                const inclusion = valueOf(d, "B1");
                const finality = valueOf(d, "B2b") ?? valueOf(d, "B2");
                return (
                  <div key={red} className="mt-8">
                    {tied && <p className="mb-2 text-sm font-extrabold">{label(red)}</p>}
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Stat
                        icon={<Coins size={15} aria-hidden />}
                        label={t("best.fee")}
                        value={fee !== null ? fmt.usdt(fee) : "—"}
                        sub={fee !== null ? `≈ ${fmt.copSmall(fee * rec.trm)}` : ""}
                      />
                      <Stat
                        icon={<Clock size={15} aria-hidden />}
                        label={t("best.time")}
                        value={inclusion !== null ? fmt.seconds(inclusion) : "—"}
                        sub={finality !== null ? t("best.finality", { time: fmt.seconds(finality) }) : ""}
                      />
                      <div className="rounded-2xl bg-paper p-4">
                        <p className="flex items-center gap-1.5 text-xs font-bold text-muted">
                          <ShieldAlert size={15} aria-hidden /> {t("best.risk")}
                        </p>
                        <div className="mt-3">
                          <Semaphore light={luzRed(r, red)} size="lg" ring />
                        </div>
                      </div>
                    </div>
                    {notAccepted(red) && (
                      <p className="mt-3 rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white">
                        {t("recipientNotice", { network: label(red) })}
                      </p>
                    )}
                  </div>
                );
              })}
              <p className="mt-5 text-xs">{t("best.disclaimer")}</p>
            </div>
          </div>

          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-xl font-extrabold">{tied ? t("why.titleTie") : t("why.title")}</h2>
            <p className="text-sm leading-relaxed">
              {r.determinante
                ? t("why.determinant", { metric: `${r.determinante.metrica} · ${tm(`${r.determinante.metrica}.name`)}` })
                : t("why.noDeterminant")}
            </p>
            {nextBand && band1.separacion_con_siguiente !== undefined && (
              <p className="mt-3 text-sm leading-relaxed text-muted">
                {t("why.separation", {
                  a: label(winners[0]),
                  network: label(nextBand.redes[0]),
                  p: fmt.decimal(band1.separacion_con_siguiente, 2),
                })}
              </p>
            )}
            {winners.map((red) => (
              <div key={red}>
                <h3 className="mb-3 mt-6 text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  {t("why.blocks", { network: label(red) })}
                </h3>
                <BlockBars d={rec.detalle[red]} />
              </div>
            ))}
          </Card>
        </section>
      ) : (
        <section className="rounded-[28px] bg-light-red/10 p-8 ring-2 ring-light-red sm:p-10">
          <div className="flex items-center gap-4">
            <Semaphore light="red" size="lg" />
            <h1 className="text-2xl font-extrabold">{t("none.title")}</h1>
          </div>
          <p className="mt-3 max-w-2xl">{t("none.body")}</p>
        </section>
      )}

      {changed && (
        <p role="status" className="mt-5 rounded-2xl bg-brand-soft px-5 py-4 text-sm font-bold">
          {t("changed", { from: originalWinners.map(label).join(" · ") || "—", to: winners.map(label).join(" · ") || "—" })}
        </p>
      )}

      <Card className="mt-5">
        <h2 className="text-xl font-extrabold">{t("case.title")}</h2>
        <p className="mb-6 mt-1 text-sm text-muted">{t("case.sub")}</p>
        <div className="grid gap-8 md:grid-cols-2">
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-muted">{t("case.composition")}</h3>
            <ul className="space-y-3">
              {SCENARIO_IDS.map((e) => (
                <li key={e}>
                  <div className="mb-1 flex justify-between text-sm font-bold">
                    <span>{ts(`${e}.name`)}</span>
                    <span className="tabular-nums">{fmt.percent(composition[e])}</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-surface">
                    <div className="h-2.5 rounded-full bg-ink" style={{ width: `${composition[e] * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-muted">{t("case.certainty")}</h3>
            <div className="flex items-center gap-4">
              <Semaphore
                light={rec.nivel_certidumbre === "alta" ? "green" : rec.nivel_certidumbre === "media" ? "yellow" : "red"}
                size="lg"
              />
              <p className="text-2xl font-extrabold">
                {t(`case.level.${LEVEL[rec.nivel_certidumbre]}`)}{" "}
                <span className="text-base font-semibold text-muted">κ = {fmt.decimal(r.certidumbre, 2)}</span>
              </p>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted">{t("case.certaintyNote")}</p>
          </div>
        </div>

        {r.advertencias.length > 0 && (
          <div className="mt-6 rounded-2xl bg-light-yellow/15 px-5 py-4">
            <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em]">
              <AlertTriangle size={14} aria-hidden /> {t("model.warnings")}
            </p>
            <ul className="list-disc space-y-1 pl-5 text-sm" lang="es">
              {r.advertencias.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="mt-6 flex items-center gap-2 border-t border-line pt-4 text-sm font-bold">
          <CalendarDays size={16} aria-hidden /> {t("model.measurement", { when: rec.medicion })}
        </p>
        <p className="mt-2 text-xs text-muted">
          {t("why.weights")} {BLOCKS.map((b) => `${b} ${fmt.percent(r.pesos[b])}`).join(" · ")}
        </p>
      </Card>

      <Card className="mt-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl font-extrabold">
            <Scale size={20} aria-hidden /> {t("adjust.title")}
          </h2>
          {override && (
            <Button variant="secondary" size="sm" onClick={() => setOverride(null)}>
              <RotateCcw size={14} aria-hidden /> {t("adjust.reset")}
            </Button>
          )}
        </div>
        <p className="mb-6 text-sm text-muted">{t("adjust.sub")}</p>
        <Field label={tt("q.amount")}>
          <input
            inputMode="numeric"
            className={`${inputClass} max-w-xs font-extrabold`}
            value={new Intl.NumberFormat("es-CO").format(tx.amountCop)}
            onChange={(e) => {
              const n = Number(e.target.value.replace(/\D/g, ""));
              if (n >= 1) setOverride((o) => ({ ...o, amountCop: n }));
            }}
          />
        </Field>
        <PaymentAttributes
          waitSec={tx.waitSec}
          irreversibility={tx.irreversibility}
          onChange={(next) => setOverride((o) => ({ ...o, ...next }))}
        />
      </Card>

      {r.bandas.length > 0 && (
        <section className="mt-10">
          <h2 className="text-2xl font-extrabold tracking-tight">{t("bands.title")}</h2>
          <p className="mb-5 mt-1 max-w-3xl text-muted">{t("bands.sub")}</p>
          <div className="space-y-3">
            {r.bandas.map((band, i) => (
              <div key={band.banda} className="rounded-card border-[1.5px] border-line bg-paper p-5">
                <div className="mb-3 flex flex-wrap items-center gap-3">
                  <span className="rounded-full bg-ink px-3 py-1 text-xs font-extrabold uppercase tracking-wider text-brand">
                    {t("bands.band", { n: band.banda })}
                  </span>
                  {band.redes.length > 1 && (
                    <span className="rounded-full bg-brand px-3 py-1 text-xs font-extrabold">{t("bands.tie")}</span>
                  )}
                  {band.no_distinguibles && <span className="text-xs text-muted">{band.no_distinguibles}</span>}
                </div>
                <ul className="space-y-3">
                  {band.redes.map((red) => (
                    <ScoreBar key={red} red={red} rec={rec} />
                  ))}
                </ul>
                {band.separacion_con_siguiente !== undefined && r.bandas[i + 1] && (
                  <p className="mt-3 text-sm text-muted">
                    {t("bands.pi", {
                      a: label(band.redes[0]),
                      b: label(r.bandas[i + 1].redes[0]),
                      p: fmt.decimal(band.separacion_con_siguiente, 2),
                    })}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("compare.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("compare.sub")}</p>
        <ul className="space-y-3">
          {ordered.map((red) => (
            <NetworkRow
              key={red}
              red={red}
              rec={rec}
              q={q}
              id={id}
              isWinner={winners.includes(red)}
              notAccepted={notAccepted(red)}
            />
          ))}
        </ul>
      </section>

      {Object.keys(r.inadmisibles).length > 0 && (
        <Card tone="surface" className="mt-8">
          <h2 className="flex items-center gap-3 text-xl font-extrabold">
            <Semaphore light="red" /> {t("excluded.title")}
          </h2>
          <p className="mb-5 mt-1 text-sm text-muted">{t("excluded.sub")}</p>
          <div className="grid gap-4 md:grid-cols-2">
            {Object.entries(r.inadmisibles).map(([red, fallas]) => (
              <div key={red} className="rounded-2xl bg-paper p-5">
                <p className="mb-2 font-extrabold">{label(red)}</p>
                <ul className="space-y-1.5 text-sm text-muted">
                  {fallas.map(([gate, motivo]) => (
                    <li key={gate}>
                      {t("excluded.gate", { gate, name: tg(`${gate}.name`) })} <span lang="es">{motivo}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}

      {single && runnerUp && (
        <VsCard a={single} b={runnerUp} rec={rec} title={t("vs.title", { network: label(single), other: label(runnerUp) })} tb={tb} />
      )}

      <Card tone="surface" className="mt-8">
        <h2 className="mb-2 text-lg font-extrabold">{t("provenance.title")}</h2>
        <p className="text-sm leading-relaxed text-muted">{t("provenance.thesis")}</p>
        <p className="mt-2 text-sm leading-relaxed text-muted">{t("provenance.benchmark")}</p>
        <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-muted">
          <DemoBadge /> {t("disclaimer")}
        </p>
      </Card>

      <div className="mt-8 flex flex-wrap gap-3">
        <ButtonLink href="/transaction/new" size="lg">
          {t("actions.new")} <ArrowRight size={18} aria-hidden />
        </ButtonLink>
        <ButtonLink href="/history" variant="secondary" size="lg">
          {t("actions.history")}
        </ButtonLink>
        <ButtonLink href="/standard" variant="ghost" size="lg">
          {t("actions.standard")}
        </ButtonLink>
      </div>
    </Container>
  );
}

function Stat({ icon, label, value, sub }: { icon: ReactNode; label: string; value: string; sub: string }) {
  return (
    <div className="rounded-2xl bg-paper p-4">
      <p className="flex items-center gap-1.5 text-xs font-bold text-muted">
        {icon} {label}
      </p>
      <p className="mt-2 text-xl font-extrabold tracking-tight">{value}</p>
      <p className="text-xs text-muted">{sub}</p>
    </div>
  );
}

function BlockBars({ d }: { d: DetalleRed | undefined }) {
  const tb = useTranslations("detail.block");
  const fmt = useFmt();
  if (!d) return null;
  return (
    <ul className="space-y-3">
      {BLOCKS.map((b) => {
        const score = d.bloques[b];
        return (
          <li key={b}>
            <div className="mb-1 flex justify-between text-sm font-bold">
              <span>
                <span className="mr-2 inline-grid h-6 w-6 place-items-center rounded-full bg-brand text-xs">{b}</span>
                {tb(b)}
              </span>
              <span className="tabular-nums">{score !== null ? fmt.decimal(score, 2) : "—"}</span>
            </div>
            <div className="h-2 rounded-full bg-surface">
              <div className="h-2 rounded-full bg-brand" style={{ width: `${(score ?? 0) * 100}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function ScoreBar({ red, rec }: { red: string; rec: RespuestaCompleta }) {
  const t = useTranslations("result.bands");
  const fmt = useFmt();
  const p = rec.resultado.bandas.find((b) => b.redes.includes(red))?.puntajes[red];
  if (!p) return null;
  return (
    <li className="grid items-center gap-x-4 gap-y-1 sm:grid-cols-[9rem_1fr_9rem]">
      <span className="flex items-center gap-2 font-extrabold">
        <Semaphore light={luzRed(rec.resultado, red)} size="sm" /> {label(red)}
      </span>
      <div className="relative h-6" role="img" aria-label={`${t("range")}: ${fmt.decimal(p.p05, 3)} – ${fmt.decimal(p.p95, 3)}`}>
        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-surface" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-grey/60"
          style={{ left: `${p.p05 * 100}%`, width: `${Math.max((p.p95 - p.p05) * 100, 0.8)}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-paper bg-ink shadow"
          style={{ left: `${p.mediana * 100}%` }}
        />
      </div>
      <span className="text-right text-sm tabular-nums">
        <span className="font-extrabold">{fmt.decimal(p.mediana, 3)}</span>{" "}
        <span className="text-xs text-muted">
          [{fmt.decimal(p.p05, 3)}–{fmt.decimal(p.p95, 3)}]
        </span>
      </span>
    </li>
  );
}

function NetworkRow({
  red,
  rec,
  q,
  id,
  isWinner,
  notAccepted,
}: {
  red: string;
  rec: RespuestaCompleta;
  q: string;
  id: string;
  isWinner: boolean;
  notAccepted: boolean;
}) {
  const t = useTranslations("result");
  const fmt = useFmt();
  const r = rec.resultado;
  const d = rec.detalle[red];
  const band = r.bandas.find((b) => b.redes.includes(red))?.banda ?? null;
  const fee = valueOf(d, "A1");
  const inclusion = valueOf(d, "B1");

  return (
    <li
      className={cx(
        "grid items-center gap-x-5 gap-y-4 rounded-card border-[1.5px] bg-paper p-5 transition-shadow hover:shadow-card lg:grid-cols-[2fr_auto_2fr_1.3fr_auto]",
        isWinner ? "border-ink" : "border-line",
        band === null && "bg-surface",
      )}
    >
      <div className="flex items-center gap-4">
        <span
          className={cx(
            "grid h-11 w-11 shrink-0 place-items-center rounded-full text-xs font-extrabold",
            band === 1 ? "bg-brand" : band === null ? "bg-line" : "bg-surface",
          )}
          title={band !== null ? t("bands.band", { n: band }) : undefined}
        >
          {band !== null ? `B${band}` : "—"}
        </span>
        <div>
          <p className="text-lg font-extrabold leading-tight">{label(red)}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {isWinner && (
              <span className="inline-block rounded-full bg-ink px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-brand">
                {t("compare.best")}
              </span>
            )}
            {band === null && (
              <span className="inline-block rounded-full bg-light-red px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-white">
                {t("compare.excludedTag")}
              </span>
            )}
            {notAccepted && (
              <span className="inline-block rounded-full border border-line px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
                {t("compare.notAcceptedTag")}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2" title={t("compare.global")}>
        <Semaphore light={luzRed(r, red)} size="lg" />
        <span className="text-xs font-bold uppercase tracking-wide text-muted lg:sr-only">{t("compare.global")}</span>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {BLOCKS.map((b) => {
          const light = luzPuntaje(d?.bloques[b] ?? null);
          return (
            <div key={b} className="flex flex-col items-center gap-1.5 text-center">
              {light ? <Semaphore light={light} size="md" /> : <span className="h-5 w-5 rounded-full border-2 border-dashed border-grey" />}
              <span className="text-xs font-extrabold text-muted">{b}</span>
            </div>
          );
        })}
      </div>

      <div className="text-sm lg:text-right">
        <p className="font-bold tabular-nums">{fee !== null ? fmt.usdt(fee) : "—"}</p>
        <p className="tabular-nums text-muted">{inclusion !== null ? fmt.seconds(inclusion) : "—"}</p>
      </div>

      <Link
        href={`/result/${id}/${red}?${q}`}
        className={buttonClass(isWinner ? "primary" : "secondary", "sm", "justify-self-start lg:justify-self-end")}
      >
        {t("compare.detail")} <ArrowRight size={14} aria-hidden />
      </Link>
    </li>
  );
}

function VsCard({
  a,
  b,
  rec,
  title,
  tb,
}: {
  a: string;
  b: string;
  rec: RespuestaCompleta;
  title: string;
  tb: (k: BlockId) => string;
}) {
  const t = useTranslations("result.vs");
  const ahead = blocksAhead(rec.detalle[a], rec.detalle[b]);
  return (
    <Card className="mt-8">
      <h2 className="mb-4 text-xl font-extrabold">{title}</h2>
      <p className="text-sm">
        <span className="font-bold text-ok">{t("winnerAhead")}</span>{" "}
        {ahead.a.length ? ahead.a.map((k) => `${k} · ${tb(k)}`).join(", ") : t("nothing")}
      </p>
      <p className="mt-2 text-sm">
        <span className="font-bold text-warn">{t("altAhead")}</span>{" "}
        {ahead.b.length ? ahead.b.map((k) => `${k} · ${tb(k)}`).join(", ") : t("nothing")}
      </p>
    </Card>
  );
}
