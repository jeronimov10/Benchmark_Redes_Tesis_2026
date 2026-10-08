"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { ChevronRight } from "lucide-react";
import { DemoBadge, Semaphore } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { recommend } from "@/engine/scoring";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
import type { HistoryEntry } from "@/state/store";

export function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const t = useTranslations("history");
  const ts = useTranslations("scenarios");
  const fmt = useFmt();
  const rec = useMemo(() => recommend(entry.tx, entry.answers), [entry]);

  return (
    <Link
      href={`/result/${entry.id}`}
      className="-mx-3 flex items-center gap-4 rounded-2xl px-3 py-4 transition-colors hover:bg-surface"
    >
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand text-sm font-extrabold">
        {rec.best ? NETWORK_LABEL[rec.best.network.id][0] : "—"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 font-extrabold">
          {fmt.cop(entry.tx.amountCop)}
          <span className="text-xs font-semibold text-muted">≈ {fmt.usdt(rec.amountUsd)}</span>
          {entry.seeded && <DemoBadge />}
        </p>
        <p className="mt-0.5 text-sm text-muted">
          {fmt.date(entry.createdAt)} · {ts(`${rec.scenario}.name`)} · {t("to")} {fmt.country(entry.tx.recipient.country)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden text-sm font-bold sm:block">
          {rec.best ? NETWORK_LABEL[rec.best.network.id] : t("none")}
        </span>
        {rec.best && <Semaphore light={rec.best.light} />}
        <ChevronRight size={18} className="text-grey" aria-hidden />
      </div>
    </Link>
  );
}
