"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, Radio, WifiOff } from "lucide-react";
import { ButtonLink, Container, cx } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { edadCorta } from "@/lib/monitor";
import type { Procedencia, RespuestaRecomendar } from "@/modelo/tipos";

/** Full-page notice when the backend cannot support a recommendation (insufficient data). */
export function SinRecomendacion({ rec }: { rec: RespuestaRecomendar }) {
  const t = useTranslations("liveData.insufficient");
  return (
    <Container className="max-w-xl py-20 text-center">
      <AlertTriangle size={32} className="mx-auto mb-4 text-warn" aria-hidden />
      <p className="mb-2 text-lg font-bold">{t("title")}</p>
      {rec.motivo && <p className="mb-2 text-sm text-muted" lang="es">{rec.motivo}</p>}
      <p className="mb-6 text-sm text-muted">{t("body")}</p>
      <div className="flex justify-center gap-3">
        <ButtonLink href="/monitor">{t("monitor")}</ButtonLink>
        <ButtonLink href="/home" variant="secondary">{t("home")}</ButtonLink>
      </div>
    </Container>
  );
}

/** Strip above a result: how many inputs are live, how old, and whether the last refresh failed. */
export function AvisoDatos({ rec, obsoleto }: { rec: RespuestaRecomendar; obsoleto: boolean }) {
  const t = useTranslations("liveData.banner");
  const { frescura } = rec;
  const hayVivo = frescura.metricas_vivo > 0;
  return (
    <div
      className={cx(
        "mb-6 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl border-[1.5px] px-4 py-3 text-sm",
        obsoleto ? "border-warn bg-surface" : "border-line bg-surface",
      )}
      role="status"
    >
      {obsoleto ? (
        <WifiOff size={16} className="text-warn" aria-hidden />
      ) : (
        <Radio size={16} className={hayVivo ? "text-ok" : "text-grey"} aria-hidden />
      )}
      <span className="font-bold">
        {rec.modo === "medicion"
          ? t("baseMode")
          : hayVivo
            ? t("live", { n: frescura.metricas_vivo, total: frescura.metricas_total, age: edadCorta(frescura.edad_vivo_max_s) })
            : t("baseOnly")}
      </span>
      {obsoleto && <span className="text-warn">{t("stale")}</span>}
      <Link href="/monitor" className="ml-auto font-bold underline underline-offset-4">
        {t("monitor")}
      </Link>
    </div>
  );
}

/** Small tag showing whether a metric value is live or from the baseline measurement. */
export function EtiquetaProcedencia({ p }: { p: Procedencia | null | undefined }) {
  const t = useTranslations("liveData.tag");
  if (!p) return null;
  const vivo = p.origen === "vivo";
  const titulo = vivo
    ? t("liveTitle", { age: edadCorta(p.edad_s), n: p.n ?? 0, window: edadCorta(p.ventana_s) })
    : p.vivo_descartado
      ? t("baseWhy", { state: p.vivo_descartado.estado })
      : t("baseTitle");
  return (
    <span
      title={titulo}
      className={cx(
        "rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide",
        vivo ? "bg-brand text-ink" : "border border-line text-muted",
      )}
    >
      {vivo ? t("live") : t("base")}
      {vivo && <span className="ml-1 font-semibold normal-case">{edadCorta(p.edad_s)}</span>}
    </span>
  );
}
