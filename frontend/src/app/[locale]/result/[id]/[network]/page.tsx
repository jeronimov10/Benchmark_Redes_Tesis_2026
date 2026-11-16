// Pagina de detalle de una red dentro de una recomendacion.
"use client";

import { Suspense, use } from "react";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, CalendarDays, ChevronDown, Loader2 } from "lucide-react";
import { ButtonLink, Card, Container, Semaphore, cx } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { BLOCKS } from "@/engine/metrics";
import { recipientRisk } from "@/lib/recipient";
import type { Light, NetworkId } from "@/engine/types";
import { useEntrada, useRecomendacion } from "@/modelo/cliente";
import { bandaDe, blocksAhead, entradaModelo, luzMetrica, luzPuntaje, luzRed, UNIDAD, valueOf } from "@/modelo/entrada";
import { esCompleta, type MetricaDetalle } from "@/modelo/tipos";
import { AvisoDatos, EtiquetaProcedencia, SinRecomendacion } from "@/components/result/EstadoDatos";
import { applyQuery } from "@/lib/attrs";
import { networkLabel as label, useFmt } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

function Detail({ id, network }: { id: string; network: string }) {
  const t = useTranslations("detail");
  const tr = useTranslations("result");
  const tn = useTranslations("networks");
  const td = useTranslations("data");
  const tg = useTranslations("gates");
  const fmt = useFmt();
  const params = useSearchParams();
  const { ready } = useRequireUser();
  const store = useStore();
  const entry = store.history.find((h) => h.id === id);
  const tx = entry ? applyQuery(entry.tx, params) : null;
  const { data: rec, error, stale } = useRecomendacion(useEntrada(entry && tx ? entradaModelo(tx, entry.answers.country) : null));

  if (!ready) return <Container className="py-12" />;
  if (entry && !rec && !error) {
    return (
      <Container className="py-20">
        <p className="flex items-center justify-center gap-3 text-lg font-bold" role="status">
          <Loader2 size={22} className="animate-spin" aria-hidden /> {tr("model.loading")}
        </p>
      </Container>
    );
  }
  const d = rec?.detalle[network];
  if (!entry || !tx || !rec || !d) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{error ? `${tr("model.error")} ${error}` : tr("notFound")}</p>
        <ButtonLink href="/home">{tr("backHome")}</ButtonLink>
      </Container>
    );
  }

  if (!esCompleta(rec)) return <SinRecomendacion rec={rec} />;

  const r = rec.resultado;
  const band = bandaDe(r, network);
  const score = band !== null ? r.bandas[band - 1].puntajes[network] : null;
  const winners = r.bandas[0]?.redes ?? [];
  const isWinner = winners.includes(network);
  const reference = !isWinner && winners.length === 1 && band !== null ? winners[0] : null;
  const ahead = reference ? blocksAhead(d, rec.detalle[reference]) : null;
  const fee = valueOf(d, "A1");
  const inclusion = valueOf(d, "B1");
  const finality = valueOf(d, "B2b") ?? valueOf(d, "B2");
  const accepted = tx.recipient.accepted;
  const acceptance = accepted === "unknown" ? null : accepted.includes(network as NetworkId);
  const risk = recipientRisk(tx);
  const riskLight: Light = risk <= 25 ? "green" : risk >= 60 ? "red" : "yellow";
  const back = `/result/${id}`;

  return (
    <Container className="max-w-4xl py-12">
      <Link
        href={back}
        className="mb-6 inline-flex items-center gap-2 rounded-full border-[1.5px] border-line px-4 py-2 text-sm font-bold transition-colors hover:bg-surface"
      >
        <ArrowLeft size={16} aria-hidden /> {t("back")}
      </Link>

      <AvisoDatos rec={rec} obsoleto={stale} />

      <section className="animate-fade-up relative overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10">
        <span aria-hidden className="absolute -right-12 -top-12 h-48 w-48 rounded-full bg-white/30" />
        <div className="relative">
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-5xl font-extrabold tracking-tight">{label(network)}</h1>
            <Semaphore light={luzRed(r, network)} size="lg" ring />
            {isWinner && (
              <span className="rounded-full bg-ink px-3.5 py-1 text-xs font-extrabold uppercase tracking-wider text-brand">
                {winners.length > 1 ? tr("bands.tie") : tr("compare.best")}
              </span>
            )}
            {band !== null && (
              <span className="rounded-full bg-paper px-3.5 py-1 text-xs font-extrabold uppercase tracking-wider">
                {t("band", { n: band })}
              </span>
            )}
          </div>
          <p className="mt-3 max-w-2xl leading-relaxed">{tn(`${network}.desc`)}</p>
          <p className="mt-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em]">
            <CalendarDays size={14} aria-hidden /> {tr("model.measurement", { when: rec.medicion })}
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Tile
              label={tr("best.fee")}
              value={fee !== null ? fmt.usdt(fee) : "—"}
              sub={fee !== null ? `≈ ${fmt.copSmall(fee * rec.trm)}` : ""}
            />
            <Tile
              label={tr("best.time")}
              value={inclusion !== null ? fmt.seconds(inclusion) : "—"}
              sub={finality !== null ? tr("best.finality", { time: fmt.seconds(finality) }) : ""}
            />
            <Tile
              label={t("score")}
              value={score ? fmt.decimal(score.mediana, 3) : t("excluded")}
              sub={score ? t("scoreNote", { p5: fmt.decimal(score.p05, 3), p95: fmt.decimal(score.p95, 3) }) : ""}
            />
          </div>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{tg("title")}</h2>
        <p className="mb-5 mt-1 text-muted">{tg("sub")}</p>
        {d.compuertas_falladas.length === 0 ? (
          <Card className="flex items-center gap-3 p-5 sm:p-5">
            <Semaphore light="green" size="md" />
            <p className="font-bold">{tg("allPass")}</p>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {d.compuertas_falladas.map((g) => (
              <div key={g.compuerta} className="rounded-card border-[1.5px] border-line bg-paper p-5">
                <div className="flex items-start gap-3">
                  <Semaphore light="red" size="md" />
                  <div className="min-w-0">
                    <p className="font-extrabold">
                      <span className="mr-2 rounded-md bg-surface px-1.5 py-0.5 text-xs">{g.compuerta}</span>
                      {tg(`${g.compuerta}.name`)}
                    </p>
                    <p className="mt-0.5 text-sm text-muted">{tg(`${g.compuerta}.desc`)}</p>
                    <p className="mt-2 text-sm font-bold">
                      {tg("fail")} <span className="font-normal text-muted" lang="es">{g.motivo}</span>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("sem2.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("sem2.sub")}</p>
        <div className="space-y-3">
          {BLOCKS.map((b) => {
            const metrics = d.metricas.filter((m) => m.bloque === b);
            const blockScore = d.bloques[b];
            const light = luzPuntaje(blockScore);
            const n = metrics.filter((m) => m.puntaje !== null).length;
            return (
              <details
                key={b}
                className="group overflow-hidden rounded-card border-[1.5px] border-line bg-paper open:shadow-card"
                open={light !== "green"}
              >
                <summary className="flex cursor-pointer list-none items-center gap-4 p-5 sm:p-6">
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand text-lg font-extrabold">
                    {b}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-lg font-extrabold">{t(`block.${b}`)}</span>
                    <span className="block text-sm text-muted">{t(`blockDesc.${b}`)}</span>
                    <span className="mt-1 block text-xs font-semibold text-muted">
                      {blockScore !== null ? `${fmt.decimal(blockScore, 2)} · ` : ""}
                      {t("blockMeta", { n, excluded: metrics.length - n })}
                    </span>
                  </span>
                  {light ? <Semaphore light={light} size="lg" /> : null}
                  <ChevronDown size={20} className="shrink-0 text-grey transition-transform group-open:rotate-180" aria-hidden />
                </summary>
                <ul className="divide-y divide-line/70 border-t border-line/70 px-5 sm:px-6">
                  {metrics.map((m) => (
                    <MetricRow key={m.id} m={m} />
                  ))}
                </ul>
              </details>
            );
          })}
        </div>
        <p className="mt-4 text-sm text-muted">{t("sem2.rule")}</p>
        <p className="mt-1 text-sm text-muted">
          {td("centralScore", { score: fmt.decimal(d.puntaje_central, 3) })}
        </p>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("recipient.title")}</h2>
        <Card className="mt-4 p-6 sm:p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="flex items-center gap-3">
              <Semaphore light={acceptance === true ? "green" : acceptance === false ? "red" : "yellow"} size="lg" />
              <p className="font-bold">
                {acceptance === true
                  ? t("recipient.accepted")
                  : acceptance === false
                    ? t("recipient.notAccepted")
                    : t("recipient.unknown")}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Semaphore light={riskLight} size="lg" />
              <p className="font-bold">
                {t("recipient.risk")}: {fmt.decimal(risk, 0)}/100
              </p>
            </div>
          </div>
          <p className="mt-4 text-xs text-muted">{t("recipient.riskNote")}</p>
        </Card>
      </section>

      {r.inadmisibles[network] && (
        <Card tone="surface" className="mt-10">
          <h2 className="mb-3 flex items-center gap-3 text-xl font-extrabold">
            <Semaphore light="red" /> {t("redTitle")}
          </h2>
          <ul className="space-y-2 text-sm">
            {r.inadmisibles[network].map(([gate, motivo]) => (
              <li key={gate}>
                {tr("excluded.gate", { gate, name: tg(`${gate}.name`) })} <span lang="es">{motivo}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {reference && ahead && (
        <Card className="mt-10">
          <h2 className="mb-4 text-xl font-extrabold">{t("vsBest", { network: label(reference) })}</h2>
          <p className="text-sm">
            <span className="font-bold text-ok">{tr("vs.winnerAhead")}</span>{" "}
            {ahead.a.length ? ahead.a.map((b) => `${b} · ${t(`block.${b}`)}`).join(", ") : tr("vs.nothing")}
          </p>
          <p className="mt-2 text-sm">
            <span className="font-bold text-warn">{tr("vs.altAhead")}</span>{" "}
            {ahead.b.length ? ahead.b.map((b) => `${b} · ${t(`block.${b}`)}`).join(", ") : tr("vs.nothing")}
          </p>
        </Card>
      )}

      <div className="mt-10 flex flex-wrap gap-3">
        <ButtonLink href={back} variant="secondary" size="lg">
          {t("back")}
        </ButtonLink>
        <ButtonLink href="/transaction/new" size="lg">
          {tr("actions.new")}
        </ButtonLink>
      </div>
    </Container>
  );
}

function Tile({ label, value, sub }: { label: string; value: string; sub: ReactNode }) {
  return (
    <div className="rounded-2xl bg-paper p-4">
      <p className="text-xs font-bold text-muted">{label}</p>
      <p className="mt-2 text-2xl font-extrabold tracking-tight">{value}</p>
      <p className="mt-0.5 text-xs text-muted">{sub}</p>
    </div>
  );
}

function MetricRow({ m }: { m: MetricaDetalle }) {
  const t = useTranslations("detail");
  const tm = useTranslations("metrics");
  const td = useTranslations("data");
  const fmt = useFmt();
  const excluded = m.valor === null;
  const light = luzMetrica(m.puntaje);
  const unit = UNIDAD[m.id];
  return (
    <li className="grid items-center gap-x-6 gap-y-2 py-4 sm:grid-cols-[1fr_auto_auto]">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 font-bold">
          <span className="rounded-md bg-surface px-1.5 py-0.5 text-xs">{m.id}</span>
          {tm(`${m.id}.name`)}
          <EtiquetaProcedencia p={m.procedencia} />
          {m.cota_inferior && (
            <span className="rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
              {td("lowerBoundTag")}
            </span>
          )}
        </p>
        <p className="mt-0.5 text-sm text-muted">{tm(`${m.id}.desc`)}</p>
        {m.nota && (
          <p className="mt-1 text-xs text-muted" lang="es">
            {m.nota}
          </p>
        )}
        {excluded && <p className="mt-1 text-xs font-bold uppercase tracking-wide text-muted">{t("excludedMetric")}</p>}
      </div>
      <div className="sm:text-right">
        {excluded ? (
          <p className="text-xl font-extrabold text-grey">—</p>
        ) : (
          <>
            <p className={cx("text-xl font-extrabold tabular-nums", light === "red" && "text-bad")}>
              {fmt.metricValue(m.valor as number, unit)}
            </p>
            <p className="text-xs text-muted">
              {t("col.target")} {fmt.metricValue(m.objetivo, unit)} · {t("col.limit")} {fmt.metricValue(m.inaceptable, unit)}
            </p>
            {m.puntaje !== null && (
              <p className="text-xs text-muted">
                {t("col.score")} {fmt.decimal(m.puntaje, 2)}
              </p>
            )}
          </>
        )}
      </div>
      <div className="justify-self-start sm:justify-self-end">
        {light ? <Semaphore light={light} size="md" /> : <span className="inline-block h-5 w-5 rounded-full border-2 border-dashed border-grey" />}
      </div>
    </li>
  );
}

export default function NetworkDetailPage({ params }: { params: Promise<{ id: string; network: string }> }) {
  const { id, network } = use(params);
  return (
    <Suspense>
      <Detail id={id} network={network} />
    </Suspense>
  );
}
