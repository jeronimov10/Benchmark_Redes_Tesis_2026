"use client";

import { useTranslations } from "next-intl";
import { Card, Container, DemoBadge, Semaphore, SectionTitle } from "@/components/ui";
import { BLOCKS, METRICS } from "@/engine/metrics";
import { SCENARIO_IDS, type ScenarioId } from "@/engine/types";
import { useFmt } from "@/lib/format";
import { UNIDAD } from "@/modelo/entrada";
import { useInfoModelo } from "@/modelo/cliente";

const ESCENARIO_MODELO = { E1: "remesas", E2: "comercio", E3: "altovalor" } as const satisfies Record<ScenarioId, string>;
const DIRECCION = { menor: "lower", mayor: "higher", nueves: "higher" } as const;

const GATES = ["G1", "G2", "G3", "G4"] as const;

export default function StandardPage() {
  const t = useTranslations("standard");
  const tm = useTranslations("metrics");
  const ts = useTranslations("scenarios");
  const td = useTranslations("detail");
  const tg = useTranslations("gates");
  const fmt = useFmt();
  const info = useInfoModelo();
  const umbral = (v: number | { fraccion_ticket: number }) =>
    typeof v === "number" ? null : fmt.percent(v.fraccion_ticket);

  return (
    <Container className="max-w-5xl py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>
      <p className="-mt-3 mb-8 flex items-start gap-2 text-sm text-muted">
        <DemoBadge className="mt-0.5" /> {t("demoNote")}
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
        <h2 className="mb-4 text-xl font-extrabold">{t("model.title")}</h2>
        <ol className="space-y-3">
          {(["s1", "s2", "s3", "s4", "s5", "s6"] as const).map((s, i) => (
            <li key={s} className="flex gap-4 text-sm leading-relaxed">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand font-extrabold">{i + 1}</span>
              <span className="pt-1">{t(`model.${s}`)}</span>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="mb-5 overflow-x-auto">
        <h2 className="mb-4 text-xl font-extrabold">{t("scenarios.title")}</h2>
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead>
            <tr className="border-b-2 border-ink text-xs uppercase tracking-[0.1em] text-muted">
              <th className="py-2">{t("scenarios.scenario")}</th>
              <th>{t("scenarios.ticket")}</th>
              <th>{t("scenarios.restriction")}</th>
              <th>{t("scenarios.weights")}</th>
            </tr>
          </thead>
          <tbody>
            {SCENARIO_IDS.map((e) => (
              <tr key={e} className="border-b border-line align-top">
                <td className="py-3 font-extrabold">
                  <span className="mr-2 rounded-md bg-surface px-1.5 py-0.5 text-xs">{e}</span>
                  {ts(`${e}.name`)}
                </td>
                <td>{ts(`${e}.ticket`)}</td>
                <td>{t(`scenarios.r.${e}`)}</td>
                <td className="tabular-nums">
                  {info ? BLOCKS.map((b) => fmt.decimal(info.escenarios[ESCENARIO_MODELO[e]].pesos[b], 2)).join(" / ") : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-muted">{t("scenarios.note")}</p>
      </Card>

      <Card className="mb-5">
        <h2 className="mb-1 text-xl font-extrabold">{tg("title")}</h2>
        <p className="mb-4 text-sm text-muted">{tg("sub")}</p>
        <ul className="grid gap-3 sm:grid-cols-2">
          {GATES.map((g) => (
            <li key={g} className="rounded-2xl bg-surface p-4 text-sm">
              <p className="font-extrabold">
                <span className="mr-2 rounded-md bg-paper px-1.5 py-0.5 text-xs">{g}</span>
                {tg(`${g}.name`)}
              </p>
              <p className="mt-1 text-muted">{tg(`${g}.desc`)}</p>
            </li>
          ))}
        </ul>
      </Card>

      <h2 className="mb-4 mt-10 text-2xl font-extrabold tracking-tight">{t("catalog.title")}</h2>
      {BLOCKS.map((b) => (
        <Card key={b} className="mb-5 overflow-x-auto">
          <h3 className="mb-1 flex items-center text-xl font-extrabold">
            <span className="mr-3 inline-grid h-9 w-9 place-items-center rounded-full bg-brand text-base">{b}</span>
            {td(`block.${b}`)}
          </h3>
          <p className="mb-3 text-sm text-muted">{td(`blockDesc.${b}`)}</p>
          <table className="w-full min-w-[620px] text-left text-sm">
            <thead>
              <tr className="border-b-2 border-ink text-xs uppercase tracking-[0.1em] text-muted">
                <th className="py-2">{td("col.metric")}</th>
                <th className="text-right">{td("col.target")}</th>
                <th className="text-right">{td("col.limit")}</th>
                <th className="pl-4">{t("direction")}</th>
                <th>{t("catalog.source")}</th>
              </tr>
            </thead>
            <tbody>
              {METRICS.filter((m) => m.block === b).map((m) => (
                <tr key={m.id} className="border-b border-line align-top">
                  <td className="py-2">
                    <span className="mr-2 rounded-md bg-surface px-1.5 py-0.5 text-xs font-bold">{m.id}</span>
                    <span className="font-bold">{tm(`${m.id}.name`)}</span>
                    <span className="block text-xs text-muted">{tm(`${m.id}.desc`)}</span>
                  </td>
                  <td className="text-right tabular-nums">
                    {info ? (umbral(info.metricas[m.id].objetivo) ?? fmt.metricValue(info.metricas[m.id].objetivo as number, UNIDAD[m.id])) : "—"}
                  </td>
                  <td className="text-right tabular-nums">
                    {info ? (umbral(info.metricas[m.id].inaceptable) ?? fmt.metricValue(info.metricas[m.id].inaceptable as number, UNIDAD[m.id])) : "—"}
                  </td>
                  <td className="pl-4 text-xs">{info ? t(`dir.${DIRECCION[info.metricas[m.id].direccion]}`) : "—"}</td>
                  <td className="text-xs">{t(`catalog.${m.source}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}

      <Card tone="surface" className="mt-5">
        <h2 className="mb-2 text-lg font-extrabold">{t("limits.title")}</h2>
        <p className="text-sm leading-relaxed text-muted">{t("limits.body")}</p>
      </Card>
    </Container>
  );
}
