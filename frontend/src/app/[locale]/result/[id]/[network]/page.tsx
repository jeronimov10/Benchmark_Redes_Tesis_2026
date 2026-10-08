"use client";

import { Suspense, use, useMemo } from "react";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { ButtonLink, Card, Container, Semaphore, cx } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { recommend } from "@/engine/recommend";
import { NETWORK_IDS, type BlockId, type GateOutcome, type Light, type MetricResult, type NetworkId } from "@/engine/types";
import { applyQuery } from "@/lib/attrs";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
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
  const qs = params.toString();

  const rec = useMemo(
    () => (entry ? recommend(applyQuery(entry.tx, new URLSearchParams(qs)), entry.answers) : null),
    [entry, qs],
  );

  if (!ready) return <Container className="py-12" />;
  const netId = NETWORK_IDS.find((n) => n === network) as NetworkId | undefined;
  const ev = rec?.evaluations.find((e) => e.data.id === netId);
  if (!entry || !rec || !ev || !netId) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{tr("notFound")}</p>
        <ButtonLink href="/home">{tr("backHome")}</ButtonLink>
      </Container>
    );
  }

  const isBest = rec.best?.data.id === netId;
  const ahead = { mine: [] as BlockId[], best: [] as BlockId[] };
  if (rec.best && !isBest) {
    for (const b of ev.blocks) {
      const other = rec.best.blocks.find((x) => x.id === b.id);
      if (b.score === null || !other || other.score === null) continue;
      if (b.score - other.score > 0.02) ahead.mine.push(b.id);
      else if (other.score - b.score > 0.02) ahead.best.push(b.id);
    }
  }
  const back = `/result/${id}`;
  const gateName = (g: GateOutcome) => tg(`${g.id}.name`);

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
            {ev.band && (
              <span className="rounded-full bg-paper px-3.5 py-1 text-xs font-extrabold uppercase tracking-wider">
                {t("band", { n: ev.band })}
              </span>
            )}
          </div>
          <p className="mt-3 max-w-2xl leading-relaxed">{tn(`${netId}.desc`)}</p>
          <p className="mt-2 text-xs font-bold uppercase tracking-[0.12em]">{td(`source.${ev.data.source}`)}</p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Tile
              label={tr("best.fee")}
              value={ev.feeUsd !== null ? fmt.usdt(ev.feeUsd) : "—"}
              sub={ev.feeUsd !== null ? `≈ ${fmt.copSmall(ev.feeUsd * rec.trm)}` : ""}
            />
            <Tile
              label={tr("best.time")}
              value={ev.inclusionSec !== null ? fmt.seconds(ev.inclusionSec) : "—"}
              sub={ev.finalitySec !== null ? tr("best.finality", { time: fmt.seconds(ev.finalitySec) }) : ""}
            />
            <Tile
              label={t("score")}
              value={ev.score !== null && ev.admissible ? fmt.decimal(ev.score, 3) : t("excluded")}
              sub={ev.p5 !== null && ev.p95 !== null ? t("scoreNote", { p5: fmt.decimal(ev.p5, 2), p95: fmt.decimal(ev.p95, 2) }) : ""}
            />
          </div>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{tg("title")}</h2>
        <p className="mb-5 mt-1 text-muted">{tg("sub")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {ev.gates.map((g) => (
            <GateCard key={g.id} g={g} name={gateName(g)} />
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
                  <span className="mt-1 block text-xs font-semibold text-muted">
                    {b.score !== null ? `${fmt.decimal(b.score, 2)} · ` : ""}
                    {t("blockMeta", { n: b.n, excluded: b.excluded })}
                  </span>
                </span>
                {b.light ? <Semaphore light={b.light} size="lg" /> : null}
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

      <section className="mt-12">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("recipient.title")}</h2>
        <Card className="mt-4 p-6 sm:p-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="flex items-center gap-3">
              <Semaphore
                light={ev.recipient.accepted === true ? "green" : ev.recipient.accepted === false ? "red" : "yellow"}
                size="lg"
              />
              <p className="font-bold">
                {ev.recipient.accepted === true
                  ? t("recipient.accepted")
                  : ev.recipient.accepted === false
                    ? t("recipient.notAccepted")
                    : t("recipient.unknown")}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Semaphore light={ev.recipient.riskLight} size="lg" />
              <div>
                <p className="font-bold">
                  {t("recipient.risk")}: {fmt.decimal(ev.recipient.risk, 0)}/100
                </p>
              </div>
            </div>
          </div>
          <p className="mt-4 text-xs text-muted">{t("recipient.riskNote")}</p>
        </Card>
      </section>

      {!ev.admissible && (
        <Card tone="surface" className="mt-10">
          <h2 className="mb-3 flex items-center gap-3 text-xl font-extrabold">
            <Semaphore light="red" /> {t("redTitle")}
          </h2>
          <ul className="space-y-2 text-sm">
            {ev.excludedBy.map((by) => (
              <li key={by}>
                {by === "recipient"
                  ? tr("excluded.recipient")
                  : tr("excluded.gate", { gate: by, name: tg(`${by}.name`) })}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {rec.best && !isBest && ev.admissible && (
        <Card className="mt-10">
          <h2 className="mb-4 text-xl font-extrabold">{t("vsBest", { network: NETWORK_LABEL[rec.best.data.id] })}</h2>
          <p className="text-sm">
            <span className="font-bold text-ok">{tr("vs.winnerAhead")}</span>{" "}
            {ahead.mine.length ? ahead.mine.map((b) => `${b} · ${t(`block.${b}`)}`).join(", ") : tr("vs.nothing")}
          </p>
          <p className="mt-2 text-sm">
            <span className="font-bold text-warn">{tr("vs.altAhead")}</span>{" "}
            {ahead.best.length ? ahead.best.map((b) => `${b} · ${t(`block.${b}`)}`).join(", ") : tr("vs.nothing")}
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

function GateCard({ g, name }: { g: GateOutcome; name: string }) {
  const tg = useTranslations("gates");
  const td = useTranslations("data.notes");
  const fmt = useFmt();
  const light: Light = !g.applies || g.result === "na" ? "yellow" : g.result === "pass" ? "green" : "red";
  const label = !g.applies ? tg("notApplicable") : tg(g.result);
  return (
    <div className="rounded-card border-[1.5px] border-line bg-paper p-5">
      <div className="flex items-start gap-3">
        {g.applies ? (
          <Semaphore light={light} size="md" />
        ) : (
          <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full border-2 border-dashed border-grey" />
        )}
        <div className="min-w-0">
          <p className="font-extrabold">
            <span className="mr-2 rounded-md bg-surface px-1.5 py-0.5 text-xs">{g.id}</span>
            {name}
          </p>
          <p className="mt-0.5 text-sm text-muted">{tg(`${g.id}.desc`)}</p>
          <p className="mt-2 text-sm font-bold">
            {label}
            {g.applies && g.measured !== null && g.measured !== undefined && (
              <span className="ml-2 font-normal text-muted tabular-nums">
                {g.id === "G3" ? `${fmt.decimal(g.measured, 2)} %` : g.id === "G4" ? `${fmt.decimal(g.measured, 2)}×` : fmt.seconds(g.measured)}
              </span>
            )}
          </p>
          {g.note && <p className="mt-1 text-xs text-muted">{td(g.note)}</p>}
        </div>
      </div>
    </div>
  );
}

function MetricRow({ m }: { m: MetricResult }) {
  const t = useTranslations("detail");
  const tm = useTranslations("metrics");
  const td = useTranslations("data");
  const fmt = useFmt();
  const excluded = m.value === null;
  return (
    <li className="grid items-center gap-x-6 gap-y-2 py-4 sm:grid-cols-[1fr_auto_auto]">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 font-bold">
          <span className="rounded-md bg-surface px-1.5 py-0.5 text-xs">{m.def.id}</span>
          {tm(`${m.def.id}.name`)}
          {m.status !== "computed" && (
            <span className="rounded-full border border-line px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
              {td(`status.${m.status}`)}
            </span>
          )}
        </p>
        <p className="mt-0.5 text-sm text-muted">{tm(`${m.def.id}.desc`)}</p>
        {m.note && <p className="mt-1 text-sm font-semibold">{td(`notes.${m.note}`)}</p>}
        {excluded && <p className="mt-1 text-xs font-bold uppercase tracking-wide text-muted">{t("excludedMetric")}</p>}
      </div>
      <div className="sm:text-right">
        {excluded ? (
          <p className="text-xl font-extrabold text-grey">—</p>
        ) : (
          <>
            <p className={cx("text-xl font-extrabold tabular-nums", m.light === "red" && "text-bad")}>
              {fmt.metricValue(m.value as number, m.def.unit)}
            </p>
            <p className="text-xs text-muted">
              {t("col.target")} {fmt.metricValue(m.def.t, m.def.unit)} · {t("col.limit")} {fmt.metricValue(m.def.w, m.def.unit)}
            </p>
          </>
        )}
      </div>
      <div className="justify-self-start sm:justify-self-end">
        {m.light ? <Semaphore light={m.light} size="md" /> : <span className="inline-block h-5 w-5 rounded-full border-2 border-dashed border-grey" />}
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
