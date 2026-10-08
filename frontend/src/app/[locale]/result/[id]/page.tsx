"use client";

import { use, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, Clock, Coins, RotateCcw, Scale, ShieldAlert } from "lucide-react";
import {
  Button,
  ButtonLink,
  buttonClass,
  Card,
  Container,
  DemoBadge,
  Semaphore,
  cx,
} from "@/components/ui";
import { PrioritySliders } from "@/components/result/PrioritySliders";
import { Link } from "@/i18n/navigation";
import { explain, redReasons } from "@/engine/explain";
import { recommend } from "@/engine/scoring";
import { DIMENSIONS } from "@/engine/risk-standard";
import type { NetworkEvaluation, Recommendation, Weights } from "@/engine/types";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
import { priorityQuery } from "@/lib/priorityQuery";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

export default function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useTranslations("result");
  const ts = useTranslations("scenarios");
  const tp = useTranslations("priorities");
  const tm = useTranslations("metrics");
  const fmt = useFmt();
  const { ready } = useRequireUser();
  const store = useStore();
  const entry = store.history.find((h) => h.id === id);

  const [adjusted, setAdjusted] = useState<Weights | null>(null);
  const priorities = adjusted ?? entry?.tx.priorities;

  const original = useMemo(() => (entry ? recommend(entry.tx, entry.answers) : null), [entry]);
  const rec: Recommendation | null = useMemo(
    () => (entry && priorities ? recommend({ ...entry.tx, priorities }, entry.answers) : null),
    [entry, priorities],
  );
  const exp = useMemo(() => (rec ? explain(rec) : null), [rec]);

  if (!ready) return <Container className="py-12" />;
  if (!entry || !rec || !original || !priorities) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{t("notFound")}</p>
        <ButtonLink href="/home">{t("backHome")}</ButtonLink>
      </Container>
    );
  }

  const best = rec.best;
  const changed = adjusted && best?.network.id !== original.best?.network.id;
  const q = priorityQuery(priorities);

  return (
    <Container className="py-12">
      <p className="mb-4 text-sm font-bold uppercase tracking-[0.14em] text-muted">
        {ts(`${rec.scenario}.name`)} · {fmt.cop(entry.tx.amountCop)} ≈ {fmt.usdt(rec.amountUsd)}
      </p>

      {best ? (
        <section className="animate-fade-up grid gap-5 lg:grid-cols-5">
          <div className="relative overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10 lg:col-span-3">
            <span aria-hidden className="absolute -right-12 -top-12 h-52 w-52 rounded-full bg-white/30" />
            <div className="relative">
              <p className="text-xs font-bold uppercase tracking-[0.14em]">{t("best.kicker")}</p>
              <h1 className="mt-3 text-5xl font-extrabold tracking-tight sm:text-6xl">
                {NETWORK_LABEL[best.network.id]}
              </h1>
              <p className="mt-4 max-w-lg leading-relaxed">
                {t("best.summary", { network: NETWORK_LABEL[best.network.id], scenario: ts(`${rec.scenario}.name`) })}
              </p>

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <Stat icon={<Coins size={15} aria-hidden />} label={t("best.fee")} value={fmt.usdt(best.feeUsd)} sub={`≈ ${fmt.cop(best.feeCop)}`} />
                <Stat
                  icon={<Clock size={15} aria-hidden />}
                  label={t("best.time")}
                  value={fmt.seconds(best.timeSec)}
                  sub={t("best.finality", { time: fmt.seconds(best.network.irreversibilitySec) })}
                />
                <div className="rounded-2xl bg-paper p-4">
                  <p className="flex items-center gap-1.5 text-xs font-bold text-muted">
                    <ShieldAlert size={15} aria-hidden /> {t("best.risk")}
                  </p>
                  <div className="mt-3">
                    <Semaphore light={best.light} size="lg" ring />
                  </div>
                </div>
              </div>
              <p className="mt-5 flex items-center gap-2 text-xs">
                <DemoBadge className="!bg-ink !text-white" /> {t("best.disclaimer")}
              </p>
            </div>
          </div>

          <Card className="lg:col-span-2">
            <h2 className="mb-5 text-xl font-extrabold">{t("why.title")}</h2>
            <ul className="space-y-5">
              {exp?.determinants.slice(0, 3).map((d) => (
                <li key={d.axis}>
                  <div className="mb-1.5 flex justify-between font-bold">
                    <span>{tp(`axis.${d.axis}`)}</span>
                    <span className="tabular-nums">{fmt.percent(d.share)}</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-surface">
                    <div className="h-2.5 rounded-full bg-brand" style={{ width: `${d.share * 100}%` }} />
                  </div>
                  <p className="mt-1.5 text-sm leading-snug text-muted">{t(`why.axis.${d.axis}`)}</p>
                </li>
              ))}
            </ul>
            <p className="mt-6 border-t border-line pt-4 text-xs text-muted">
              {t("why.weights", {
                cost: fmt.percent(rec.weights.cost),
                speed: fmt.percent(rec.weights.speed),
                security: fmt.percent(rec.weights.security),
              })}
            </p>
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

      {changed && best && original.best && (
        <p role="status" className="mt-5 rounded-2xl bg-brand-soft px-5 py-4 text-sm font-bold">
          {t("changed", { from: NETWORK_LABEL[original.best.network.id], to: NETWORK_LABEL[best.network.id] })}
        </p>
      )}

      <Card className="mt-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl font-extrabold">
            <Scale size={20} aria-hidden /> {t("adjust.title")}
          </h2>
          {adjusted && (
            <Button variant="secondary" size="sm" onClick={() => setAdjusted(null)}>
              <RotateCcw size={14} aria-hidden /> {t("adjust.reset")}
            </Button>
          )}
        </div>
        <p className="mb-5 text-sm text-muted">{t("adjust.sub")}</p>
        <PrioritySliders value={priorities} onChange={setAdjusted} />
      </Card>

      <section className="mt-10">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("compare.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("compare.sub")}</p>
        <ul className="space-y-3">
          {[...rec.ranking, ...rec.excluded].map((e, i) => (
            <NetworkRow key={e.network.id} e={e} rank={e.light === "red" ? null : i + 1} q={q} id={id} isBest={e === best} />
          ))}
        </ul>
      </section>

      {rec.excluded.length > 0 && (
        <Card tone="surface" className="mt-8">
          <h2 className="flex items-center gap-3 text-xl font-extrabold">
            <Semaphore light="red" /> {t("excluded.title")}
          </h2>
          <p className="mb-5 mt-1 text-sm text-muted">{t("excluded.sub")}</p>
          <div className="grid gap-4 md:grid-cols-2">
            {rec.excluded.map((e) => (
              <div key={e.network.id} className="rounded-2xl bg-paper p-5">
                <p className="mb-2 font-extrabold">{NETWORK_LABEL[e.network.id]}</p>
                <ul className="space-y-1.5 text-sm text-muted">
                  {redReasons(e).slice(0, 3).map((m) => (
                    <li key={m.def.id}>
                      <span className="font-bold text-ink">{tm(`${m.def.id}.name`)}</span>:{" "}
                      {fmt.metricValue(m.value, m.def.unit)} ({t("excluded.limit", { w: fmt.metricValue(m.w, m.def.unit) })})
                      {m.noteKey && <span className="block">{t(`notes.${m.noteKey}`)}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}

      {exp && exp.comparisons.length > 0 && best && (
        <section className="mt-10">
          <h2 className="mb-5 text-2xl font-extrabold tracking-tight">
            {t("vs.title", { network: NETWORK_LABEL[best.network.id] })}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {exp.comparisons.map((c) => (
              <Card key={c.network.network.id} className="p-6 sm:p-6">
                <p className="mb-3 text-lg font-extrabold">{NETWORK_LABEL[c.network.network.id]}</p>
                <p className="text-sm">
                  <span className="font-bold text-ok">{t("vs.winnerAhead")}</span>{" "}
                  {c.winnerAhead.length ? c.winnerAhead.map((a) => tp(`axis.${a}`)).join(", ") : t("vs.nothing")}
                </p>
                <p className="mt-1.5 text-sm">
                  <span className="font-bold text-warn">{t("vs.altAhead")}</span>{" "}
                  {c.altAhead.length ? c.altAhead.map((a) => tp(`axis.${a}`)).join(", ") : t("vs.nothing")}
                </p>
              </Card>
            ))}
          </div>
        </section>
      )}

      <p className="mt-10 rounded-2xl bg-surface p-5 text-sm leading-relaxed text-muted">{t("disclaimer")}</p>

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

function NetworkRow({
  e,
  rank,
  q,
  id,
  isBest,
}: {
  e: NetworkEvaluation;
  rank: number | null;
  q: string;
  id: string;
  isBest: boolean;
}) {
  const t = useTranslations("result");
  const fmt = useFmt();
  const excluded = e.light === "red";

  return (
    <li
      className={cx(
        "grid items-center gap-x-5 gap-y-4 rounded-card border-[1.5px] bg-paper p-5 transition-shadow hover:shadow-card lg:grid-cols-[2.2fr_auto_3fr_1.4fr_auto]",
        isBest ? "border-ink" : "border-line",
        excluded && "bg-surface",
      )}
    >
      <div className="flex items-center gap-4">
        <span
          className={cx(
            "grid h-11 w-11 shrink-0 place-items-center rounded-full text-sm font-extrabold",
            rank === 1 ? "bg-brand" : excluded ? "bg-line" : "bg-surface",
          )}
        >
          {rank ?? "—"}
        </span>
        <div>
          <p className="text-lg font-extrabold leading-tight">{NETWORK_LABEL[e.network.id]}</p>
          {isBest && (
            <span className="mt-1 inline-block rounded-full bg-ink px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-brand">
              {t("compare.best")}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2" title={t("compare.global")}>
        <Semaphore light={e.light} size="lg" />
        <span className="text-xs font-bold uppercase tracking-wide text-muted lg:sr-only">{t("compare.global")}</span>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {DIMENSIONS.map((d) => (
          <div key={d} className="flex flex-col items-center gap-1.5 text-center">
            <Semaphore light={e.dimensions.find((x) => x.id === d)!.light} size="md" />
            <span className="text-[10px] font-semibold leading-tight text-muted">{t(`dimension.${d}`)}</span>
          </div>
        ))}
      </div>

      <div className="text-sm lg:text-right">
        <p className="font-bold tabular-nums">{fmt.usdt(e.feeUsd)}</p>
        <p className="tabular-nums text-muted">{fmt.seconds(e.timeSec)}</p>
      </div>

      <Link
        href={`/result/${id}/${e.network.id}?${q}`}
        className={buttonClass(isBest ? "primary" : "secondary", "sm", "justify-self-start lg:justify-self-end")}
      >
        {t("compare.detail")} <ArrowRight size={14} aria-hidden />
      </Link>
    </li>
  );
}
