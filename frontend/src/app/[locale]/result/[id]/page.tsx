"use client";

import { use, useDeferredValue, useMemo, useState } from "react";
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
  Field,
  inputClass,
  Semaphore,
  cx,
} from "@/components/ui";
import { PaymentAttributes } from "@/components/result/PaymentAttributes";
import { Link } from "@/i18n/navigation";
import { explain } from "@/engine/explain";
import { BLOCKS } from "@/engine/metrics";
import { recommend } from "@/engine/recommend";
import { SCENARIO_IDS, type Irreversibility, type NetworkEvaluation, type ScenarioId, type TxInput } from "@/engine/types";
import { txQuery } from "@/lib/attrs";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

export default function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useTranslations("result");
  const ts = useTranslations("scenarios");
  const tm = useTranslations("metrics");
  const tg = useTranslations("gates");
  const tb = useTranslations("detail.block");
  const tt = useTranslations("tx");
  const tdn = useTranslations("data.notes");
  const fmt = useFmt();
  const { ready } = useRequireUser();
  const store = useStore();
  const entry = store.history.find((h) => h.id === id);

  const [override, setOverride] = useState<{ amountCop?: number; waitSec?: number; irreversibility?: Irreversibility } | null>(null);
  const tx: TxInput | undefined = entry ? { ...entry.tx, ...override } : undefined;
  const deferredTx = useDeferredValue(tx);
  const stale = tx !== deferredTx;

  const original = useMemo(() => (entry ? recommend(entry.tx, entry.answers) : null), [entry]);
  const rec = useMemo(
    () => (entry && deferredTx ? recommend(deferredTx, entry.answers) : null),
    [entry, deferredTx],
  );
  const exp = useMemo(() => (rec ? explain(rec) : null), [rec]);

  if (!ready) return <Container className="py-12" />;
  if (!entry || !tx || !rec || !original) {
    return (
      <Container className="py-20 text-center">
        <p className="mb-6 text-lg text-muted">{t("notFound")}</p>
        <ButtonLink href="/home">{t("backHome")}</ButtonLink>
      </Container>
    );
  }

  const best = rec.best;
  const dominant = SCENARIO_IDS.reduce((a, b) => (rec.lambda[a] >= rec.lambda[b] ? a : b));
  const tieMates = best ? (rec.bands[0] ?? []).filter((e) => e !== best) : [];
  const changed = override && best?.data.id !== original.best?.data.id;
  const q = txQuery(tx);
  const runnerUp = rec.ranking[1];

  return (
    <Container className={cx("py-12 transition-opacity", stale && "opacity-70")}>
      <p className="mb-4 text-sm font-bold uppercase tracking-[0.14em] text-muted">
        {fmt.cop(tx.amountCop)} ≈ {fmt.usdt(rec.amountUsd)} · {ts(`${dominant}.name`)}
      </p>

      {best ? (
        <section className="animate-fade-up grid gap-5 lg:grid-cols-5">
          <div className="relative overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10 lg:col-span-3">
            <span aria-hidden className="absolute -right-12 -top-12 h-52 w-52 rounded-full bg-white/30" />
            <div className="relative">
              <p className="text-xs font-bold uppercase tracking-[0.14em]">{t("best.kicker")}</p>
              <h1 className="mt-3 text-5xl font-extrabold tracking-tight sm:text-6xl">{NETWORK_LABEL[best.data.id]}</h1>
              <p className="mt-4 max-w-lg leading-relaxed">
                {t("best.summary", { network: NETWORK_LABEL[best.data.id], scenario: ts(`${dominant}.name`) })}
              </p>
              {tieMates.length > 0 && (
                <p className="mt-2 max-w-lg rounded-2xl bg-paper/70 px-4 py-2 text-sm font-semibold">
                  {t("best.tie", { others: tieMates.map((e) => NETWORK_LABEL[e.data.id]).join(", ") })}
                </p>
              )}

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <Stat
                  icon={<Coins size={15} aria-hidden />}
                  label={t("best.fee")}
                  value={best.feeUsd !== null ? fmt.usdt(best.feeUsd) : "—"}
                  sub={best.feeUsd !== null ? `≈ ${fmt.copSmall(best.feeUsd * rec.trm)}` : ""}
                />
                <Stat
                  icon={<Clock size={15} aria-hidden />}
                  label={t("best.time")}
                  value={best.inclusionSec !== null ? fmt.seconds(best.inclusionSec) : "—"}
                  sub={best.finalitySec !== null ? t("best.finality", { time: fmt.seconds(best.finalitySec) }) : ""}
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
              {best.data.set === 2 && (
                <p className="mt-4 max-w-lg rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white">{t("best.preliminary")}</p>
              )}
              <p className="mt-5 text-xs">{t("best.disclaimer")}</p>
            </div>
          </div>

          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-xl font-extrabold">{t("why.title")}</h2>
            <p className="text-sm leading-relaxed">
              {exp?.determinant
                ? t("why.determinant", { metric: `${exp.determinant.metric} · ${tm(`${exp.determinant.metric}.name`)}` })
                : t("why.noDeterminant")}
            </p>
            {exp?.determinant && best?.data.metrics[exp.determinant.metric]?.note && (
              <p className="mt-2 rounded-2xl bg-surface px-4 py-3 text-sm leading-relaxed">
                <span className="font-bold">{t("why.determinantNote")}</span>
                {tdn(best.data.metrics[exp.determinant.metric]!.note as string)}
              </p>
            )}
            {runnerUp && rec.separation !== null && (
              <p className="mt-3 text-sm leading-relaxed text-muted">
                {t("why.separation", { network: NETWORK_LABEL[runnerUp.data.id], p: fmt.decimal(rec.separation, 2) })}
              </p>
            )}
            <h3 className="mb-3 mt-6 text-xs font-bold uppercase tracking-[0.12em] text-muted">{t("why.blocks")}</h3>
            <ul className="space-y-3">
              {exp?.blocks.map((b) => (
                <li key={b.block}>
                  <div className="mb-1 flex justify-between text-sm font-bold">
                    <span>
                      <span className="mr-2 inline-grid h-6 w-6 place-items-center rounded-full bg-brand text-xs">{b.block}</span>
                      {tb(b.block)}
                    </span>
                    <span className="tabular-nums">{b.score !== null ? fmt.decimal(b.score, 2) : "—"}</span>
                  </div>
                  <div className="h-2 rounded-full bg-surface">
                    <div className="h-2 rounded-full bg-brand" style={{ width: `${(b.score ?? 0) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
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
          {t("changed", { from: NETWORK_LABEL[original.best.data.id], to: NETWORK_LABEL[best.data.id] })}
        </p>
      )}

      <Card className="mt-5">
        <h2 className="text-xl font-extrabold">{t("case.title")}</h2>
        <p className="mb-6 mt-1 text-sm text-muted">{t("case.sub")}</p>
        <div className="grid gap-8 md:grid-cols-2">
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-muted">{t("case.composition")}</h3>
            <ul className="space-y-3">
              {SCENARIO_IDS.map((e: ScenarioId) => (
                <li key={e}>
                  <div className="mb-1 flex justify-between text-sm font-bold">
                    <span>{ts(`${e}.name`)}</span>
                    <span className="tabular-nums">{fmt.percent(rec.lambda[e])}</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-surface">
                    <div className="h-2.5 rounded-full bg-ink" style={{ width: `${rec.lambda[e] * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-muted">{t("case.certainty")}</h3>
            <div className="flex items-center gap-4">
              <Semaphore
                light={rec.certainty === "high" ? "green" : rec.certainty === "medium" ? "yellow" : "red"}
                size="lg"
              />
              <div>
                <p className="text-2xl font-extrabold">
                  {t(`case.level.${rec.certainty}`)} <span className="text-base font-semibold text-muted">κ = {fmt.decimal(rec.kappa, 2)}</span>
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted">{t("case.certaintyNote")}</p>
            {rec.certainty === "low" && (
              <p className="mt-3 rounded-2xl bg-light-red/10 px-4 py-3 text-sm font-semibold">{t("case.lowWarning")}</p>
            )}
          </div>
        </div>
        <p className="mt-6 border-t border-line pt-4 text-xs text-muted">
          {t("why.weights")}{" "}
          {BLOCKS.map((b) => `${b} ${fmt.percent(rec.weights[b])}`).join(" · ")}
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

      {rec.bands.length > 0 && (
        <section className="mt-10">
          <h2 className="text-2xl font-extrabold tracking-tight">{t("bands.title")}</h2>
          <p className="mb-5 mt-1 max-w-3xl text-muted">{t("bands.sub")}</p>
          <div className="space-y-3">
            {rec.bands.map((band, i) => (
              <div key={i} className="rounded-card border-[1.5px] border-line bg-paper p-5">
                <div className="mb-3 flex items-center gap-3">
                  <span className="rounded-full bg-ink px-3 py-1 text-xs font-extrabold uppercase tracking-wider text-brand">
                    {t("bands.band", { n: i + 1 })}
                  </span>
                  {band.length > 1 && (
                    <span className="rounded-full bg-brand px-3 py-1 text-xs font-extrabold">{t("bands.tie")}</span>
                  )}
                </div>
                <ul className="space-y-3">
                  {band.map((e) => (
                    <ScoreBar key={e.data.id} e={e} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {rec.ranking.length > 1 && (
            <p className="mt-3 text-sm text-muted">
              {rec.ranking.slice(0, -1).map((e, i) => {
                const next = rec.ranking[i + 1];
                return t("bands.pi", {
                  a: NETWORK_LABEL[e.data.id],
                  b: NETWORK_LABEL[next.data.id],
                  p: fmt.decimal(rec.pi[e.data.id][next.data.id], 2),
                });
              }).join(" · ")}
            </p>
          )}
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-2xl font-extrabold tracking-tight">{t("compare.title")}</h2>
        <p className="mb-5 mt-1 text-muted">{t("compare.sub")}</p>
        <ul className="space-y-3">
          {[...rec.ranking, ...rec.excluded].map((e, i) => (
            <NetworkRow key={e.data.id} e={e} rank={e.admissible ? i + 1 : null} q={q} id={id} isBest={e === best} />
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
              <div key={e.data.id} className="rounded-2xl bg-paper p-5">
                <p className="mb-2 font-extrabold">{NETWORK_LABEL[e.data.id]}</p>
                <ul className="space-y-1.5 text-sm text-muted">
                  {e.excludedBy.map((by) => (
                    <li key={by}>
                      {by === "recipient"
                        ? t("excluded.recipient")
                        : t("excluded.gate", { gate: by, name: tg(`${by}.name`) })}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}

      {exp?.vsRunnerUp && best && (
        <Card className="mt-8">
          <h2 className="mb-4 text-xl font-extrabold">
            {t("vs.title", { network: NETWORK_LABEL[best.data.id], other: NETWORK_LABEL[exp.vsRunnerUp.network.data.id] })}
          </h2>
          <p className="text-sm">
            <span className="font-bold text-ok">{t("vs.winnerAhead")}</span>{" "}
            {exp.vsRunnerUp.winnerAhead.length ? exp.vsRunnerUp.winnerAhead.map((b) => `${b} · ${tb(b)}`).join(", ") : t("vs.nothing")}
          </p>
          <p className="mt-2 text-sm">
            <span className="font-bold text-warn">{t("vs.altAhead")}</span>{" "}
            {exp.vsRunnerUp.runnerAhead.length ? exp.vsRunnerUp.runnerAhead.map((b) => `${b} · ${tb(b)}`).join(", ") : t("vs.nothing")}
          </p>
        </Card>
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

function ScoreBar({ e }: { e: NetworkEvaluation }) {
  const t = useTranslations("result.bands");
  const fmt = useFmt();
  const score = e.score ?? 0;
  const lo = e.p5 ?? score;
  const hi = e.p95 ?? score;
  return (
    <li className="grid items-center gap-x-4 gap-y-1 sm:grid-cols-[9rem_1fr_5rem]">
      <span className="flex items-center gap-2 font-extrabold">
        <Semaphore light={e.light} size="sm" /> {NETWORK_LABEL[e.data.id]}
      </span>
      <div className="relative h-6" role="img" aria-label={`${t("range")}: ${fmt.decimal(lo, 2)} – ${fmt.decimal(hi, 2)}`}>
        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-surface" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-grey/60"
          style={{ left: `${lo * 100}%`, width: `${Math.max((hi - lo) * 100, 0.8)}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-paper bg-ink shadow"
          style={{ left: `${score * 100}%` }}
        />
      </div>
      <span className="text-right text-sm font-extrabold tabular-nums">{fmt.decimal(score, 3)}</span>
    </li>
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

  return (
    <li
      className={cx(
        "grid items-center gap-x-5 gap-y-4 rounded-card border-[1.5px] bg-paper p-5 transition-shadow hover:shadow-card lg:grid-cols-[2fr_auto_2fr_1.3fr_auto]",
        isBest ? "border-ink" : "border-line",
        !e.admissible && "bg-surface",
      )}
    >
      <div className="flex items-center gap-4">
        <span
          className={cx(
            "grid h-11 w-11 shrink-0 place-items-center rounded-full text-sm font-extrabold",
            rank === 1 ? "bg-brand" : !e.admissible ? "bg-line" : "bg-surface",
          )}
        >
          {rank ?? "—"}
        </span>
        <div>
          <p className="text-lg font-extrabold leading-tight">{NETWORK_LABEL[e.data.id]}</p>
          {isBest && (
            <span className="mt-1 inline-block rounded-full bg-ink px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-brand">
              {t("compare.best")}
            </span>
          )}
          {!e.admissible && (
            <span className="mt-1 inline-block rounded-full bg-light-red px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-white">
              {t("compare.excludedTag")}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2" title={t("compare.global")}>
        <Semaphore light={e.light} size="lg" />
        <span className="text-xs font-bold uppercase tracking-wide text-muted lg:sr-only">{t("compare.global")}</span>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {e.blocks.map((b) => (
          <div key={b.id} className="flex flex-col items-center gap-1.5 text-center">
            {b.light ? <Semaphore light={b.light} size="md" /> : <span className="h-5 w-5 rounded-full border-2 border-dashed border-grey" />}
            <span className="text-xs font-extrabold text-muted">{b.id}</span>
          </div>
        ))}
      </div>

      <div className="text-sm lg:text-right">
        <p className="font-bold tabular-nums">{e.feeUsd !== null ? fmt.usdt(e.feeUsd) : "—"}</p>
        <p className="tabular-nums text-muted">{e.inclusionSec !== null ? fmt.seconds(e.inclusionSec) : "—"}</p>
      </div>

      <Link
        href={`/result/${id}/${e.data.id}?${q}`}
        className={buttonClass(isBest ? "primary" : "secondary", "sm", "justify-self-start lg:justify-self-end")}
      >
        {t("compare.detail")} <ArrowRight size={14} aria-hidden />
      </Link>
    </li>
  );
}
