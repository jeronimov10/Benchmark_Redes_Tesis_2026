"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { Button, Container, DemoBadge, ProgressBar } from "@/components/ui";
import { useRouter } from "@/i18n/navigation";
import { pedirRecomendacion } from "@/modelo/cliente";
import { entradaModelo } from "@/modelo/entrada";
import { useRequireUser } from "@/lib/useRequireUser";
import { actions, useStore } from "@/state/store";

const STEPS = ["scenario", "convert", "networks", "lights", "rank"] as const;
const STEP_MS = 650;

export default function AnalyzingPage() {
  const t = useTranslations("analyzing");
  const router = useRouter();
  const { ready, user } = useRequireUser();
  const { draft } = useStore();
  const [done, setDone] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
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

    const tx = draftRef.current;
    let alive = true;
    // The animation advances on a timer; the last step waits for the model (about 1 s).
    const timers: ReturnType<typeof setTimeout>[] = [];
    STEPS.slice(0, -1).forEach((_, i) => timers.push(setTimeout(() => alive && setDone(i + 1), (i + 1) * STEP_MS)));
    const minDelay = new Promise((r) => timers.push(setTimeout(r, (STEPS.length - 1) * STEP_MS)));
    Promise.all([pedirRecomendacion(entradaModelo(tx, user?.answers.country ?? "CO")), minDelay]).then(
      () => {
        if (!alive) return;
        setDone(STEPS.length);
        timers.push(
          setTimeout(() => {
            const id = actions.addHistory(tx);
            router.replace(id ? `/result/${id}` : "/transaction/new");
          }, 400),
        );
      },
      (e: Error) => alive && setError(e.message),
    );
    return () => {
      // Strict Mode re-runs effects: allow the second run to start again (the model call is cached).
      alive = false;
      timers.forEach(clearTimeout);
      started.current = false;
    };
  }, [ready, router, user, attempt]);

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
      {error && (
        <div className="mb-8 rounded-2xl bg-light-red/10 p-5 text-center ring-2 ring-light-red" role="alert">
          <p className="font-bold">{t("error")}</p>
          <p className="mt-1 text-sm text-muted">{error}</p>
          <Button
            className="mt-4"
            onClick={() => {
              setError(null);
              setDone(0);
              setAttempt((n) => n + 1);
            }}
          >
            {t("retry")}
          </Button>
        </div>
      )}
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
