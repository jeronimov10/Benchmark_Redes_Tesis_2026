"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { COUNTRY_CODES } from "@/data/countries";
import type { NetworkId, Unit } from "@/engine/types";

/** Network names are proper nouns and are not translated. */
export const NETWORK_LABEL: Record<NetworkId, string> = {
  tempo: "Tempo",
  aptos: "Aptos",
  canton: "Canton",
  polygon: "Polygon",
  arbitrum: "Arbitrum",
  celo: "Celo",
};

export function useFmt() {
  const f = useFormatter();
  const locale = useLocale();
  const tc = useTranslations("common");

  const cop = (n: number) =>
    f.number(n, { style: "currency", currency: "COP", maximumFractionDigits: 0 });

  const usdt = (n: number) => {
    const formatted =
      n > 0 && n < 0.01
        ? f.number(n, { maximumSignificantDigits: 2 })
        : f.number(n, { maximumFractionDigits: 2 });
    return `${formatted} USDT`;
  };

  const seconds = (s: number) => {
    if (s < 1) return f.number(s, { style: "unit", unit: "second", maximumFractionDigits: 1 });
    if (s < 60) return f.number(s, { style: "unit", unit: "second", maximumFractionDigits: 1 });
    if (s < 3600) return f.number(s / 60, { style: "unit", unit: "minute", maximumFractionDigits: 1 });
    return f.number(s / 3600, { style: "unit", unit: "hour", maximumFractionDigits: 1 });
  };

  const percent = (fraction: number) =>
    f.number(fraction, { style: "percent", maximumSignificantDigits: 2 });

  const metricValue = (n: number, unit: Unit) => {
    switch (unit) {
      case "fraction":
        return percent(n);
      case "seconds":
        return seconds(n);
      case "ratio":
        return `${f.number(n, { maximumFractionDigits: 1 })}×`;
      case "percent":
        return `${f.number(n, { maximumFractionDigits: 2 })} %`;
      default:
        return f.number(n, { maximumFractionDigits: 2 });
    }
  };

  const date = (ms: number) =>
    f.dateTime(ms, { year: "numeric", month: "short", day: "numeric" });

  const country = (code: string) => {
    if (code === "OTHER") return tc("otherCountry");
    try {
      return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? code;
    } catch {
      return code;
    }
  };

  const countryOptions = () =>
    COUNTRY_CODES.map((code) => ({ code, label: country(code) })).sort((a, b) =>
      a.code === "OTHER" ? 1 : b.code === "OTHER" ? -1 : a.label.localeCompare(b.label, locale),
    );

  return { cop, usdt, seconds, percent, metricValue, date, country, countryOptions };
}
