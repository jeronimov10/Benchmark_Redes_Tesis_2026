"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

/** Segmented control "ES | EN": the current language is bold, a vertical bar separates them. */
export function LanguageSwitcher() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  return (
    <div
      role="group"
      aria-label={t("language")}
      className="flex items-center rounded-full border-[1.5px] border-line px-1 py-1 text-xs font-bold uppercase"
    >
      {routing.locales.map((l, i) => (
        <span key={l} className="flex items-center">
          {i > 0 && <span aria-hidden className="mx-0.5 h-4 w-px bg-ink/30" />}
          <button
            type="button"
            lang={l}
            aria-pressed={l === locale}
            onClick={() => l !== locale && router.replace(pathname, { locale: l })}
            className={`rounded-full px-3 py-1.5 uppercase transition-colors ${
              l === locale ? "bg-ink text-white" : "text-ink hover:bg-surface"
            }`}
          >
            {l}
          </button>
        </span>
      ))}
    </div>
  );
}
