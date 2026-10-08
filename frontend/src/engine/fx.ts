/** Demo exchange rate, COP per USDT. Fixed on purpose: no live data in this prototype. */
export const DEMO_TRM = 4000;

export function copToUsdt(cop: number, trm: number = DEMO_TRM): number {
  return cop / trm;
}

export function usdtToCop(usdt: number, trm: number = DEMO_TRM): number {
  return usdt * trm;
}
