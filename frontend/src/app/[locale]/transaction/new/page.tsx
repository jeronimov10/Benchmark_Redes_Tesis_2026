// Pagina del asistente para describir un pago nuevo.
"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeftRight, ArrowRight } from "lucide-react";
import { z } from "zod";
import { Button, Card, Chip, Choice, ChoiceGrid, Container, Field, inputClass, SectionTitle } from "@/components/ui";
import { PaymentAttributes } from "@/components/result/PaymentAttributes";
import { copToUsdt, DEMO_TRM } from "@/engine/fx";
import { useRouter } from "@/i18n/navigation";
import { defaultsFor } from "@/lib/attrs";
import { networkLabel, useFmt } from "@/lib/format";
import { useDebounced, useEntrada, useInfoModelo, useInterpretacion } from "@/modelo/cliente";
import { entradaModelo, escenarioDominante } from "@/modelo/entrada";
import { useRequireUser } from "@/lib/useRequireUser";
import { actions } from "@/state/store";
import {
  type Irreversibility,
  type NetworkId,
  type Purpose,
  type RecipientType,
  type TxInput,
} from "@/engine/types";

const PURPOSES: Purpose[] = ["p2p", "commerce", "remittance", "payroll", "treasury"];
const RECIPIENTS: RecipientType[] = ["person", "business", "exchange", "ownWallet", "unknown"];
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
  const [attrs, setAttrs] = useState<{ waitSec: number; irreversibility: Irreversibility } | null>(null);
  const [rType, setRType] = useState<RecipientType>("person");
  const [rCountry, setRCountry] = useState("CO");
  const [firstTime, setFirstTime] = useState(false);
  const [needsMemo, setNeedsMemo] = useState<boolean | null>(null);
  const [accepted, setAccepted] = useState<NetworkId[] | "unknown">("unknown");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const amountCop = Number(amount.replace(/\D/g, "")) || 0;
  const originCountry = user?.answers.country ?? "CO";
  const crossBorder = rCountry !== originCountry;
  const preset = defaultsFor(purpose, user?.answers ?? { timeTolerance: "medium", riskTolerance: "medium" });
  const current = attrs ?? preset;
  const memo = needsMemo ?? user?.answers.needsReconciliation ?? false;

  const previewKey = useDebounced(
    amountCop >= 1 ? `${amountCop}|${rCountry}|${current.waitSec}|${current.irreversibility}` : "",
    300,
  );
  const [pAmount, pCountry, pWait, pIrr] = previewKey.split("|");
  const preview = useInterpretacion(
    useEntrada(
      previewKey
        ? entradaModelo(
            {
              amountCop: Number(pAmount),
              waitSec: Number(pWait),
              irreversibility: Number(pIrr) as Irreversibility,
              recipient: { country: pCountry },
            },
            originCountry,
          )
        : null,
    ),
  );
  const similar = amountCop >= 1 && preview.data ? escenarioDominante(preview.data.composicion) : null;
  const info = useInfoModelo();

  const schema = useMemo(
    () =>
      z.object({
        amountCop: z.number().min(1, t("errors.amountMin")).max(MAX_COP, t("errors.amountMax")),
        accepted: z.union([z.literal("unknown"), z.array(z.string()).min(1, t("errors.accepted"))]),
      }),
    [t],
  );

  if (!ready || !user) return <Container className="py-12" />;

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
      waitSec: current.waitSec,
      irreversibility: current.irreversibility,
      recipient: { type: rType, country: rCountry, firstTime, accepted, needsMemo: memo },
    };
    actions.setDraft(tx);
    router.push("/transaction/analyzing");
  }

  const toggleNet = (id: NetworkId) => {
    const list = accepted === "unknown" ? [] : accepted;
    setAccepted(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  return (
    <Container className="max-w-3xl py-12">
      <SectionTitle sub={t("sub")}>{t("title")}</SectionTitle>

      <Card className="mb-5">
        <h2 className="mb-6 text-2xl font-extrabold tracking-tight">{t("sections.operation")}</h2>
        <Field label={t("q.amount")} hint={t("h.amount")} error={errors.amountCop}>
          <div className="relative">
            <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-sm font-extrabold text-muted">
              COP
            </span>
            <input
              inputMode="numeric"
              className={`${inputClass} pl-16 text-2xl font-extrabold`}
              value={amountCop ? new Intl.NumberFormat("es-CO").format(amountCop) : amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              aria-label={t("q.amount")}
            />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-2 font-semibold">
              <ArrowLeftRight size={14} aria-hidden />
              {fmt.usdt(copToUsdt(amountCop))}
            </span>
            <span className="text-xs text-muted">{t("trmNote", { trm: fmt.cop(DEMO_TRM) })}</span>
            {similar && (
              <span className="rounded-full bg-brand px-3.5 py-1.5 text-xs font-extrabold">
                {t("scenarioDetected", { scenario: ts(`${similar}.name`) })}
              </span>
            )}
          </div>
        </Field>

        <Field label={t("q.purpose")}>
          <ChoiceGrid cols={3}>
            {PURPOSES.map((p) => (
              <Choice
                key={p}
                selected={purpose === p}
                onClick={() => {
                  setPurpose(p);
                  setAttrs(null);
                }}
                title={to(`opt.purposes.${p}`)}
              />
            ))}
          </ChoiceGrid>
        </Field>
      </Card>

      <Card className="mb-5">
        <h2 className="mb-1 text-2xl font-extrabold tracking-tight">{t("sections.recipient")}</h2>
        <p className="mb-6 text-sm text-muted">{t("originNote", { country: fmt.country(originCountry) })}</p>
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
          <p className="mt-2 text-sm font-semibold">
            {t("crossBorder.label")}: <span className="font-normal text-muted">{crossBorder ? t("crossBorder.yes") : t("crossBorder.no")}</span>
          </p>
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
            {(info?.redes ?? []).map((red) => {
              const id = red as NetworkId;
              return (
                <Chip key={id} selected={accepted !== "unknown" && accepted.includes(id)} onClick={() => toggleNet(id)}>
                  {networkLabel(id)}
                </Chip>
              );
            })}
          </div>
        </Field>
        <Field label={t("q.needsMemo")} hint={t("h.needsMemo")}>
          <ChoiceGrid cols={2}>
            <Choice selected={memo} onClick={() => setNeedsMemo(true)} title={to("yes")} />
            <Choice selected={!memo} onClick={() => setNeedsMemo(false)} title={to("no")} />
          </ChoiceGrid>
        </Field>
      </Card>

      <Card className="mb-8">
        <h2 className="mb-1 text-2xl font-extrabold tracking-tight">{t("sections.attributes")}</h2>
        <p className="mb-6 text-sm text-muted">{t("h.attributes")}</p>
        <PaymentAttributes
          waitSec={current.waitSec}
          irreversibility={current.irreversibility}
          onChange={(next) => setAttrs({ ...current, ...next })}
        />
      </Card>

      <div className="flex justify-end">
        <Button size="lg" onClick={submit}>
          {t("submit")} <ArrowRight size={18} aria-hidden />
        </Button>
      </div>
    </Container>
  );
}
