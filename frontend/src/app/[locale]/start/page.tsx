// Pagina para empezar: elegir un perfil existente o crear uno nuevo.
"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { Button, ButtonLink, Card, Container, DemoBadge, SectionTitle } from "@/components/ui";
import { Link, useRouter } from "@/i18n/navigation";
import { useFmt } from "@/lib/format";
import { actions, useHydrated, useStore } from "@/state/store";

export default function StartPage() {
  const t = useTranslations("start");
  const to = useTranslations("onboarding");
  const fmt = useFmt();
  const router = useRouter();
  const store = useStore();
  const hydrated = useHydrated();

  const select = (id: string) => {
    actions.setActive(id);
    router.push("/home");
  };

  return (
    <Container className="py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>

      {hydrated && store.users.length === 0 && (
        <Card tone="yellow" className="mb-6 text-center">
          <p className="mb-5 text-lg font-semibold">{t("empty")}</p>
          <ButtonLink href="/onboarding" size="lg">
            <Plus size={18} aria-hidden /> {t("create")}
          </ButtonLink>
        </Card>
      )}

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {store.users.map((u) => {
          const count = store.history.filter((h) => h.userId === u.id).length;
          return (
            <Card key={u.id} className="flex flex-col gap-4 p-6 sm:p-6">
              <div className="flex items-center gap-4">
                <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand text-xl font-extrabold">
                  {u.alias[0]?.toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xl font-extrabold">{u.alias}</p>
                  <p className="text-sm text-muted">
                    {to(`opt.userType.${u.answers.userType}`)} · {fmt.country(u.answers.country)}
                  </p>
                </div>
              </div>
              <p className="text-sm text-muted">{t("meta", { count, date: fmt.date(u.createdAt) })}</p>
              <div className="mt-auto flex gap-2">
                <Button className="flex-1" onClick={() => select(u.id)}>
                  {t("enter")} <ArrowRight size={16} aria-hidden />
                </Button>
                <Button
                  variant="secondary"
                  aria-label={t("delete")}
                  title={t("delete")}
                  onClick={() => {
                    if (window.confirm(t("confirmDelete", { alias: u.alias }))) actions.deleteUser(u.id);
                  }}
                >
                  <Trash2 size={16} aria-hidden />
                </Button>
              </div>
            </Card>
          );
        })}

        {hydrated && store.users.length > 0 && (
          <Link
            href="/onboarding"
            className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-card border-[1.5px] border-dashed border-grey p-6 text-base font-bold transition-colors hover:border-ink hover:bg-surface"
          >
            <span className="grid h-12 w-12 place-items-center rounded-full bg-brand">
              <Plus aria-hidden />
            </span>
            {t("create")}
          </Link>
        )}
      </div>
      <p className="mt-8 flex items-center gap-2 text-sm text-muted">
        <DemoBadge /> {t("storage")}
      </p>
    </Container>
  );
}
