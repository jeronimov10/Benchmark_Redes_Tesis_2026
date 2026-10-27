"""Pruebas de los colectores con transporte HTTP simulado (httpx.MockTransport): EVM (pagos en USDC, fallos, patrocinio, precio verificado),
Tempo, Aptos y Canton, mas el monitor (fallos registrados, sin ciclos solapados) y la continuidad incremental. No tocan la red real."""

import asyncio
import dataclasses
import json
import time

import httpx
import pytest

from app.container import Contenedor
from app.pipelines.collectors.precios import SEL_DECIMALES as SD, SEL_DESCRIPCION, SEL_ULTIMA_RONDA
from app.pipelines.processors.evm import TOPIC_TRANSFER
from app.services.analytics.continuidad import resumen_ciclo
from app.utils.keccak import selector
from conftest import REPO

RAW = REPO / "resultados" / "raw"
USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
SEL_AUTORIZACION = selector("transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)")


def abi_texto(t):
    b = t.encode()
    return "0x" + (32).to_bytes(32, "big").hex() + len(b).to_bytes(32, "big").hex() + b.ljust(32, bytes(1)).hex()


def palabra(n):
    return n.to_bytes(32, "big").hex()


def rpc_falso(metodos):
    def handler(req):
        cuerpo = json.loads(req.content)

        def uno(c):
            fn = metodos.get(c["method"])
            if fn is None:
                return {"jsonrpc": "2.0", "id": c["id"], "error": {"code": -32601, "message": "no existe"}}
            return {"jsonrpc": "2.0", "id": c["id"], "result": fn(c["params"])}

        return httpx.Response(200, json=[uno(c) for c in cuerpo] if isinstance(cuerpo, list) else uno(cuerpo))

    return handler


def contenedor(settings, handler, db, redes):
    cfg = dataclasses.replace(settings, redes_activas=tuple(redes), max_bloques_por_ciclo=5)
    return Contenedor(cfg, db=db, transporte_http=httpx.MockTransport(handler))


def correr(c):
    return asyncio.run(c)


def bloque_evm(n, txs, ts=1_790_000_000):
    return {"number": hex(n), "timestamp": hex(ts + n), "gasLimit": hex(30_000_000), "gasUsed": hex(15_000_000),
            "miner": "0xAbC" + str(n % 2) * 37, "transactions": txs}


def tx(h, to, entrada="0x", tipo="0x2"):
    return {"hash": h, "to": to, "input": entrada, "type": tipo}


def recibo(h, ok=True, transfer=False, gas=60_000, precio=30_000_000_000):
    logs = [{"address": USDC, "topics": [TOPIC_TRANSFER, "0x0", "0x0"], "data": "0x"}] if transfer else []
    return {"transactionHash": h, "status": "0x1" if ok else "0x0", "gasUsed": hex(gas), "effectiveGasPrice": hex(precio),
            "logs": logs}


def manejador_polygon(bloques, recibos, precio_chainlink=1.0, edad_precio=10):
    def eth_call(p):
        d = p[0]["data"]
        if d == SEL_DESCRIPCION:
            return abi_texto("MATIC / USD")
        if d == SD:
            return "0x" + palabra(6 if p[0]["to"].lower() == USDC.lower() else 8)
        if d == SEL_ULTIMA_RONDA:
            return ("0x" + palabra(1) + palabra(int(precio_chainlink * 1e8)) + palabra(0)
                    + palabra(int(time.time()) - edad_precio) + palabra(1))
        if d == selector("symbol()"):
            return abi_texto("USDC")
        return "0x" + palabra(6)

    return rpc_falso({
        "eth_blockNumber": lambda p: hex(max(bloques)),
        "eth_getBlockByNumber": lambda p: bloques[int(p[0], 16)],
        "eth_getLogs": lambda p: [{"transactionHash": h} for h, r in recibos.items() if r["logs"]],
        "eth_getTransactionReceipt": lambda p: recibos[p[0]],
        "eth_call": eth_call,
        "eth_getCode": lambda p: "0x6080",
        "eth_getStorageAt": lambda p: "0x" + "00" * 12 + "ab" * 20,
    })


def test_evm_pagos_usdc_fallos_patrocinio_y_precio(settings, db):
    recibos = {"0xa": recibo("0xa", transfer=True), "0xb": recibo("0xb", ok=False), "0xc": recibo("0xc")}
    bloques = {n: bloque_evm(n, [tx("0xa", USDC, SEL_AUTORIZACION), tx("0xb", USDC), tx("0xz", "0x" + "11" * 20)] if n == 12 else [])
               for n in range(8, 13)}
    c = contenedor(settings, manejador_polygon(bloques, recibos, precio_chainlink=2.0), db, ["polygon"])
    r = correr(c.colectores["polygon"].ciclo_bloques())
    assert (r["bloques"], r["pagos"], len(r["muestras"])) == (5, 2, 5)
    filas = {f["hash"]: f for f in c.repos["muestras"].txs_desde("polygon", 0)}
    assert set(filas) == {"0xa", "0xb"}
    assert filas["0xa"]["tiene_transfer"] == 1 and filas["0xa"]["patrocinada"] == 1 and filas["0xa"]["estado_ok"] == 1
    assert filas["0xa"]["fee_usd"] == pytest.approx(60_000 * 30e9 / 1e18 * 2.0)
    assert filas["0xb"]["estado_ok"] == 0 and filas["0xb"]["tiene_transfer"] == 0
    assert len(c.repos["muestras"].bloques_desde("polygon", 0)) == 5
    assert c.repos["estado"].ultima("polygon", "usdc_verificado")[0]["decimals"] == 6


def test_evm_precio_obsoleto_deja_fee_nulo_y_registra_fallo(settings, db):
    recibos = {"0xa": recibo("0xa", transfer=True)}
    bloques = {n: bloque_evm(n, [tx("0xa", USDC)] if n == 12 else []) for n in range(8, 13)}
    c = contenedor(settings, manejador_polygon(bloques, recibos, edad_precio=99999), db, ["polygon"])
    correr(c.colectores["polygon"].ciclo_bloques())
    assert c.repos["muestras"].txs_desde("polygon", 0)[0]["fee_usd"] is None
    fila = next(f for f in c.repos["salud"].todos() if f["componente"] == "precio")
    assert fila["fallos_consecutivos"] == 1 and "obsoleto" in fila["error"]


def test_evm_contrato_que_no_es_usdc_se_rechaza(settings, db):
    h = rpc_falso({"eth_call": lambda p: abi_texto("SCAM") if p[0]["data"] == selector("symbol()") else "0x" + palabra(6),
                   "eth_getCode": lambda p: "0x6080"})
    c = contenedor(settings, h, db, ["polygon"])
    with pytest.raises(Exception, match="no se verifica como USDC"):
        correr(c.colectores["polygon"].verificar())


def test_evm_lee_ranura_de_proxy(settings, db):
    bloques = {1: bloque_evm(1, [])}
    c = contenedor(settings, manejador_polygon(bloques, {}), db, ["polygon"])
    r = correr(c.colectores["polygon"].ciclo_estado())
    assert r["impl"] == "0x" + "ab" * 20
    assert c.repos["estado"].ultima("polygon", "proxy_impl")[0]["impl"] == r["impl"]


def test_tempo_bloques_recibos_y_finalidad(settings, db):
    ft = "0x20c0000000000000000000000000000000000001"
    bloques = {n: {"number": hex(n), "timestamp": hex(1_790_000_000), "timestampMillisPart": hex(n % 10 * 100),
                   "gasLimit": hex(500_000_000), "gasUsed": hex(1000),
                   "consensusContext": {"proposer": "0xAA" + str(n % 3) * 38},
                   "transactions": [{"hash": f"0x{n:x}t"}] if n == 12 else []} for n in range(8, 13)}
    rec = {"transactionHash": "0xct", "blockNumber": hex(12), "status": "0x1", "gasUsed": hex(100_000),
           "effectiveGasPrice": hex(20_000_000_000), "feeToken": ft, "feePayer": "0xsp",
           "logs": [{"address": ft, "topics": [TOPIC_TRANSFER]}, {"address": ft, "topics": [TOPIC_TRANSFER]}]}
    finalizados = iter([10, 10, 11])

    def bloque(p):
        if p[0] == "finalized":
            return {"number": hex(next(finalizados)), "timestamp": hex(int(time.time()) - 1),
                    "timestampMillisPart": hex(0), "transactions": []}
        return bloques[int(p[0], 16)]

    metodos = {
        "eth_blockNumber": lambda p: hex(12),
        "eth_getBlockByNumber": bloque,
        "eth_getTransactionReceipt": lambda p: {**rec, "transactionHash": p[0]},
        "eth_call": lambda p: "0x" + palabra(6),
    }
    c = contenedor(settings, rpc_falso(metodos), db, ["tempo"])
    col = c.colectores["tempo"]
    r = correr(col.ciclo_bloques())
    assert r["bloques"] == 5 and r["txs"] == 1
    fila = c.repos["muestras"].txs_desde("tempo", 0)[0]
    assert fila["fee_usd"] == pytest.approx(100_000 * 20e9 / 1e18) and fila["patrocinada"] == 1 and fila["multi_transfer"] == 1
    assert c.repos["muestras"].bloques_desde("tempo", 0)[0]["productor"].startswith("0xaa")
    assert [correr(col.ciclo_finalidad())["transiciones"] for _ in range(3)] == [0, 0, 1]
    fin = c.repos["muestras"].finalidad_desde("tempo", 0)
    assert len(fin) == 1 and 0.9 < fin[0]["delta_s"] < 5


@pytest.mark.skipif(not (RAW / "aptos" / "execution_config.json").exists(), reason="faltan datos crudos")
def test_aptos_bloques_estado_y_precio_congelado(settings, db):
    def cargar(r):
        return json.load(open(RAW / "aptos" / r, encoding="utf-8"))

    plantilla = cargar("blocks_sample.json")[100]
    pyth = cargar("pyth_apt_usd_price.json")

    def handler(req):
        ruta = req.url.path
        if ruta == "/v1" or ruta.endswith("/v1"):
            return httpx.Response(200, json={"block_height": "1031817300"})
        if "/blocks/by_height/" in ruta:
            h = int(ruta.rsplit("/", 1)[1])
            return httpx.Response(200, json={**plantilla, "block_height": str(h),
                                             "block_timestamp": str(1_790_000_000_000_000 + h * 20_000)})
        if ruta.endswith("ExecutionConfig"):
            return httpx.Response(200, json=cargar("execution_config.json"))
        if ruta.endswith("ValidatorSet"):
            return httpx.Response(200, json=cargar("validator_set.json"))
        if ruta.endswith("LatestPriceInfo"):
            return httpx.Response(200, json={"data": {"info": {"handle": "0xh"}}})
        if "/tables/" in ruta:
            return httpx.Response(200, json=pyth["price_info"])
        if ruta.endswith("FungibleStore"):
            return httpx.Response(200, json={"data": {"metadata": {"inner": "0xasset"}}})
        if ruta.endswith("/v2/price_feeds"):
            return httpx.Response(200, json=[{"id": pyth["feed_id"][2:], "attributes": {"symbol": "Crypto.APT/USD"}}])
        return httpx.Response(404)

    c = contenedor(settings, handler, db, ["aptos"])
    col = c.colectores["aptos"]
    est = correr(col.ciclo_estado())
    assert est["limite_gas"] == 300000 and est["precio_congelado"] is True
    r = correr(col.ciclo_bloques())
    assert r["bloques"] == settings.bloques_aptos_por_ciclo
    assert c.repos["muestras"].txs_desde("aptos", 0)
    assert c.repos["estado"].ultima("aptos", "precio_apt")[0]["congelado"] is True


@pytest.mark.skipif(not (RAW / "canton" / "events_sample.json").exists(), reason="faltan datos crudos")
def test_canton_eventos_cursor_y_submuestreo(settings, db):
    dso = json.load(open(RAW / "canton" / "dso_state.json", encoding="utf-8"))
    eventos = json.load(open(RAW / "canton" / "events_sample.json", encoding="utf-8"))[:200]
    llamadas = []

    def handler(req):
        if req.url.path == "/v0/dso":
            return httpx.Response(200, json=dso)
        llamadas.append(json.loads(req.content))
        return httpx.Response(200, json={"events": eventos if len(llamadas) == 1 else []})

    c = contenedor(settings, handler, db, ["canton"])
    col = c.colectores["canton"]
    assert correr(col.ciclo_estado())["super_validators"] == 13
    r = correr(col.ciclo_bloques())
    assert r["eventos"] == 200
    veredictos = sum(1 for e in eventos if e.get("verdict"))
    guardados_v = sum(1 for f in c.repos["muestras"].txs_desde("canton", 0) if f["hash"].startswith("v:"))
    assert 0 < guardados_v <= veredictos // settings.canton_submuestreo + 1
    cursor = c.repos["estado"].ultima("canton", "cursor_eventos")[0]
    assert cursor["after_migration_id"] == 4 and cursor["after_record_time"]
    assert c.repos["estado"].ultima("canton", "c5_cambios")[0]["cambios"] >= 0
    correr(col.ciclo_bloques())
    assert llamadas[1]["after"] == cursor


def test_monitor_registra_fallos_y_no_solapa_ciclos(settings, db):
    c = contenedor(settings, lambda r: httpx.Response(500), db, ["polygon"])
    m = c.monitor
    assert correr(m.ejecutar_componente("polygon", "bloques", c.colectores["polygon"].ciclo_bloques)) is None
    fila = next(f for f in c.repos["salud"].todos() if f["componente"] == "bloques")
    assert fila["fallos_consecutivos"] == 1 and "ErrorFuente" in fila["error"]

    async def escenario():
        liberar = asyncio.Event()

        async def lento():
            await liberar.wait()
            return {"ok": True}

        t = asyncio.create_task(m.ejecutar_componente("polygon", "estado", lento))
        await asyncio.sleep(0.05)
        segundo = await m.ejecutar_componente("polygon", "estado", lento)
        liberar.set()
        return segundo, await t

    segundo, primero = asyncio.run(escenario())
    assert segundo is None and primero == {"ok": True}


def test_continuidad_incremental_detecta_huecos_y_saltos():
    puntos = [(1, 0.0), (2, 1.0), (3, 2.0), (4, 3.0), (5, 100.0)]
    r = resumen_ciclo(puntos, None, True)
    assert r["n"] == 4 and r["mediana"] == 1.0 and r["grandes"] == [97.0] and r["saltados"] == 0
    r2 = resumen_ciclo([(10, 101.0), (11, 102.0)], (5, 100.0), True)
    assert r2["n"] == 1 and r2["saltados"] == 4
