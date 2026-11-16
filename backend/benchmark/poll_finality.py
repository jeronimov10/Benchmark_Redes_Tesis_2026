"""Sondeo en vivo de la finalidad (B2) de Tempo y Aptos: registra el instante en que cada altura pasa a finalizada; pensado para correr horas en segundo plano."""
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
