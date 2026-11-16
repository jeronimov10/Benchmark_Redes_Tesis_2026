// Catalogo de metricas y bloques A-D para mostrar en la interfaz.
import type { BlockId, MetricMeta } from "./types";

export const METRICS: MetricMeta[] = [
  { id: "A1", block: "A", unit: "fraction", source: "chain" },
  { id: "A2", block: "A", unit: "ratio", source: "chain" },
  { id: "A3", block: "A", unit: "index", source: "chain" },
  { id: "A4", block: "A", unit: "usd", source: "chain" },
  { id: "B1", block: "B", unit: "seconds", source: "chain" },
  { id: "B2", block: "B", unit: "seconds", source: "chain" },
  { id: "B2b", block: "B", unit: "seconds", source: "chain" },
  { id: "B3", block: "B", unit: "ratio", source: "chain" },
  { id: "C1", block: "C", unit: "index", source: "chain" },
  { id: "C2", block: "C", unit: "count", source: "chain" },
  { id: "C3", block: "C", unit: "percent", source: "chain" },
  { id: "C4", block: "C", unit: "percent", source: "chain" },
  { id: "C5", block: "C", unit: "count", source: "chain" },
  { id: "D1", block: "D", unit: "percent", source: "chain" },
  { id: "D2", block: "D", unit: "percent", source: "chain" },
  { id: "D3", block: "D", unit: "percent", source: "chain" },
];

export const BLOCKS: BlockId[] = ["A", "B", "C", "D"];
