// Conversion COP/USDT con una tasa fija de visualizacion (DEMO_TRM).
export const DEMO_TRM = 4000;

export function copToUsdt(cop: number, trm: number = DEMO_TRM): number {
  return cop / trm;
}

export function usdtToCop(usdt: number, trm: number = DEMO_TRM): number {
  return usdt * trm;
}
