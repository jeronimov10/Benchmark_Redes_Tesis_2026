// Fila del historial de recomendaciones.
"use client";

import { useTranslations } from "next-intl";
import { ChevronRight, Loader2 } from "lucide-react";
import { DemoBadge, Semaphore } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { copToUsdt } from "@/engine/fx";
import { useEntrada, useRecomendacion } from "@/modelo/cliente";
import { entradaModelo, escenarioDominante, luzRed } from "@/modelo/entrada";
import { networkLabel, useFmt } from "@/lib/format";
import type { HistoryEntry } from "@/state/store";

export function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const t = useTranslations("history");
  const ts = useTranslations("scenarios");
  const fmt = useFmt();
  const { data } = useRecomendacion(useEntrada(entradaModelo(entry.tx, entry.answers.country)));
  const r = data?.resultado ?? null;
  const winners = r?.bandas[0]?.redes ?? [];

  return (
    <Link
      href={`/result/${entry.id}`}
      className="-mx-3 flex items-center gap-4 rounded-2xl px-3 py-4 transition-colors hover:bg-surface"
    >
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand text-sm font-extrabold">
        {!data ? <Loader2 size={16} className="animate-spin" aria-hidden /> : winners.length ? networkLabel(winners[0])[0] : "—"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 font-extrabold">
          {fmt.cop(entry.tx.amountCop)}
          <span className="text-xs font-semibold text-muted">≈ {fmt.usdt(copToUsdt(entry.tx.amountCop))}</span>
          {entry.seeded && <DemoBadge />}
        </p>
        <p className="mt-0.5 text-sm text-muted">
          {fmt.date(entry.createdAt)}
          {r && ` · ${ts(`${escenarioDominante(r.composicion)}.name`)}`} · {t("to")} {fmt.country(entry.tx.recipient.country)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden text-sm font-bold sm:block">
          {r ? (winners.length ? winners.map(networkLabel).join(" · ") : t("none")) : ""}
        </span>
        {r && winners.length > 0 && <Semaphore light={luzRed(r, winners[0])} />}
        <ChevronRight size={18} className="text-grey" aria-hidden />
      </div>
    </Link>
  );
}
