import type { Weights } from "@/engine/types";

/** Encode priorities as a query string so the detail page shows the same ranking. */
export function priorityQuery(p: Weights): string {
  return `p=${Math.round(p.cost * 100)},${Math.round(p.speed * 100)},${Math.round(p.security * 100)}`;
}

export function parsePriorities(raw: string | null): Weights | null {
  if (!raw) return null;
  const parts = raw.split(",").map(Number);
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n) || n < 0)) return null;
  return { cost: parts[0] / 100, speed: parts[1] / 100, security: parts[2] / 100 };
}
