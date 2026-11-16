// Pagina del historial de recomendaciones del usuario.
"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { Button, ButtonLink, Card, Container, SectionTitle } from "@/components/ui";
import { HistoryRow } from "@/components/result/HistoryRow";
import { useRequireUser } from "@/lib/useRequireUser";
import { actions, useStore } from "@/state/store";

export default function HistoryPage() {
  const t = useTranslations("history");
  const { user, ready } = useRequireUser();
  const store = useStore();

  const entries = useMemo(
    () =>
      store.history
        .filter((h) => h.userId === user?.id)
        .sort((a, b) => b.createdAt - a.createdAt),
    [store.history, user?.id],
  );

  if (!ready || !user) return <Container className="py-12" />;

  return (
    <Container className="py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>
      <Card className="p-5 sm:p-8">
        {entries.length === 0 ? (
          <p className="py-10 text-center text-muted">{t("empty")}</p>
        ) : (
          entries.map((e) => <HistoryRow key={e.id} entry={e} />)
        )}
      </Card>
      <div className="mt-6 flex flex-wrap gap-3">
        <ButtonLink href="/transaction/new">{t("new")}</ButtonLink>
        {entries.length > 0 && (
          <Button
            variant="secondary"
            onClick={() => {
              if (window.confirm(t("confirmClear"))) actions.clearHistory(user.id);
            }}
          >
            <Trash2 size={16} aria-hidden /> {t("clear")}
          </Button>
        )}
      </div>
    </Container>
  );
}
