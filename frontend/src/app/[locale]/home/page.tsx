"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, History, Pencil, ShieldCheck } from "lucide-react";
import { buttonClass, Card, Container, SectionTitle } from "@/components/ui";
import { HistoryRow } from "@/components/result/HistoryRow";
import { Link } from "@/i18n/navigation";
import { useRecomendaciones } from "@/modelo/cliente";
import { entradaModelo } from "@/modelo/entrada";
import { networkLabel, useFmt } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import { useStore } from "@/state/store";

export default function HomePage() {
  const t = useTranslations("home");
  const to = useTranslations("onboarding");
  const fmt = useFmt();
  const { user, ready } = useRequireUser();
  const store = useStore();

  const entries = useMemo(
    () =>
      store.history
        .filter((h) => h.userId === user?.id)
        .sort((a, b) => b.createdAt - a.createdAt),
    [store.history, user?.id],
  );

  const entradas = useMemo(() => entries.map((e) => entradaModelo(e.tx, e.answers.country)), [entries]);
  const results = useRecomendaciones(entradas);

  const stats = useMemo(() => {
    // Every network of band 1 counts: tied networks are not split into a winner and a loser.
    const winners: Record<string, number> = {};
    for (const res of results) {
      for (const red of res?.resultado.bandas[0]?.redes ?? []) winners[red] = (winners[red] ?? 0) + 1;
    }
    const top = Object.entries(winners).sort((a, b) => b[1] - a[1])[0];
    const volume = entries.reduce((s, e) => s + e.tx.amountCop, 0);
    const pending = results.some((res) => res === null);
    return { top: top ? top[0] : null, volume, pending };
  }, [entries, results]);

  if (!ready || !user) return <Container className="py-12" />;
  const a = user.answers;

  return (
    <Container className="py-12">
      <SectionTitle sub={t("sub")}>{t("greeting", { name: user.alias })}</SectionTitle>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="relative flex flex-col justify-between gap-10 overflow-hidden rounded-[28px] bg-brand p-8 sm:p-10 lg:col-span-2">
          <span aria-hidden className="absolute -right-10 -top-10 h-44 w-44 rounded-full bg-white/30" />
          <div className="relative">
            <p className="text-xs font-bold uppercase tracking-[0.14em]">{t("cta.kicker")}</p>
            <p className="mt-3 max-w-lg text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
              {t("cta.title")}
            </p>
            <p className="mt-3 max-w-md">{t("cta.sub")}</p>
          </div>
          <div className="relative">
            <Link href="/transaction/new" className={buttonClass("primary", "lg")}>
              {t("cta.action")} <ArrowRight size={18} aria-hidden />
            </Link>
          </div>
        </div>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-lg font-extrabold">{t("profile")}</p>
            <Link
              href={`/onboarding?edit=${user.id}`}
              className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold hover:bg-surface"
            >
              <Pencil size={14} aria-hidden /> {t("edit")}
            </Link>
          </div>
          <ul className="flex flex-wrap gap-2 text-sm font-semibold">
            {[
              to(`opt.userType.${a.userType}`),
              fmt.country(a.country),
              to(`opt.experience.${a.experience}`),
              to(`opt.frequency.${a.frequency}`),
              to(`opt.defaultPriority.${a.defaultPriority}`),
            ].map((chip) => (
              <li key={chip} className="rounded-full bg-surface px-3.5 py-1.5">
                {chip}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-3">
        {[
          [t("stats.count"), String(entries.length)],
          [t("stats.volume"), fmt.cop(stats.volume)],
          [t("stats.top"), stats.top ? networkLabel(stats.top) : stats.pending ? "…" : "—"],
        ].map(([label, value]) => (
          <Card key={label} tone="surface" className="p-6 sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">{label}</p>
            <p className="mt-2 text-3xl font-extrabold tracking-tight">{value}</p>
          </Card>
        ))}
      </div>

      <Card className="mt-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xl font-extrabold">
            <History size={20} aria-hidden /> {t("recent")}
          </h2>
          <Link href="/history" className="rounded-full px-3 py-1.5 text-sm font-bold underline underline-offset-4 hover:bg-surface">
            {t("seeAll")}
          </Link>
        </div>
        {entries.length === 0 ? (
          <p className="py-8 text-center text-muted">{t("noHistory")}</p>
        ) : (
          <div>{entries.slice(0, 5).map((e) => <HistoryRow key={e.id} entry={e} />)}</div>
        )}
      </Card>

      <Link
        href="/standard"
        className="mt-5 flex items-center gap-3 rounded-card bg-surface p-5 font-bold transition-colors hover:bg-brand-soft"
      >
        <ShieldCheck size={20} aria-hidden /> {t("standardLink")}
        <ArrowRight size={16} className="ml-auto" aria-hidden />
      </Link>
    </Container>
  );
}
