"""Colector real Aptos contra api.mainnet.aptoslabs.com/v1.
Muestra reducida, n declarado explicitamente, no la ventana de 14 dias completa.

Limite del API: sin clave, 40.000 unidades de computo por 300 s y por IP (medido: un bloque con transacciones pesa ~127 KB y cuesta ~2.200
unidades, asi que solo caben ~18 bloques por ventana de 5 min). Por eso la muestra por defecto es de 40 bloques y el colector espera a que
se libere la ventana en vez de martillar el API. Con APTOS_API_KEY (clave gratuita de Aptos Build/Geomi) el limite sube y N_BLOCKS_APTOS
puede aumentarse (p. ej. 350).
"""
import json
import os
import socket
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = "https://api.mainnet.aptoslabs.com/v1"
OUT_RAW = "resultados/raw/aptos"
API_KEY = os.environ.get("APTOS_API_KEY", "")
N_BLOCKS = int(os.environ.get("N_BLOCKS_APTOS", 350 if API_KEY else 40))
WORKERS = int(os.environ.get("APTOS_WORKERS", 8 if API_KEY else 2))
UNIDADES_POR_BLOQUE = 2200
UNIDADES_POR_SEGUNDO = 40000 / 300

# Pyth en Aptos. Direccion del paquete confirmada por sesiones anteriores
# (docs.pyth.network/price-feeds/contract-addresses/aptos). El ID de 32 bytes
# del feed APT/USD se verifico EN VIVO en esta sesion contra la propia API de
# Pyth (hermes.pyth.network/v2/price_feeds?query=APT), no se adivino ni se
# tomo de memoria (ver CLAUDE.md/limitaciones.md sobre el intento fallido
# anterior). El handle de la tabla sale de leer el resource state::LatestPriceInfo
# de la cuenta -- ambos son identificadores, no valores; el VALOR (precio) sale
# de una consulta de tabla en vivo abajo.
PYTH_ACCOUNT = "0x7e783b349d3e89cf5931af376ebeadbfab855b3fa239b7ada8f5a92fbea6b387"
PYTH_APT_USD_FEED_ID = "0x03ae4db29ed4ae33d323568895aa00337e658e348b37509f5372ae51f0af00d5"


def _abrir(req, retries):
    delay = 3.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
            espera = float(e.headers.get("Retry-After") or delay) if e.code == 429 else delay
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            if attempt == retries - 1:
                raise
            espera = delay
        time.sleep(espera)
        delay = min(delay * 1.5, 40.0)


def _cabeceras(extra=None):
    h = {"User-Agent": "bench/1.0", **(extra or {})}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


def get(path, retries=30):
    return _abrir(urllib.request.Request(BASE + path, headers=_cabeceras()), retries)


def post(path, payload, retries=30):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers=_cabeceras({"Content-Type": "application/json"}))
    return _abrir(req, retries)


def bajar_bloque(h):
    try:
        return get(f"/blocks/by_height/{h}?with_transactions=true")
    except Exception as e:
        print("error bloque", h, e)
        return None


def resolver_store(s):
    try:
        return s, get(f"/accounts/{s}/resource/0x1::fungible_asset::FungibleStore")["data"]["metadata"]["inner"]
    except Exception:
        return s, None


def main():
    info = get("")
    head = int(info["block_height"])
    start = head - N_BLOCKS + 1
    print(f"Aptos: bloque actual {head}, muestreando [{start}, {head}]")

    if not API_KEY:
        minutos = N_BLOCKS * UNIDADES_POR_BLOQUE / UNIDADES_POR_SEGUNDO / 60
        print(f"Sin APTOS_API_KEY: limite anonimo de 40.000 unidades/300 s; {N_BLOCKS} bloques tardan ~{minutos:.0f} min "
              f"(con clave gratuita el limite sube y no hay espera)")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        blocks = [b for b in ex.map(bajar_bloque, range(start, head + 1)) if b]
    print(f"{len(blocks)} bloques en {time.time() - t0:.1f} s con {WORKERS} hilos")

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

    # --- limite de gas de bloque: blob BCS opaco, decodificado en compute_aptos_metrics.py
    # contra el layout EXACTO de OnChainExecutionConfig confirmado leyendo
    # types/src/on_chain_config/execution_config.rs en aptos-labs/aptos-core (codigo
    # fuente publico) -- no se adivina el layout, se verifica byte a byte (ver
    # compute_aptos_metrics.py:decode_execution_config).
    execution_config = get("/accounts/0x1/resource/0x1::execution_config::ExecutionConfig")
    with open(f"{OUT_RAW}/execution_config.json", "w") as f:
        json.dump(execution_config, f, indent=2)

    # --- D3: resolver el activo subyacente de cada `store` que aparece en eventos
    # 0x1::fungible_asset::Deposit/Withdraw de la muestra. El evento solo trae la
    # direccion del store (objeto), no el activo; se resuelve leyendo el resource
    # FungibleStore.metadata de cada store distinto visto (n pequeno, ver abajo).
    stores = set()
    for b in blocks:
        for tx in b.get("transactions", []):
            if tx.get("type") != "user_transaction":
                continue
            for ev in tx.get("events", []):
                if ev.get("type") in ("0x1::fungible_asset::Deposit", "0x1::fungible_asset::Withdraw"):
                    s = ev.get("data", {}).get("store")
                    if s:
                        stores.add(s)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        store_to_asset = dict(ex.map(resolver_store, sorted(stores)))
    with open(f"{OUT_RAW}/fa_store_to_asset.json", "w") as f:
        json.dump(store_to_asset, f, indent=2)
    print(f"Stores de Fungible Asset resueltos: {len(store_to_asset)}")

    # --- Precio APT/USD de Pyth (congelado desde 2026-08-26, ver nota arriba) ---
    # Tabla Table<PriceIdentifier, PriceInfo> confirmada leyendo el resource
    # state::LatestPriceInfo; el item se consulta con el feed ID verificado.
    try:
        latest = get(f"/accounts/{PYTH_ACCOUNT}/resource/{PYTH_ACCOUNT}::state::LatestPriceInfo")
        handle = latest["data"]["info"]["handle"]
        item = post(
            f"/tables/{handle}/item",
            {
                "key_type": f"{PYTH_ACCOUNT}::price_identifier::PriceIdentifier",
                "value_type": f"{PYTH_ACCOUNT}::price_info::PriceInfo",
                "key": {"bytes": PYTH_APT_USD_FEED_ID},
            },
        )
        with open(f"{OUT_RAW}/pyth_apt_usd_price.json", "w") as f:
            json.dump({"feed_id": PYTH_APT_USD_FEED_ID, "table_handle": handle, "price_info": item}, f, indent=2)
        print("Precio Pyth APT/USD (congelado):", item["price_feed"]["price"])
    except Exception as e:
        print("No se pudo leer el precio de Pyth:", e)

    print("OK - crudo guardado en", OUT_RAW)


if __name__ == "__main__":
    main()
