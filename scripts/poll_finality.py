"""Sondeador de finalidad en vivo para B2 (tau_F - tau_1) en Tempo y Aptos.

NO reconstruible desde el historico: ninguna de las dos redes deja un evento
posterior que registre cuando un bloque paso a ser 'finalizado'. Este script
implementa el mecanismo tal como lo exige la Sec.7.1 del plan (ventana W_L,
sondeo <=100ms, reloj del observador registrado), pero esta pensado para
correr HORAS (72h en el plan completo) en un proceso de fondo dedicado, no
dentro de una sesion interactiva corta.

Uso:
    python poll_finality.py tempo   --minutes 5 --interval-ms 100
    python poll_finality.py aptos   --minutes 5 --interval-ms 100

Salida: resultados/raw/<red>/finality_samples.jsonl, una linea por bloque
recien finalizado, con:
    numero_bloque, timestamp_red (tau_1), timestamp_observador_utc (tau_F
    aproximado -- el instante en que ESTE observador vio el cambio, no el
    instante exacto de finalizacion en la red), delta_s, deriva_reloj_nota.

Limitacion declarada: tau_F medido asi es "cuando este observador se entero",
no el instante exacto en que la red considero el bloque final -- el plan
exige registrar la deriva del reloj del observador precisamente porque esta
aproximacion es inevitable al sondear desde afuera. No se puede eliminar el
sesgo de sondeo (polling lag), solo acotarlo con un intervalo pequeno.
"""
import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone

TEMPO_RPC = "https://rpc.tempo.xyz"
APTOS_REST = "https://api.mainnet.aptoslabs.com/v1"


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(TEMPO_RPC, data=body, headers={"Content-Type": "application/json", "User-Agent": "bench/1.0"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["result"]


def get(path):
    req = urllib.request.Request(APTOS_REST + path, headers={"User-Agent": "bench/1.0"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def poll_tempo(minutes, interval_ms, out_path):
    end = time.time() + minutes * 60
    last_finalized = None
    n = 0
    with open(out_path, "w") as f:
        while time.time() < end:
            t_obs = datetime.now(timezone.utc)
            try:
                block = rpc("eth_getBlockByNumber", ["finalized", False])
            except Exception:
                time.sleep(interval_ms / 1000)
                continue
            num = int(block["number"], 16)
            if num != last_finalized:
                tau_1 = int(block["timestamp"], 16) + int(block.get("timestampMillisPart", "0x0"), 16) / 1000.0
                tau_f = t_obs.timestamp()
                rec = dict(
                    numero_bloque=num,
                    tau_1_timestamp_red=tau_1,
                    tau_f_timestamp_observador=tau_f,
                    delta_s=tau_f - tau_1,
                    reloj_observador_utc=t_obs.isoformat(),
                )
                f.write(json.dumps(rec) + "\n")
                f.flush()
                last_finalized = num
                n += 1
            time.sleep(interval_ms / 1000)
    print(f"Tempo: {n} transiciones de finalidad observadas en {minutes} min")


def poll_aptos(minutes, interval_ms, out_path):
    end = time.time() + minutes * 60
    last_height = None
    n = 0
    with open(out_path, "w") as f:
        while time.time() < end:
            t_obs = datetime.now(timezone.utc)
            try:
                info = get("")
            except Exception:
                time.sleep(interval_ms / 1000)
                continue
            height = int(info["block_height"])
            if height != last_height:
                # tau_1 real exige leer el bloque para su block_timestamp;
                # se hace solo en la transicion, no en cada tick, para no
                # multiplicar peticiones y disparar rate limit.
                try:
                    b = get(f"/blocks/by_height/{height}")
                    tau_1 = int(b["block_timestamp"]) / 1e6
                except Exception:
                    tau_1 = None
                tau_f = t_obs.timestamp()
                rec = dict(
                    altura=height,
                    tau_1_timestamp_red=tau_1,
                    tau_f_timestamp_observador=tau_f,
                    delta_s=(tau_f - tau_1) if tau_1 else None,
                    reloj_observador_utc=t_obs.isoformat(),
                )
                f.write(json.dumps(rec) + "\n")
                f.flush()
                last_height = height
                n += 1
            time.sleep(interval_ms / 1000)
    print(f"Aptos: {n} nuevas alturas observadas en {minutes} min")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("red", choices=["tempo", "aptos"])
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--interval-ms", type=int, default=100)
    args = ap.parse_args()

    out = f"resultados/raw/{args.red}/finality_samples.jsonl"
    if args.red == "tempo":
        poll_tempo(args.minutes, args.interval_ms, out)
    else:
        poll_aptos(args.minutes, args.interval_ms, out)
