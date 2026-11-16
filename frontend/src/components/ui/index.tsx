// Componentes de interfaz basicos: botones, tarjetas y contenedor.
"use client";

import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import type { Light } from "@/engine/types";

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

type Variant = "primary" | "secondary" | "accent" | "ghost";
type Size = "md" | "lg" | "sm";

const VARIANT: Record<Variant, string> = {
  primary: "bg-ink text-white border-ink hover:bg-black hover:border-black",
  secondary: "bg-transparent text-ink border-ink hover:bg-ink hover:text-white",
  accent: "bg-brand text-ink border-brand hover:bg-brand-deep hover:border-brand-deep",
  ghost: "bg-transparent text-ink border-transparent hover:bg-surface",
};
const SIZE: Record<Size, string> = {
  sm: "px-4 py-2 text-xs",
  md: "px-6 py-3 text-sm",
  lg: "px-8 py-4 text-base",
};
const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full border-[1.5px] font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-40";

export function buttonClass(variant: Variant = "primary", size: Size = "md", extra?: string) {
  return cx(BASE, VARIANT[variant], SIZE[size], extra);
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return <button className={buttonClass(variant, size, className)} {...props} />;
}

export function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  size?: Size;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={buttonClass(variant, size, className)}>
      {children}
    </Link>
  );
}

export function Card({
  className,
  children,
  tone = "white",
}: {
  className?: string;
  children?: ReactNode;
  tone?: "white" | "surface" | "yellow" | "ink";
}) {
  const tones = {
    white: "bg-paper border border-line/70 shadow-card",
    surface: "bg-surface",
    yellow: "bg-brand",
    ink: "bg-ink text-white",
  };
  return <div className={cx("rounded-card p-6 sm:p-8", tones[tone], className)}>{children}</div>;
}

export function Container({ children, className }: { children?: ReactNode; className?: string }) {
  return <div className={cx("mx-auto w-full max-w-6xl px-5 sm:px-8", className)}>{children}</div>;
}

export function SectionTitle({
  children,
  sub,
  eyebrow,
}: {
  children: ReactNode;
  sub?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-8">
      {eyebrow && (
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-muted">{eyebrow}</p>
      )}
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{children}</h1>
      {sub && <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted">{sub}</p>}
    </div>
  );
}

export function DemoBadge({ className }: { className?: string }) {
  const t = useTranslations("common");
  return (
    <span
      className={cx(
        "inline-block rounded-full bg-brand px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-ink",
        className,
      )}
    >
      {t("demo")}
    </span>
  );
}

const DOT: Record<Light, string> = {
  green: "bg-light-green",
  yellow: "bg-light-yellow",
  red: "bg-light-red",
};
const DOT_SIZE = { xs: "h-2.5 w-2.5", sm: "h-3.5 w-3.5", md: "h-5 w-5", lg: "h-8 w-8" } as const;

export function Semaphore({
  light,
  size = "md",
  ring,
}: {
  light: Light;
  size?: keyof typeof DOT_SIZE;
  ring?: boolean;
}) {
  const t = useTranslations("risk.light");
  return (
    <span
      role="img"
      aria-label={t(light)}
      title={t(`${light}Hint`)}
      className={cx(
        "inline-block shrink-0 rounded-full",
        DOT[light],
        DOT_SIZE[size],
        ring && "ring-4 ring-black/10",
      )}
    />
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="mb-8 min-w-0 last:mb-0">
      <legend className="mb-1 text-base font-bold">{label}</legend>
      {hint && <p className="mb-3 text-sm text-muted">{hint}</p>}
      {!hint && <div className="mb-2" />}
      {children}
      {error && (
        <p role="alert" className="mt-2 text-sm font-semibold text-bad">
          {error}
        </p>
      )}
    </fieldset>
  );
}

export function Choice({
  selected,
  onClick,
  title,
  desc,
  multi,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  desc?: string;
  multi?: boolean;
}) {
  return (
    <button
      type="button"
      role={multi ? "checkbox" : "radio"}
      aria-checked={selected}
      onClick={onClick}
      className={cx(
        "relative flex items-start gap-3 rounded-2xl border-[1.5px] px-4 py-3.5 text-left transition-all",
        selected
          ? "border-ink bg-brand-soft shadow-card"
          : "border-line bg-paper hover:border-ink/60 hover:bg-surface",
      )}
    >
      <span
        aria-hidden
        className={cx(
          "mt-0.5 grid h-5 w-5 shrink-0 place-items-center border-[1.5px]",
          multi ? "rounded-md" : "rounded-full",
          selected ? "border-ink bg-ink text-white" : "border-grey bg-paper",
        )}
      >
        {selected && <Check size={12} strokeWidth={3.5} />}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-bold">{title}</span>
        {desc && <span className="mt-0.5 block text-xs leading-snug text-muted">{desc}</span>}
      </span>
    </button>
  );
}

export function ChoiceGrid({ children, cols = 2 }: { children: ReactNode; cols?: 2 | 3 | 4 }) {
  const grid = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4" }[cols];
  return <div className={cx("grid grid-cols-1 gap-3", grid)}>{children}</div>;
}

export function Chip({
  selected,
  onClick,
  children,
  radio,
}: {
  selected: boolean;
  onClick: () => void;
  children: ReactNode;
  radio?: boolean;
}) {
  return (
    <button
      type="button"
      role={radio ? "radio" : "checkbox"}
      aria-checked={selected}
      onClick={onClick}
      className={cx(
        "rounded-full border-[1.5px] px-4 py-2 text-sm font-semibold transition-colors",
        selected ? "border-ink bg-ink text-white" : "border-line bg-paper hover:border-ink/60",
      )}
    >
      {children}
    </button>
  );
}

export const inputClass =
  "w-full rounded-xl border-[1.5px] border-line bg-paper px-4 py-3 text-base transition-colors placeholder:text-grey focus:border-ink";

export function ProgressBar({ value }: { value: number }) {
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-line/60"
      role="progressbar"
      aria-valuenow={Math.round(value * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-brand transition-all duration-500"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  );
}
