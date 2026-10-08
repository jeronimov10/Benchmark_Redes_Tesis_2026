"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, ArrowLeftRight } from "lucide-react";
import { z } from "zod";
import { Button, Card, Chip, Choice, ChoiceGrid, Container, DemoBadge, Field, inputClass, SectionTitle } from "@/components/ui";
import { PrioritySliders } from "@/components/result/PrioritySliders";
import { classifyScenario, MIN_AMOUNT_COP } from "@/engine/scenarios";
import { defaultPriorities } from "@/engine/scoring";
import { copToUsdt, DEMO_TRM } from "@/engine/fx";
import { useRouter } from "@/i18n/navigation";
import { NETWORK_LABEL, useFmt } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import { actions } from "@/state/store";
import {
  NETWORK_IDS,
  type NetworkId,
  type Purpose,
  type RecipientType,
  type TxInput,
  type Urgency,
  type Weights,
} from "@/engine/types";

const PURPOSES: Purpose[] = ["p2p", "commerce", "remittance", "payroll", "treasury"];
const RECIPIENTS: RecipientType[] = ["person", "business", "exchange", "ownWallet", "unknown"];
const URGENCIES: Urgency[] = ["low", "normal", "urgent"];
const MAX_COP = 10_000_000_000;

export default function NewTransactionPage() {
  const t = useTranslations("tx");
  const to = useTranslations("onboarding");
  const ts = useTranslations("scenarios");
  const fmt = useFmt();
  const router = useRouter();
  const { user, ready } = useRequireUser();

  const [amount, setAmount] = useState("");
  const [purpose, setPurpose] = useState<Purpose>("p2p");
  const [urgency, setUrgency] = useState<Urgency>("normal");
  const [rType, setRType] = useState<RecipientType>("person");
  const [rCountry, setRCountry] = useState("CO");
  const [firstTime, setFirstTime] = useState(false);
  const [needsMemo, setNeedsMemo] = useState(false);
  const [accepted, setAccepted] = useState<NetworkId[] | "unknown">("unknown");
  const [priorities, setPriorities] = useState<Weights | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const amountCop = Number(amount.replace(/\D/g, "")) || 0;
  const prio = priorities ?? defaultPriorities(user?.answers.defaultPriority ?? "balanced");
  const scenario = amountCop >= MIN_AMOUNT_COP ? classifyScenario(amountCop, purpose) : null;

  const schema = useMemo(
    () =>
      z.object({
        amountCop: z
          .number()
          .min(MIN_AMOUNT_COP, t("errors.amountMin"))
          .max(MAX_COP, t("errors.amountMax")),
        accepted: z.union([z.literal("unknown"), z.array(z.string()).min(1, t("errors.accepted"))]),
      }),
    [t],
  );

  if (!ready || !user) return <Container className="py-10" />;

  function submit() {
    const parsed = schema.safeParse({ amountCop, accepted });
    if (!parsed.success) {
      const e: Record<string, string> = {};
      for (const issue of parsed.error.issues) e[String(issue.path[0])] = issue.message;
      setErrors(e);
      return;
    }
    const tx: TxInput = {
      amountCop,
      purpose,
      urgency,
      priorities: prio,
      recipient: { type: rType, country: rCountry, firstTime, accepted, needsMemo },
    };
    actions.setDraft(tx);
    router.push("/transaction/analyzing");
  }

  const toggleNet = (id: NetworkId) => {
    const current = accepted === "unknown" ? [] : accepted;
    setAccepted(current.includes(id) ? current.filter((x) => x !== id) : [...current, id]);
  };

  return (
    <Container className="max-w-3xl py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>

      <Card className="mb-5">
        <h2 className="mb-6 text-2xl font-extrabold tracking-tight">{t("sections.operation")}</h2>
        <Field label={t("q.amount")} hint={t("h.amount")} error={errors.amountCop}>
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-sm font-extrabold text-muted">COP</span>
              <input
                inputMode="numeric"
                className={`${inputClass} pl-16 text-2xl font-extrabold`}
                value={amountCop ? new Intl.NumberFormat("es-CO").format(amountCop) : amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0"
                aria-label={t("q.amount")}
              />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-2 font-semibold">
              <ArrowLeftRight size={14} aria-hidden />
              {fmt.usdt(copToUsdt(amountCop))}
            </span>
            <span className="text-xs text-muted">
              {t("trmNote", { trm: fmt.cop(DEMO_TRM) })} <DemoBadge className="ml-1" />
            </span>
            {scenario && (
              <span className="rounded-full bg-brand px-3.5 py-1.5 text-xs font-extrabold">
                {t("scenarioDetected", { scenario: ts(`${scenario}.name`) })}
              </span>
            )}
          </div>
        </Field>

        <Field label={t("q.purpose")}>
          <ChoiceGrid cols={3}>
            {PURPOSES.map((p) => (
              <Choice key={p} selected={purpose === p} onClick={() => setPurpose(p)} title={to(`opt.purposes.${p}`)} />
            ))}
          </ChoiceGrid>
        </Field>

        <Field label={t("q.urgency")}>
          <ChoiceGrid cols={3}>
            {URGENCIES.map((u) => (
              <Choice key={u} selected={urgency === u} onClick={() => setUrgency(u)} title={t(`urgency.${u}`)} desc={t(`urgency.${u}_d`)} />
            ))}
          </ChoiceGrid>
        </Field>
      </Card>

      <Card className="mb-5">
        <h2 className="mb-1 text-2xl font-extrabold tracking-tight">{t("sections.recipient")}</h2>
        <p className="mb-6 text-sm text-muted">{t("originNote")}</p>
        <Field label={t("q.recipientType")}>
          <ChoiceGrid cols={3}>
            {RECIPIENTS.map((r) => (
              <Choice key={r} selected={rType === r} onClick={() => setRType(r)} title={to(`opt.recipientTypes.${r}`)} />
            ))}
          </ChoiceGrid>
        </Field>
        <Field label={t("q.recipientCountry")}>
          <select className={inputClass} value={rCountry} onChange={(e) => setRCountry(e.target.value)}>
            {fmt.countryOptions().map(({ code, label }) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("q.firstTime")}>
          <ChoiceGrid cols={2}>
            <Choice selected={firstTime} onClick={() => setFirstTime(true)} title={t("firstTime.yes")} />
            <Choice selected={!firstTime} onClick={() => setFirstTime(false)} title={t("firstTime.no")} />
          </ChoiceGrid>
        </Field>
        <Field label={t("q.accepted")} hint={t("h.accepted")} error={errors.accepted}>
          <div className="flex flex-wrap gap-2" role={accepted === "unknown" ? "radiogroup" : "group"}>
            <Chip radio selected={accepted === "unknown"} onClick={() => setAccepted("unknown")}>
              {t("acceptedUnknown")}
            </Chip>
            {NETWORK_IDS.map((id) => (
              <Chip key={id} selected={accepted !== "unknown" && accepted.includes(id)} onClick={() => toggleNet(id)}>
                {NETWORK_LABEL[id]}
              </Chip>
            ))}
          </div>
        </Field>
        <Field label={t("q.needsMemo")} hint={t("h.needsMemo")}>
          <ChoiceGrid cols={2}>
            <Choice selected={needsMemo} onClick={() => setNeedsMemo(true)} title={to("yes")} />
            <Choice selected={!needsMemo} onClick={() => setNeedsMemo(false)} title={to("no")} />
          </ChoiceGrid>
        </Field>
      </Card>

      <Card className="mb-8">
        <h2 className="mb-1 text-2xl font-extrabold tracking-tight">{t("sections.priorities")}</h2>
        <p className="mb-5 text-sm text-muted">{t("h.priorities")}</p>
        <PrioritySliders value={prio} onChange={setPriorities} />
      </Card>

      <div className="flex justify-end">
        <Button size="lg" onClick={submit}>
          {t("submit")} <ArrowRight size={16} aria-hidden />
        </Button>
      </div>
    </Container>
  );
}
