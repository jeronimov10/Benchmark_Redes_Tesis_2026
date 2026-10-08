import { useTranslations } from "next-intl";
import { Container } from "@/components/ui";

export function Footer() {
  const t = useTranslations("footer");
  const tn = useTranslations("nav");
  return (
    <footer className="mt-16 bg-ink py-10 text-sm text-white">
      <Container className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-brand text-base font-black text-ink">R</span>
          <span className="text-xl font-extrabold tracking-tight">{tn("brand")}</span>
        </div>
        <div className="max-w-2xl space-y-2 text-white/70">
          <p className="font-semibold text-white">{t("demo")}</p>
          <p>{t("academic")}</p>
        </div>
      </Container>
    </footer>
  );
}
