// Encabezado con logo y navegacion.
"use client";

import { useTranslations } from "next-intl";
import { UserRound } from "lucide-react";
import { buttonClass, Container } from "@/components/ui";
import { Link, usePathname } from "@/i18n/navigation";
import { useActiveUser, useHydrated } from "@/state/store";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function Logo() {
  const t = useTranslations("nav");
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label={t("brand")}>
      <span className="grid h-9 w-9 place-items-center rounded-full bg-brand text-base font-black">R</span>
      <span className="text-xl font-extrabold tracking-tight">{t("brand")}</span>
    </Link>
  );
}

export function Header() {
  const t = useTranslations("nav");
  const user = useActiveUser();
  const hydrated = useHydrated();
  const pathname = usePathname();

  const links = [
    { href: "/home", label: t("home") },
    { href: "/history", label: t("history") },
    { href: "/monitor", label: t("monitor") },
    { href: "/simulation", label: t("simulation") },
    { href: "/standard", label: t("standard") },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-paper/95 backdrop-blur">
      <Container className="flex h-[72px] items-center justify-between gap-4">
        <div className="flex items-center gap-10">
          <Logo />
          {hydrated && user && (
            <nav className="hidden items-center gap-1 md:flex" aria-label={t("main")}>
              {links.map((l) => {
                const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                      active ? "bg-brand" : "hover:bg-surface"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <LanguageSwitcher />
          {hydrated && user ? (
            <Link
              href="/start"
              title={t("switchUser")}
              className="flex max-w-[11rem] items-center gap-2 rounded-full border-[1.5px] border-line py-1.5 pl-1.5 pr-4 text-sm font-semibold hover:bg-surface"
            >
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand">
                <UserRound size={16} aria-hidden />
              </span>
              <span className="hidden truncate sm:block">{user.alias}</span>
            </Link>
          ) : (
            hydrated && (
              <Link href="/start" className={buttonClass("primary", "sm")}>
                {t("start")}
              </Link>
            )
          )}
        </div>
      </Container>
    </header>
  );
}
