"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, Gauge, ListChecks, Route } from "lucide-react";
import { ButtonLink, Container, DemoBadge, Semaphore, cx } from "@/components/ui";
import { NETWORK_IDS, SCENARIO_IDS, type Light, type ScenarioId } from "@/engine/types";
import { NETWORK_LABEL } from "@/lib/format";
import { useHydrated, useStore } from "@/state/store";

const STEP_ICONS = [ListChecks, Route, Gauge];
const SCENARIO_TONE: Record<ScenarioId, string> = {
  E1: "bg-pink text-ink",
  E2: "bg-brand text-ink",
  E3: "bg-ink text-white",
};
const SAMPLE: [string, Light][] = [
  ["Polygon", "green"],
  ["Arbitrum", "yellow"],
  ["Celo", "yellow"],
  ["Tempo", "yellow"],
  ["Canton", "red"],
];

export default function LandingPage() {
  const t = useTranslations("landing");
  const ts = useTranslations("scenarios");
  const tn = useTranslations("networks");
  const hydrated = useHydrated();
  const { users, activeId } = useStore();
  const hasUsers = hydrated && users.length > 0;
  const ctaHref = hydrated && activeId ? "/home" : "/start";

  return (
    <>
      <section className="overflow-hidden">
        <Container className="grid items-center gap-12 py-14 lg:grid-cols-[1.1fr_1fr] lg:py-24">
          <div className="animate-fade-up">
            <DemoBadge />
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">{t("hero.sub")}</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <ButtonLink href={ctaHref} size="lg">
                {hasUsers ? t("hero.ctaContinue") : t("hero.cta")} <ArrowRight size={18} aria-hidden />
              </ButtonLink>
              <ButtonLink href="/standard" variant="secondary" size="lg">
                {t("hero.ctaStandard")}
              </ButtonLink>
            </div>
          </div>

          <div className="relative" aria-hidden>
            <div className="absolute -right-6 -top-6 h-40 w-40 rounded-full bg-pink" />
            <div className="relative rounded-[32px] bg-brand p-7 shadow-lift sm:p-9">
              <p className="text-xs font-bold uppercase tracking-[0.14em]">{t("hero.cardKicker")}</p>
              <p className="mt-2 text-5xl font-extrabold tracking-tight">Polygon</p>
              <p className="mt-1 text-sm">{t("hero.cardSub")}</p>
              <ul className="mt-6 space-y-1 rounded-2xl bg-paper p-3">
                {SAMPLE.map(([name, light]) => (
                  <li key={name} className="flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-bold odd:bg-surface">
                    {name}
                    <Semaphore light={light} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Container>
      </section>

      <section className="bg-surface py-20">
        <Container>
          <h2 className="mb-10 text-3xl font-extrabold tracking-tight">{t("how.title")}</h2>
          <ol className="grid gap-5 md:grid-cols-3">
            {[0, 1, 2].map((i) => {
              const Icon = STEP_ICONS[i];
              return (
                <li key={i} className="rounded-card bg-paper p-7 shadow-card">
                  <span className="mb-5 grid h-12 w-12 place-items-center rounded-full bg-brand">
                    <Icon size={22} aria-hidden />
                  </span>
                  <p className="text-lg font-extrabold">{t(`how.s${i + 1}.title`)}</p>
                  <p className="mt-2 leading-relaxed text-muted">{t(`how.s${i + 1}.desc`)}</p>
                </li>
              );
            })}
          </ol>
        </Container>
      </section>

      <section className="py-20">
        <Container>
          <h2 className="mb-3 text-3xl font-extrabold tracking-tight">{t("scenarios.title")}</h2>
          <p className="mb-10 max-w-2xl text-lg text-muted">{t("scenarios.sub")}</p>
          <div className="grid gap-5 md:grid-cols-3">
            {SCENARIO_IDS.map((s) => (
              <div key={s} className={cx("flex min-h-56 flex-col justify-between rounded-card p-7", SCENARIO_TONE[s])}>
                <div><p className="text-2xl font-extrabold">{ts(`${s}.name`)}</p><p className="mt-1 text-sm font-bold opacity-70">{ts(`${s}.ticket`)}</p></div>
                <p className="text-sm leading-relaxed opacity-80">{ts(`${s}.desc`)}</p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      <section className="bg-surface py-20">
        <Container>
          <h2 className="mb-3 text-3xl font-extrabold tracking-tight">{t("networks.title")}</h2>
          <p className="mb-10 max-w-2xl text-lg text-muted">{t("networks.sub")}</p>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {NETWORK_IDS.map((id) => (
              <div key={id} className="rounded-card bg-paper p-6 shadow-card">
                <div className="mb-3 flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-full bg-ink text-sm font-extrabold text-brand">
                    {NETWORK_LABEL[id][0]}
                  </span>
                  <p className="text-lg font-extrabold">{NETWORK_LABEL[id]}</p>
                </div>
                <p className="text-sm leading-relaxed text-muted">{tn(`${id}.desc`)}</p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      <section className="pt-20">
        <Container>
          <div className="flex flex-col items-start justify-between gap-6 rounded-[32px] bg-brand p-10 sm:flex-row sm:items-center sm:p-14">
            <div>
              <h2 className="text-3xl font-extrabold tracking-tight">{t("final.title")}</h2>
              <p className="mt-2 max-w-xl">{t("final.sub")}</p>
            </div>
            <ButtonLink href={ctaHref} size="lg" className="shrink-0">
              {t("hero.cta")} <ArrowRight size={18} aria-hidden />
            </ButtonLink>
          </div>
        </Container>
      </section>
    </>
  );
}
