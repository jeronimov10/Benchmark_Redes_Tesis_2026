"use client";

import { useTranslations } from "next-intl";
import { Choice, ChoiceGrid, Field } from "@/components/ui";
import { IRR_OPTIONS, WAIT_OPTIONS } from "@/lib/attrs";
import type { Irreversibility } from "@/engine/types";

const irrKey = (v: Irreversibility) => (v === 0.5 ? "half" : String(v));

/** The two attributes the user chooses directly: tolerable wait and required irreversibility. */
export function PaymentAttributes({
  waitSec,
  irreversibility,
  onChange,
}: {
  waitSec: number;
  irreversibility: Irreversibility;
  onChange: (next: { waitSec?: number; irreversibility?: Irreversibility }) => void;
}) {
  const t = useTranslations("tx");
  return (
    <>
      <Field label={t("q.wait")}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {WAIT_OPTIONS.map((w) => (
            <Choice
              key={w}
              selected={waitSec === w}
              onClick={() => onChange({ waitSec: w })}
              title={t(`wait.${w}`)}
              desc={t(`wait.${w}_d`)}
            />
          ))}
        </div>
      </Field>
      <Field label={t("q.irreversibility")}>
        <ChoiceGrid cols={3}>
          {IRR_OPTIONS.map((v) => (
            <Choice
              key={v}
              selected={irreversibility === v}
              onClick={() => onChange({ irreversibility: v })}
              title={t(`irr.${irrKey(v)}`)}
              desc={t(`irr.${irrKey(v)}_d`)}
            />
          ))}
        </ChoiceGrid>
      </Field>
    </>
  );
}
