import { z } from "zod";
import { callModel } from "@/modelo/servidor";

/**
 * Bridge to the recommendation model of the thesis (modelo/modelo.py).
 *   GET  -> networks with a measured profile and the date of the measurement.
 *   POST -> { accion: "recomendar" | "interpretar", ...parameters of modelo.recomendar() }
 */

const REPLICAS = 10_000;

const Entrada = z.object({
  monto_cop: z.number().positive().max(1e13),
  transfronterizo: z.boolean(),
  espera_s: z.number().positive().max(1e7),
  irrevocabilidad: z.enum(["baja", "media", "alta"]),
  trm: z.number().positive().max(1e6),
});

const Peticion = z.discriminatedUnion("accion", [
  Entrada.extend({ accion: z.literal("recomendar") }),
  Entrada.extend({ accion: z.literal("interpretar") }),
]);

function failure(e: unknown) {
  console.error("[api/modelo]", e);
  return Response.json({ error: e instanceof Error ? e.message : String(e) }, { status: 500 });
}

export async function GET() {
  try {
    return Response.json(await callModel({ accion: "info" }));
  } catch (e) {
    return failure(e);
  }
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "invalid JSON" }, { status: 400 });
  }
  const parsed = Peticion.safeParse(body);
  if (!parsed.success) return Response.json({ error: z.prettifyError(parsed.error) }, { status: 400 });

  const p = parsed.data;
  try {
    return Response.json(await callModel(p.accion === "recomendar" ? { ...p, replicas: REPLICAS } : p));
  } catch (e) {
    return failure(e);
  }
}
