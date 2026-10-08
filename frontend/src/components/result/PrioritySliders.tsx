"use client";

import { useTranslations } from "next-intl";
import { Chip } from "@/components/ui";
import { defaultPriorities } from "@/engine/scoring";
import type { PriorityKey, Weights } from "@/engine/types";

const AXES = ["cost", "speed", "security"] as const;
const PRESETS: PriorityKey[] = ["cost", "speed", "security", "balanced"];

function close(a: Weights, b: Weights) {
  return AXES.every((k) => Math.abs(a[k] - b[k]) < 0.01);
}

/** Three independent sliders (0-100); the engine normalizes them, the UI shows the resulting share. */
export function PrioritySliders({
  value,
  onChange,
}: {
  value: Weights;
  onChange: (w: Weights) => void;
}) {
  const t = useTranslations("priorities");
  const sum = value.cost + value.speed + value.security || 1;

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="radiogroup">
        {PRESETS.map((p) => (
          <Chip key={p} radio selected={close(value, defaultPriorities(p))} onClick={() => onChange(defaultPriorities(p))}>
            {t(`preset.${p}`)}
          </Chip>
        ))}
      </div>
      <div className="mt-6 grid gap-6 md:grid-cols-3">
        {AXES.map((axis) => (
          <label key={axis} className="block rounded-2xl bg-surface p-5">
            <span className="mb-3 flex items-baseline justify-between">
              <span className="font-extrabold">{t(`axis.${axis}`)}</span>
              <span className="text-2xl font-extrabold tabular-nums">{Math.round((value[axis] / sum) * 100)}%</span>
            </span>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(value[axis] * 100)}
              onChange={(e) => onChange({ ...value, [axis]: Number(e.target.value) / 100 })}
              className="h-2 w-full cursor-pointer"
              aria-label={t(`axis.${axis}`)}
            />
            <span className="mt-3 block text-xs leading-snug text-muted">{t(`axisHint.${axis}`)}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
