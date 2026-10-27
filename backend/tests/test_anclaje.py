"""Pruebas del rastreador de anclaje en Ethereum (Polygon, Celo, Arbitrum), de A4/B2/B2b derivados de el y del relleno por lotes de EVM,
con L1 y L2 simulados (httpx.MockTransport). No tocan la red real."""

import asyncio
import time

import pytest

from app.pipelines.collectors.anclaje import ANCLAJES, RastreadorAnclaje, costo_eth_de_recibo
from app.pipelines.collectors.base import ErrorFuente
from app.pipelines.collectors.precios import FEEDS_CHAINLINK, SEL_DECIMALES, SEL_DESCRIPCION, SEL_ULTIMA_RONDA
from app.services.analytics.metricas import Contexto, calcular_metricas
from app.utils.keccak import selector, topic
from test_colectores import abi_texto, bloque_evm, contenedor, palabra, rpc_falso

CABEZA_L1 = 100_000
SEP_BLOQUES_L1 = 75
AHORA = time.time()
T0 = AHORA - CABEZA_L1 * 12


def ts(n):
    return int(T0 + n * 12)


def bloque_con_ts(n):
    return {"number": hex(n), "timestamp": hex(ts(n)), "gasLimit": hex(30_000_000), "gasUsed": hex(15_000_000),
            "miner": "0x" + "ab" * 20, "transactions": []}


def logs_anclaje(red, bloques_l1):
    cfg = ANCLAJES[red]
    t0 = topic(cfg["evento"])
    out = []
    for i, b in enumerate(bloques_l1):
        data = "0x" + palabra(b - 80) + palabra(b - 50) + palabra(7) if cfg["rango_l2"] else "0x" + palabra(i)
        out.append({"transactionHash": f"0x{b:064x}", "logIndex": "0x0", "blockNumber": hex(b), "data": data,
                    "topics": [t0] + ["0x" + palabra(1)] * 3})
    return out


def l1_simulado(red, enlazado=True):
    bloques_l1 = list(range(CABEZA_L1, 0, -SEP_BLOQUES_L1))[::-1]
    cfg = ANCLAJES[red]

    def logs(p):
        f = p[0]
        a, b = int(f["fromBlock"], 16), int(f["toBlock"], 16)
        return logs_anclaje(red, [x for x in bloques_l1 if a <= x <= b])

    def eth_call(p):
        d = p[0]["data"]
        a = p[0]["to"].lower()
        if d == selector("sequencerInbox()"):
            return "0x" + "00" * 12 + (cfg["contrato"][2:].lower() if enlazado else "11" * 20)
        if d == SEL_DESCRIPCION:
            return abi_texto("ETH / USD")
        if d == SEL_DECIMALES:
            return "0x" + palabra(8)
        if d == SEL_ULTIMA_RONDA and a == FEEDS_CHAINLINK["ETH"]["direccion"].lower():
            return "0x" + palabra(1) + palabra(2000 * 10 ** 8) + palabra(0) + palabra(int(time.time()) - 10) + palabra(1)
        return "0x" + palabra(6)

    return rpc_falso({
        "eth_blockNumber": lambda p: hex(CABEZA_L1),
        "eth_getCode": lambda p: "0x6080",
        "eth_getLogs": logs,
        "eth_getBlockByNumber": lambda p: bloque_con_ts(int(p[0], 16)),
        "eth_getTransactionReceipt": lambda p: {"gasUsed": hex(200_000), "effectiveGasPrice": hex(2_000_000_000)},
        "eth_call": eth_call,
    })


def correr(c):
    return asyncio.run(c)


def sembrar_caudal_l2(c, red):
    n, t = 1000, AHORA - 3600
    c.repos["muestras"].guardar_bloques(red, [
        {"numero": n + i, "ts": t + 2 * i, "productor": "0xaa", "gas_usado": 1.0, "gas_limite": 2.0, "n_tx": 100, "fuente": "t"}
        for i in range(200)])


def ctx_de(c):
    return Contexto(c.settings, c.repos["muestras"], c.repos["estado"], AHORA, c.repos["anclajes"])


def test_polygon_verifica_explora_y_calcula_a4_b2_b2b(settings, db):
    c = contenedor(settings, l1_simulado("polygon"), db, ["polygon"])
    r = c.colectores["polygon"]
    res = correr(r.ciclo_anclaje())
    assert res["anclajes_nuevos"] > 90 and res["costos"] > 0
    assert c.repos["estado"].ultima("polygon", "anclaje_verificado")[0]["topic0"] == topic(ANCLAJES["polygon"]["evento"])
    anclajes = c.repos["anclajes"].desde("polygon", AHORA - 72 * 3600)
    assert anclajes[0]["l2_hasta"] == anclajes[0]["l1_bloque"] - 50
    assert anclajes[-1]["costo_usd"] == pytest.approx(200_000 * 2e9 / 1e18 * 2000)
    sembrar_caudal_l2(c, "polygon")
    m = {x.metrica: x for x in calcular_metricas("polygon", ctx_de(c))}
    assert m["B2"].valor == pytest.approx(SEP_BLOQUES_L1 * 12 / 2) and m["B2"].estado.value == "valida"
    assert m["B2b"].valor == m["B2"].valor
    assert m["A4"].valor == pytest.approx(0.8 / (50 * SEP_BLOQUES_L1 * 12), rel=1e-3) and m["A4"].estado.value == "valida"


def test_arbitrum_y_celo_no_emiten_b2b_en_vivo(settings, db):
    for red in ("arbitrum", "celo"):
        c = contenedor(settings, l1_simulado(red), db, [red])
        correr(c.colectores[red].ciclo_anclaje())
        sembrar_caudal_l2(c, red)
        m = {x.metrica: x for x in calcular_metricas(red, ctx_de(c))}
        assert "B2b" not in m and m["B2"].valor == pytest.approx(SEP_BLOQUES_L1 * 12 / 2)


def test_arbitrum_rechaza_contrato_que_no_es_su_sequencer_inbox(settings, db):
    c = contenedor(settings, l1_simulado("arbitrum", enlazado=False), db, ["arbitrum"])
    with pytest.raises(ErrorFuente, match="no apunta"):
        correr(c.colectores["arbitrum"].ciclo_anclaje())
    assert c.repos["anclajes"].desde("arbitrum", 0) == []


def test_sin_verificacion_las_metricas_de_anclaje_quedan_insuficientes(settings, db):
    c = contenedor(settings, l1_simulado("polygon"), db, ["polygon"])
    m = {x.metrica: x for x in calcular_metricas("polygon", ctx_de(c))}
    assert {m[k].estado.value for k in ("A4", "B2", "B2b")} == {"insuficiente"}


def test_el_cursor_evita_releer_y_costo_se_reparte_entre_logs_de_una_tx():
    assert costo_eth_de_recibo({"gasUsed": hex(100), "effectiveGasPrice": hex(10 ** 9), "blobGasUsed": hex(10),
                                "blobGasPrice": hex(10 ** 9)}) == pytest.approx(110 * 1e9 / 1e18)


def test_relleno_guarda_bloques_en_trozos_y_no_repite(settings, db):
    bloques = {n: bloque_evm(n, []) for n in range(0, 400)}
    c = contenedor(settings, rpc_falso({
        "eth_blockNumber": lambda p: hex(399),
        "eth_getBlockByNumber": lambda p: bloques[int(p[0], 16)],
        "eth_getLogs": lambda p: [],
        "eth_getCode": lambda p: "0x6080",
        "eth_call": lambda p: abi_texto("USDC") if p[0]["data"] == selector("symbol()") else "0x" + palabra(6),
    }), db, ["polygon"])
    col = c.colectores["polygon"]
    primero = correr(col.rellenar(minutos=2))
    assert primero["bloques"] == primero["bloques_solicitados"] == 120
    assert len(c.repos["muestras"].bloques_desde("polygon", 0)) == 120
    segundo = correr(col.rellenar(minutos=2))
    assert segundo["bloques"] == 0
