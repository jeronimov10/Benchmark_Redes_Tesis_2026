"use client";

import { Suspense } from "react";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Button, Card, Chip, Choice, ChoiceGrid, Container, Field, inputClass, ProgressBar } from "@/components/ui";
import { useRouter } from "@/i18n/navigation";
import { useFmt } from "@/lib/format";
import { actions, useStore } from "@/state/store";
import type {
  AmountBracket,
  Experience,
  Frequency,
  PriorityKey,
  PrivacyPref,
  ProfileAnswers,
  Purpose,
  RecipientType,
  Tolerance,
  UserType,
  WalletType,
} from "@/engine/types";

const DEFAULTS: ProfileAnswers = {
  userType: "natural",
  country: "CO",
  experience: "basic",
  usedStablecoins: false,
  walletType: "exchange",
  purposes: [],
  frequency: "monthly",
  typicalAmount: "small",
  recipientTypes: [],
  destinationCountries: [],
  defaultPriority: "balanced",
  costTolerance: "medium",
  timeTolerance: "medium",
  riskTolerance: "medium",
  needsReconciliation: false,
  privacyPref: "indifferent",
};

const OPTIONS = {
  userType: ["natural", "business", "institution"] satisfies UserType[],
  experience: ["none", "basic", "intermediate", "advanced"] satisfies Experience[],
  walletType: ["none", "exchange", "selfcustody"] satisfies WalletType[],
  purposes: ["remittance", "commerce", "payroll", "treasury", "p2p"] satisfies Purpose[],
  frequency: ["daily", "weekly", "monthly", "occasional"] satisfies Frequency[],
  typicalAmount: ["micro", "small", "medium", "large", "xlarge"] satisfies AmountBracket[],
  recipientTypes: ["person", "business", "exchange", "ownWallet", "unknown"] satisfies RecipientType[],
  defaultPriority: ["cost", "speed", "security", "balanced"] satisfies PriorityKey[],
  tolerance: ["low", "medium", "high"] satisfies Tolerance[],
  privacyPref: ["auditable", "private", "indifferent"] satisfies PrivacyPref[],
};

const STEPS = ["identity", "experience", "usage", "amounts", "risk", "summary"] as const;

function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function Wizard() {
  const t = useTranslations("onboarding");
  const fmt = useFmt();
  const router = useRouter();
  const params = useSearchParams();
  const store = useStore();

  const editId = params.get("edit");
  const editing = store.users.find((u) => u.id === editId) ?? null;

  const [step, setStep] = useState(0);
  const [alias, setAlias] = useState(editing?.alias ?? "");
  const [a, setA] = useState<ProfileAnswers>(editing?.answers ?? DEFAULTS);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = <K extends keyof ProfileAnswers>(k: K, v: ProfileAnswers[K]) =>
    setA((prev) => ({ ...prev, [k]: v }));

  const opt = (group: string, v: string) => t(`opt.${group}.${v}`);
  const optDesc = (group: string, v: string) =>
    t.has(`opt.${group}.${v}_d`) ? t(`opt.${group}.${v}_d`) : undefined;

  function validate(current: number): boolean {
    const e: Record<string, string> = {};
    if (STEPS[current] === "identity" && alias.trim().length < 2) e.alias = t("errors.alias");
    if (STEPS[current] === "usage" && a.purposes.length === 0) e.purposes = t("errors.pickOne");
    if (STEPS[current] === "amounts") {
      if (a.recipientTypes.length === 0) e.recipientTypes = t("errors.pickOne");
      if (a.destinationCountries.length === 0) e.destinationCountries = t("errors.pickOne");
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  const next = () => validate(step) && setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const back = () => {
    setErrors({});
    setStep((s) => Math.max(s - 1, 0));
  };

  function finish() {
    if (editing) {
      actions.updateUser(editing.id, alias.trim(), a);
    } else {
      actions.createUser(alias.trim(), a);
    }
    router.push("/home");
  }

  const radio = <K extends keyof ProfileAnswers>(key: K, group: string, values: readonly string[], cols: 2 | 3 | 4 = 2) => (
    <ChoiceGrid cols={cols}>
      {values.map((v) => (
        <Choice
          key={v}
          selected={a[key] === v}
          onClick={() => set(key, v as ProfileAnswers[K])}
          title={opt(group, v)}
          desc={optDesc(group, v)}
        />
      ))}
    </ChoiceGrid>
  );

  const multi = (key: "purposes" | "recipientTypes", group: string, values: readonly string[], cols: 2 | 3 = 2) => (
    <ChoiceGrid cols={cols}>
      {values.map((v) => (
        <Choice
          key={v}
          multi
          selected={(a[key] as string[]).includes(v)}
          onClick={() => set(key, toggle(a[key] as string[], v) as never)}
          title={opt(group, v)}
          desc={optDesc(group, v)}
        />
      ))}
    </ChoiceGrid>
  );

  const bool = (key: "usedStablecoins" | "needsReconciliation") => (
    <ChoiceGrid cols={2}>
      <Choice selected={a[key]} onClick={() => set(key, true)} title={t("yes")} />
      <Choice selected={!a[key]} onClick={() => set(key, false)} title={t("no")} />
    </ChoiceGrid>
  );

  const tolerance = (key: "costTolerance" | "timeTolerance" | "riskTolerance", label: string, hint: string) => (
    <Field label={label} hint={hint}>
      <ChoiceGrid cols={3}>
        {OPTIONS.tolerance.map((v) => (
          <Choice key={v} selected={a[key] === v} onClick={() => set(key, v)} title={opt("tolerance", v)} />
        ))}
      </ChoiceGrid>
    </Field>
  );

  const countryPicker = (
    <div className="flex flex-wrap gap-2">
      {fmt.countryOptions().map(({ code, label }) => (
        <Chip
          key={code}
          selected={a.destinationCountries.includes(code)}
          onClick={() => set("destinationCountries", toggle(a.destinationCountries, code))}
        >
          {label}
        </Chip>
      ))}
    </div>
  );

  const stepKey = STEPS[step];

  return (
    <Container className="max-w-3xl py-12">
      <div className="mb-8">
        <div className="mb-3 flex items-center justify-between text-xs font-bold uppercase tracking-[0.14em] text-muted">
          <span>{t("progress", { current: step + 1, total: STEPS.length })}</span>
          <span>{editing ? t("save") : t("finish")}</span>
        </div>
        <ProgressBar value={(step + 1) / STEPS.length} />
      </div>

      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t(`steps.${stepKey}.title`)}</h1>
      <p className="mb-8 mt-3 text-lg text-muted">{t(`steps.${stepKey}.sub`)}</p>

      <Card>
        {stepKey === "identity" && (
          <>
            <Field label={t("q.alias")} hint={t("h.alias")} error={errors.alias}>
              <input
                className={inputClass}
                value={alias}
                maxLength={30}
                onChange={(e) => setAlias(e.target.value)}
                placeholder={t("placeholder.alias")}
              />
            </Field>
            <Field label={t("q.userType")}>{radio("userType", "userType", OPTIONS.userType, 3)}</Field>
            <Field label={t("q.country")}>
              <select className={inputClass} value={a.country} onChange={(e) => set("country", e.target.value)}>
                {fmt.countryOptions().map(({ code, label }) => (
                  <option key={code} value={code}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </>
        )}

        {stepKey === "experience" && (
          <>
            <Field label={t("q.experience")}>{radio("experience", "experience", OPTIONS.experience)}</Field>
            <Field label={t("q.usedStablecoins")}>{bool("usedStablecoins")}</Field>
            <Field label={t("q.walletType")}>{radio("walletType", "walletType", OPTIONS.walletType, 3)}</Field>
          </>
        )}

        {stepKey === "usage" && (
          <>
            <Field label={t("q.purposes")} hint={t("h.multi")} error={errors.purposes}>
              {multi("purposes", "purposes", OPTIONS.purposes)}
            </Field>
            <Field label={t("q.frequency")}>{radio("frequency", "frequency", OPTIONS.frequency, 4)}</Field>
          </>
        )}

        {stepKey === "amounts" && (
          <>
            <Field label={t("q.typicalAmount")} hint={t("h.typicalAmount")}>
              {radio("typicalAmount", "typicalAmount", OPTIONS.typicalAmount, 3)}
            </Field>
            <Field label={t("q.recipientTypes")} hint={t("h.multi")} error={errors.recipientTypes}>
              {multi("recipientTypes", "recipientTypes", OPTIONS.recipientTypes, 3)}
            </Field>
            <Field label={t("q.destinationCountries")} hint={t("h.multi")} error={errors.destinationCountries}>
              {countryPicker}
            </Field>
          </>
        )}

        {stepKey === "risk" && (
          <>
            <Field label={t("q.defaultPriority")}>
              {radio("defaultPriority", "defaultPriority", OPTIONS.defaultPriority, 4)}
            </Field>
            {tolerance("costTolerance", t("q.costTolerance"), t("h.costTolerance"))}
            {tolerance("timeTolerance", t("q.timeTolerance"), t("h.timeTolerance"))}
            {tolerance("riskTolerance", t("q.riskTolerance"), t("h.riskTolerance"))}
            <Field label={t("q.needsReconciliation")} hint={t("h.needsReconciliation")}>
              {bool("needsReconciliation")}
            </Field>
            <Field label={t("q.privacyPref")} hint={t("h.privacyPref")}>
              {radio("privacyPref", "privacyPref", OPTIONS.privacyPref, 3)}
            </Field>
          </>
        )}

        {stepKey === "summary" && (
          <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
            {(
              [
                ["alias", alias],
                ["userType", opt("userType", a.userType)],
                ["country", fmt.country(a.country)],
                ["experience", opt("experience", a.experience)],
                ["walletType", opt("walletType", a.walletType)],
                ["purposes", a.purposes.map((p) => opt("purposes", p)).join(", ")],
                ["frequency", opt("frequency", a.frequency)],
                ["typicalAmount", opt("typicalAmount", a.typicalAmount)],
                ["recipientTypes", a.recipientTypes.map((p) => opt("recipientTypes", p)).join(", ")],
                ["destinationCountries", a.destinationCountries.map(fmt.country).join(", ")],
                ["defaultPriority", opt("defaultPriority", a.defaultPriority)],
                ["privacyPref", opt("privacyPref", a.privacyPref)],
              ] as const
            ).map(([k, v]) => (
              <div key={k} className="border-b border-line pb-3">
                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">{t(`summary.${k}`)}</dt>
                <dd className="mt-0.5 font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>

      <div className="mt-8 flex items-center justify-between">
        <Button variant="ghost" onClick={back} disabled={step === 0}>
          <ArrowLeft size={16} aria-hidden /> {t("back")}
        </Button>
        {stepKey === "summary" ? (
          <Button size="lg" onClick={finish}>
            <Check size={16} aria-hidden /> {editing ? t("save") : t("finish")}
          </Button>
        ) : (
          <Button size="lg" onClick={next}>
            {t("next")} <ArrowRight size={16} aria-hidden />
          </Button>
        )}
      </div>
    </Container>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense>
      <Wizard />
    </Suspense>
  );
}
