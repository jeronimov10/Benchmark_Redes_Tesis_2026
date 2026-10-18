import { spawn } from "node:child_process";
import path from "node:path";

/**
 * Server side only. Runs servicio_modelo/recomendar.py as a child process: the
 * Node event loop stays free while Python computes (about 1 s with 10.000 replicas).
 *
 * MODELO_PYTHON and MODELO_SCRIPT override the interpreter and the script path.
 */
const PYTHON = process.env.MODELO_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const SCRIPT =
  process.env.MODELO_SCRIPT ?? path.resolve(process.cwd(), "..", "servicio_modelo", "recomendar.py");
const TIMEOUT_MS = 60_000;
const MAX_PARALLEL = 4;
const MAX_CACHE = 500;

function runPython(request: object): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, [SCRIPT], {
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      windowsHide: true,
    });
    let out = "";
    let err = "";
    const timer = setTimeout(() => child.kill(), TIMEOUT_MS);
    child.stdout.setEncoding("utf8").on("data", (d: string) => (out += d));
    child.stderr.setEncoding("utf8").on("data", (d: string) => (err += d));
    child.on("error", (e) => {
      clearTimeout(timer);
      reject(new Error(`cannot start ${PYTHON}: ${e.message}`));
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      let parsed: unknown;
      try {
        parsed = JSON.parse(out);
      } catch {
        reject(new Error(`model exited with ${code}: ${err || out}`.trim()));
        return;
      }
      if (code === 0) resolve(parsed);
      else reject(new Error((parsed as { error?: string }).error ?? `model exited with ${code}`));
    });
    child.stdin.end(JSON.stringify(request));
  });
}

/* A few runs at a time: each one uses a full CPU core for about a second. */
let active = 0;
const queue: (() => void)[] = [];

async function withSlot<T>(fn: () => Promise<T>): Promise<T> {
  if (active >= MAX_PARALLEL) await new Promise<void>((r) => queue.push(r));
  active++;
  try {
    return await fn();
  } finally {
    active--;
    queue.shift()?.();
  }
}

/* The model is deterministic (random.Random(42)), so equal inputs give equal outputs. */
const cache = new Map<string, Promise<unknown>>();

export function callModel(request: object): Promise<unknown> {
  const key = JSON.stringify(request);
  const hit = cache.get(key);
  if (hit) return hit;
  const p = withSlot(() => runPython(request));
  cache.set(key, p);
  p.catch(() => cache.delete(key));
  if (cache.size > MAX_CACHE) cache.delete(cache.keys().next().value as string);
  return p;
}
