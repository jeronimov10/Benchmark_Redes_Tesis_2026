"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { Container, DemoBadge, ProgressBar } from "@/components/ui";
import { useRouter } from "@/i18n/navigation";
import { useRequireUser } from "@/lib/useRequireUser";
import { actions, useStore } from "@/state/store";

const STEPS = ["scenario", "convert", "networks", "lights", "rank"] as const;
const STEP_MS = 650;

export default function AnalyzingPage() {
  const t = useTranslations("analyzing");
  const router = useRouter();
  const { ready } = useRequireUser();
  const { draft } = useStore();
  const [done, setDone] = useState(0);
  const started = useRef(false);
  const draftRef = useRef(draft);

  useEffect(() => {
    if (draft) draftRef.current = draft;
  }, [draft]);

  useEffect(() => {
    if (!ready) return;
    if (!draftRef.current) {
      router.replace("/transaction/new");
      return;
    }
    if (started.current) return;
    started.current = true;

    const timers: ReturnType<typeof setTimeout>[] = [];
    STEPS.forEach((_, i) => timers.push(setTimeout(() => setDone(i + 1), (i + 1) * STEP_MS)));
    timers.push(
      setTimeout(() => {
        const tx = draftRef.current;
        const id = tx ? actions.addHistory(tx) : null;
        router.replace(id ? `/result/${id}` : "/transaction/new");
      }, STEPS.length * STEP_MS + 400),
    );
    return () => {
      // Strict Mode re-runs effects: allow the second run to start the timers again.
      timers.forEach(clearTimeout);
      started.current = false;
    };
  }, [ready, router]);

  return (
    <Container className="max-w-xl py-20">
      <div className="mb-10 text-center">
        <div className="mx-auto mb-6 flex items-center justify-center gap-2" aria-hidden>
          {["bg-light-green", "bg-light-yellow", "bg-light-red"].map((c, i) => (
            <span
              key={c}
              className={`h-5 w-5 rounded-full ${c} animate-dot-pulse`}
              style={{ animationDelay: `${i * 0.25}s` }}
            />
          ))}
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
        <p className="mt-3 text-lg text-muted" aria-live="polite">
          {t("sub")}
        </p>
      </div>
      <ProgressBar value={done / STEPS.length} />
      <ul className="mt-8 space-y-4">
        {STEPS.map((s, i) => (
          <li key={s} className={`flex items-center gap-4 transition-opacity ${i < done ? "opacity-100" : "opacity-35"}`}>
            <span className={`grid h-7 w-7 place-items-center rounded-full ${i < done ? "bg-brand" : "bg-line"}`}>
              {i < done && <Check size={15} strokeWidth={3} aria-hidden />}
            </span>
            <span className="font-semibold">{t(`steps.${s}`)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-10 flex items-center justify-center gap-2 text-sm text-muted">
        <DemoBadge /> {t("disclaimer")}
      </p>
    </Container>
  );
}
