"""Colector real Aptos contra api.mainnet.aptoslabs.com/v1.
Muestra reducida, n declarado explicitamente, no la ventana de 14 dias completa.
"""
import json
import time
import urllib.request

BASE = "https://api.mainnet.aptoslabs.com/v1"
OUT_RAW = "resultados/raw/aptos"
N_BLOCKS = 350


def get(path, retries=8):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "bench/1.0"})
    delay = 5.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 1.6
                continue
            raise


def main():
    info = get("")
    head = int(info["block_height"])
    start = head - N_BLOCKS + 1
    print(f"Aptos: bloque actual {head}, muestreando [{start}, {head}]")

    blocks = []
    for h in range(start, head + 1):
        try:
            b = get(f"/blocks/by_height/{h}?with_transactions=true")
            blocks.append(b)
        except Exception as e:
            print("error bloque", h, e)
        time.sleep(1.2)

    with open(f"{OUT_RAW}/blocks_sample.json", "w") as f:
        json.dump(blocks, f)
    print(f"Bloques obtenidos: {len(blocks)}")

    validator_set = get("/accounts/0x1/resource/0x1::stake::ValidatorSet")
    with open(f"{OUT_RAW}/validator_set.json", "w") as f:
        json.dump(validator_set, f, indent=2)
    n_val = len(validator_set["data"]["active_validators"])
    print(f"Validadores activos: {n_val}")

    txn_limits = get("/accounts/0x1/resource/0x1::transaction_limits::TxnLimitsConfig")
    with open(f"{OUT_RAW}/txn_limits_config.json", "w") as f:
        json.dump(txn_limits, f, indent=2)

    print("OK - crudo guardado en", OUT_RAW)


if __name__ == "__main__":
    main()
