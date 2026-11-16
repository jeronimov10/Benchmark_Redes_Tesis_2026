"""Recolecta una muestra reducida de bloques, recibos y logs de Tempo desde su JSON-RPC publico (resultados/raw/tempo)."""
import json
import os
import time
import urllib.request
import statistics as st

RPC = "https://rpc.tempo.xyz"
OUT_RAW = "resultados/raw/tempo"
N_BLOCKS = int(os.environ.get("N_BLOCKS_TEMPO", 700))


def rpc_batch(calls):
    body = json.dumps([
        {"jsonrpc": "2.0", "id": i, "method": m, "params": p}
        for i, (m, p) in enumerate(calls)
    ]).encode()
    req = urllib.request.Request(
        RPC, data=body, headers={"Content-Type": "application/json", "User-Agent": "bench/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.loads(r.read())
    raw.sort(key=lambda x: x["id"])
    return [x.get("result") for x in raw]


def rpc_one(method, params):
    return rpc_batch([(method, params)])[0]


def main():
    head_hex = rpc_one("eth_blockNumber", [])
    head = int(head_hex, 16)
    start = head - N_BLOCKS + 1
    print(f"Tempo: bloque actual {head}, muestreando [{start}, {head}]")

    blocks = []
    CHUNK = 25
    nums = list(range(start, head + 1))
    for i in range(0, len(nums), CHUNK):
        chunk = nums[i : i + CHUNK]
        calls = [("eth_getBlockByNumber", [hex(n), True]) for n in chunk]
        results = rpc_batch(calls)
        blocks.extend(results)
        time.sleep(0.3)
    blocks = [b for b in blocks if b]
    print(f"Bloques obtenidos: {len(blocks)}")

    with open(f"{OUT_RAW}/blocks_sample.json", "w") as f:
        json.dump(blocks, f)

    tx_hashes = []
    for b in blocks:
        for tx in b.get("transactions", []):
            if isinstance(tx, dict):
                tx_hashes.append(tx["hash"])
    print(f"Transacciones en la muestra: {len(tx_hashes)}")

    receipts = []
    for i in range(0, len(tx_hashes), CHUNK):
        chunk = tx_hashes[i : i + CHUNK]
        calls = [("eth_getTransactionReceipt", [h]) for h in chunk]
        results = rpc_batch(calls)
        receipts.extend(results)
        time.sleep(0.3)
    receipts = [r for r in receipts if r]

    with open(f"{OUT_RAW}/receipts_sample.json", "w") as f:
        json.dump(receipts, f)

    fee_tokens = sorted({r["feeToken"] for r in receipts if r.get("feeToken")})
    token_meta = {}
    for addr in fee_tokens:
        try:
            dec_hex = rpc_one("eth_call", [{"to": addr, "data": "0x313ce567"}, "latest"])
            decimals = int(dec_hex, 16) if dec_hex else None
        except Exception as e:
            decimals = None
        token_meta[addr] = {"decimals": decimals}
        time.sleep(0.2)

    with open(f"{OUT_RAW}/fee_token_meta.json", "w") as f:
        json.dump(token_meta, f, indent=2)

    print("Metadatos de feeToken:", token_meta)

    V2 = "0xCCCCCCCC00000000000000000000000000000001"
    try:
        from Crypto.Hash import keccak

        def selector(sig):
            h = keccak.new(digest_bits=256)
            h.update(sig.encode())
            return "0x" + h.hexdigest()[:8]

        sel = selector("getActiveValidators()")
        raw = rpc_one("eth_call", [{"to": V2, "data": sel}, "latest"])
        data = raw[2:]
        n_activos = int(data[64:128], 16)
    except Exception as e:
        n_activos = None
        print("No se pudo leer ValidatorConfigV2:", e)

    with open(f"{OUT_RAW}/validator_config.json", "w") as f:
        json.dump({"validator_config_v2_address": V2, "n_activos": n_activos}, f, indent=2)
    print("Validadores activos (ValidatorConfigV2):", n_activos)

    fork_schedule = rpc_batch([("tempo_forkSchedule", [])])[0]
    with open(f"{OUT_RAW}/fork_schedule.json", "w") as f:
        json.dump({"result": fork_schedule}, f, indent=2)
    print("Fork activo actual:", fork_schedule.get("active"))

    print("OK - crudo guardado en", OUT_RAW)


if __name__ == "__main__":
    main()
