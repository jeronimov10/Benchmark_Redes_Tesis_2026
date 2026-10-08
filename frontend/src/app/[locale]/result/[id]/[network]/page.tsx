"use client";

import { Suspense, use, useMemo } from "react";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { ButtonLink, Card, Container, DemoBadge, Semaphore, cx } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { explain, redReasons } from "@/engine/explain";
import { DIMENSIONS } from "@/engine/risk-standard";
import { recommend } from "@/engine/scoring";
import { NETWORK_IDS, type MetricResult, type NetworkId } from "@/engine/types";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
import { parsePriorities } from "@/lib/priorityQuery";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

function Detail({ id, network }: { id: string; network: string }) {
  const t = useTranslations("detail");
  const tr = useTranslations("result");
  const tm = useTranslations("metrics");
  const tp = useTranslations("priorities");
  const tn = useTranslations("networks");
  const fmt = useFmt();
  const params = useSearchParams();
  const { ready } = useRequireUser();
  const store = useStore();
  const entry = store.history.find((h) => h.id === id);
  const pRaw = params.get("p");
  const fromQuery = useMemo(() => parsePriorities(pRaw), [pRaw]);

  const rec = useMemo(
    () => (entry ? recommend({ ...entry.tx, priorities: fromQuery ?? entry.tx.priorities }, entry.answers) : null),
    [entry, fromQuery],
  );

  if (!ready) return <Container className="py-12" />;
  const netId = NETWORK_IDS.find((n) => n === network) as NetworkId | undefined;
  const ev = rec?.evaluations.find((e) => e.network.id === netId);
  if (!entry || !rec || !ev || !netId) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{tr("notFound")}</p>
        <ButtonLink href="/home">{tr("backHome")}</ButtonLink>
      </Container>
    );
  }

  const exp = explain(rec);
  const cmp = exp?.comparisons.find((c) => c.network.network.id === netId);
  const isBest = rec.best?.network.id === netId;
  const back = `/result/${id}`;

  return (
    <Container className="max-w-4xl py-12">
      <Link
        href={back}
        className="mb-6 inline-flex items-center gap-2 rounded-full border-[1.5px] border-line px-4 py-2 text-sm font-bold transition-colors hover:bg-surface"
      >
        <ArrowLeft size={16} aria-hidden /> {t("back")}
      </Link>

      <section className="animate-fade-up relative overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10">
        <span aria-hidden className="absolute -right-12 -top-12 h-48 w-48 rounded-full bg-white/30" />
        <div className="relative">
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-5xl font-extrabold tracking-tight">{NETWORK_LABEL[netId]}</h1>
            <Semaphore light={ev.light} size="lg" ring />
            {isBest && (
              <span className="rounded-full bg-ink px-3.5 py-1 text-xs font-extrabold uppercase tracking-wider text-brand">
                {tr("compare.best")}
              </span>
            )}
          </div>
          <p className="mt-3 max-w-2xl leading-relaxed">{tn(`${netId}.desc`)}</p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Tile label={tr("best.fee")} value={fmt.usdt(ev.feeUsd)} sub={`≈ ${fmt.cop(ev.feeCop)}`} />
            <Tile
              label={tr("best.time")}
              value={fmt.seconds(ev.timeSec)}
              sub={tr("best.finality", { time: fmt.seconds(ev.network.irreversibilitySec) })}
            />
            <Tile
              label={t("score")}
              value={ev.light === "red" ? t("excluded") : fmt.percent(ev.total)}
              sub={
                <span className="inline-flex items-center gap-1.5">
                  <DemoBadge className="!bg-ink !text-white" /> {t("scoreNote")}
                </span>
              }
            />
          </div>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("sem1.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("sem1.sub")}</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {DIMENSIONS.map((d) => (
            <div key={d} className="flex flex-col items-center gap-3 rounded-card bg-surface px-3 py-6 text-center">
              <Semaphore light={ev.dimensions.find((x) => x.id === d)!.light} size="lg" />
              <span className="text-sm font-bold">{tr(`dimension.${d}`)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("sem2.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("sem2.sub")}</p>
        <div className="space-y-3">
          {ev.blocks.map((b) => (
            <details
              key={b.id}
              className="group overflow-hidden rounded-card border-[1.5px] border-line bg-paper open:shadow-card"
              open={b.light !== "green"}
            >
              <summary className="flex cursor-pointer list-none items-center gap-4 p-5 sm:p-6">
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand text-lg font-extrabold">
                  {b.id}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-lg font-extrabold">{t(`block.${b.id}`)}</span>
                  <span className="block text-sm text-muted">{t(`blockDesc.${b.id}`)}</span>
                </span>
                <Semaphore light={b.light} size="lg" />
                <ChevronDown size={20} className="shrink-0 text-grey transition-transform group-open:rotate-180" aria-hidden />
              </summary>
              <ul className="divide-y divide-line/70 border-t border-line/70 px-5 sm:px-6">
                {b.metrics.map((m) => (
                  <MetricRow key={m.def.id} m={m} />
                ))}
              </ul>
            </details>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">{t("sem2.rule")}</p>
      </section>

      {ev.light === "red" && (
        <Card tone="surface" className="mt-10">
          <h2 className="mb-3 flex items-center gap-3 text-xl font-extrabold">
            <Semaphore light="red" /> {t("redTitle")}
          </h2>
          <ul className="space-y-2 text-sm">
            {redReasons(ev).map((m) => (
              <li key={m.def.id}>
                <strong>{tm(`${m.def.id}.name`)}</strong>: {fmt.metricValue(m.value, m.def.unit)}
                {m.noteKey && <span className="text-muted"> — {tr(`notes.${m.noteKey}`)}</span>}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {cmp && rec.best && (
        <Card className="mt-10">
          <h2 className="mb-4 text-xl font-extrabold">{t("vsBest", { network: NETWORK_LABEL[rec.best.network.id] })}</h2>
          <p className="text-sm">
            <span className="font-bold text-ok">{tr("vs.winnerAhead")}</span>{" "}
            {cmp.winnerAhead.length ? cmp.winnerAhead.map((a) => tp(`axis.${a}`)).join(", ") : tr("vs.nothing")}
          </p>
          <p className="mt-2 text-sm">
            <span className="font-bold text-warn">{tr("vs.altAhead")}</span>{" "}
            {cmp.altAhead.length ? cmp.altAhead.map((a) => tp(`axis.${a}`)).join(", ") : tr("vs.nothing")}
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

function MetricRow({ m }: { m: MetricResult }) {
  const t = useTranslations("detail");
  const tm = useTranslations("metrics");
  const tr = useTranslations("result");
  const fmt = useFmt();
  return (
    <li className="grid items-center gap-x-6 gap-y-2 py-4 sm:grid-cols-[1fr_auto_auto]">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 font-bold">
          <span className="rounded-md bg-surface px-1.5 py-0.5 text-xs">{m.def.id}</span>
          {tm(`${m.def.id}.name`)}
          {m.def.extension && (
            <span className="rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
              {t("extension")}
            </span>
          )}
          {m.critical && (
            <span className="rounded-full bg-ink px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-brand">
              {t("critical")}
            </span>
          )}
        </p>
        <p className="mt-0.5 text-sm text-muted">{tm(`${m.def.id}.desc`)}</p>
        {m.noteKey && <p className="mt-1 text-sm font-semibold">{tr(`notes.${m.noteKey}`)}</p>}
      </div>
      <div className="sm:text-right">
        <p className={cx("text-xl font-extrabold tabular-nums", m.light === "red" && "text-bad")}>
          {fmt.metricValue(m.value, m.def.unit)}
        </p>
        <p className="text-xs text-muted">
          {t("col.target")} {fmt.metricValue(m.t, m.def.unit)} · {t("col.limit")} {fmt.metricValue(m.w, m.def.unit)}
        </p>
      </div>
      <div className="justify-self-start sm:justify-self-end">
        <Semaphore light={m.light} size="md" />
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
