"use client";

import { useTranslations } from "next-intl";
import { Card, Container, DemoBadge, Semaphore, SectionTitle } from "@/components/ui";
import {
  COMMERCE_MAX_COP,
  FEE_THRESHOLDS,
  FINALITY_THRESHOLDS,
  HIGH_VALUE_MIN_COP,
  LATENCY_THRESHOLDS,
  MICRO_MAX_COP,
  SCENARIO_WEIGHTS,
  SCENARIOS,
} from "@/engine/scenarios";
import { BLOCKS, METRICS, STATIC_THRESHOLDS } from "@/engine/risk-standard";
import { useFmt } from "@/lib/format";

export default function StandardPage() {
  const t = useTranslations("standard");
  const tm = useTranslations("metrics");
  const ts = useTranslations("scenarios");
  const td = useTranslations("detail");
  const fmt = useFmt();

  const cut: Record<string, string> = {
    micro: `1 – ${fmt.cop(MICRO_MAX_COP)}`,
    commerce: `${fmt.cop(MICRO_MAX_COP)} – ${fmt.cop(COMMERCE_MAX_COP)}`,
    remittance: `${fmt.cop(COMMERCE_MAX_COP)} – ${fmt.cop(HIGH_VALUE_MIN_COP)}`,
    high_value: `≥ ${fmt.cop(HIGH_VALUE_MIN_COP)}`,
  };

  return (
    <Container className="max-w-5xl py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>
      <p className="-mt-3 mb-8 flex items-center gap-2 text-xs text-muted">
        <DemoBadge /> {t("demoNote")}
      </p>

      <Card className="mb-5">
        <h2 className="mb-4 text-xl font-extrabold">{t("lights.title")}</h2>
        <ul className="grid gap-4 sm:grid-cols-3">
          {(["green", "yellow", "red"] as const).map((l) => (
            <li key={l} className="rounded-2xl bg-surface p-5">
              <p className="flex items-center gap-3 text-lg font-extrabold">
                <Semaphore light={l} size="lg" /> {t(`lights.${l}.name`)}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-muted">{t(`lights.${l}.desc`)}</p>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="mb-5">
        <h2 className="mb-4 text-xl font-extrabold">{t("rules.title")}</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm">
          {(["metric", "block", "network", "ranking"] as const).map((r) => (
            <li key={r}>{t(`rules.${r}`)}</li>
          ))}
        </ol>
      </Card>

      <Card className="mb-5 overflow-x-auto">
        <h2 className="mb-4 text-xl font-extrabold">{t("scenarios.title")}</h2>
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b-2 border-ink text-xs uppercase tracking-[0.1em] text-muted">
              <th className="py-2">{t("scenarios.scenario")}</th>
              <th>{t("scenarios.range")}</th>
              <th>{t("scenarios.weights")}</th>
              <th>{t("scenarios.fee")}</th>
              <th>{t("scenarios.latency")}</th>
              <th>{t("scenarios.finality")}</th>
            </tr>
          </thead>
          <tbody>
            {SCENARIOS.map((s) => (
              <tr key={s} className="border-b border-line align-top">
                <td className="py-2 font-bold">{ts(`${s}.name`)}</td>
                <td>{cut[s]}</td>
                <td className="tabular-nums">
                  {fmt.percent(SCENARIO_WEIGHTS[s].cost)} / {fmt.percent(SCENARIO_WEIGHTS[s].speed)} / {fmt.percent(SCENARIO_WEIGHTS[s].security)}
                </td>
                <td className="tabular-nums">{fmt.percent(FEE_THRESHOLDS[s][0])} → {fmt.percent(FEE_THRESHOLDS[s][1])}</td>
                <td className="tabular-nums">{fmt.seconds(LATENCY_THRESHOLDS[s][0])} → {fmt.seconds(LATENCY_THRESHOLDS[s][1])}</td>
                <td className="tabular-nums">{fmt.seconds(FINALITY_THRESHOLDS[s][0])} → {fmt.seconds(FINALITY_THRESHOLDS[s][1])}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-muted">{t("scenarios.note")}</p>
      </Card>

      {BLOCKS.map((b) => (
        <Card key={b} className="mb-6 overflow-x-auto">
          <h2 className="mb-1 flex items-center text-xl font-extrabold">
            <span className="mr-2 inline-grid h-9 w-9 place-items-center rounded-full bg-brand text-base font-extrabold">{b}</span>
            {td(`block.${b}`)}
          </h2>
          <p className="mb-3 text-sm text-muted">{td(`blockDesc.${b}`)}</p>
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b-2 border-ink text-xs uppercase tracking-[0.1em] text-muted">
                <th className="py-2">{td("col.metric")}</th>
                <th className="text-right">{td("col.target")}</th>
                <th className="text-right">{td("col.limit")}</th>
                <th className="pl-3">{t("direction")}</th>
              </tr>
            </thead>
            <tbody>
              {METRICS.filter((m) => m.block === b).map((m) => {
                const th = STATIC_THRESHOLDS[m.id];
                return (
                  <tr key={m.id} className="border-b border-line align-top">
                    <td className="py-2">
                      <span className="font-bold">{m.id}</span> {tm(`${m.id}.name`)}
                      {m.extension && <span className="ml-1 rounded bg-surface px-1 text-[10px] font-bold uppercase text-muted">{td("extension")}</span>}
                      <span className="block text-xs text-muted">{tm(`${m.id}.desc`)}</span>
                    </td>
                    <td className="text-right tabular-nums">{th ? fmt.metricValue(th[0], m.unit) : t("perScenario")}</td>
                    <td className="text-right tabular-nums">{th ? fmt.metricValue(th[1], m.unit) : t("perScenario")}</td>
                    <td className="pl-3 text-xs">{t(`dir.${m.dir}`)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      ))}
    </Container>
  );
}
