"""Prueba de fidelidad metodologica: el calculo en vivo (procesadores + metricas) aplicado a las muestras crudas de resultados/raw/ debe reproducir
los valores de resultados/metrics.csv de Tempo, Aptos y Canton. Es la evidencia de que pasar una metrica a vivo no cambia su definicion."""

import csv
import dataclasses
import json
import statistics as st

import pytest

from app.db.repositorios import EstadoRepo, MuestrasRepo
from app.pipelines.processors.aptos import decodificar_execution_config, procesar_bloque
from app.pipelines.processors.canton import (epoch, pesos_super_validators, precio_trafico_usd_por_mb, procesar_evento,
                                             trafico_base)
from app.pipelines.processors.evm import bloque_a_muestra, hx, ocupacion
from app.pipelines.processors.tempo import tx_tempo
from app.services.analytics.metricas import Contexto, calcular_metricas
from conftest import REPO

RAW = REPO / "resultados" / "raw"
GRANDE = 10 ** 9

pytestmark = pytest.mark.skipif(not (RAW / "tempo" / "blocks_sample.json").exists(), reason="faltan datos crudos")


def csv_valores():
    out = {}
    for f in csv.DictReader(open(REPO / "resultados" / "metrics.csv", encoding="utf-8")):
        if f["valor"] != "":
            out.setdefault((f["red"], f["metrica_id"]), float(f["valor"]))
    return out


CSV = csv_valores()


def cargar(ruta):
    return json.load(open(ruta, encoding="utf-8"))


def ctx_para(db, settings, ahora):
    cfg = dataclasses.replace(settings, ventana_flujo_s=GRANDE, ventana_distribucion_s=GRANDE, obsolescencia_s=GRANDE,
                              obsolescencia_estado_s=GRANDE, ventana_continuidad_s=GRANDE, canton_submuestreo=1)
    return Contexto(cfg, MuestrasRepo(db), EstadoRepo(db), ahora)


def por_id(metricas):
    return {m.metrica: m for m in metricas}


def test_tempo_reproduce_metrics_csv(db, settings):
    blocks = cargar(RAW / "tempo" / "blocks_sample.json")
    receipts = [r for r in cargar(RAW / "tempo" / "receipts_sample.json") if r]
    fee_meta = set(cargar(RAW / "tempo" / "fee_token_meta.json"))
    muestras, info = [], {}
    for b in blocks:
        m = bloque_a_muestra(b)
        m["productor"] = ((b.get("consensusContext") or {}).get("proposer") or "").lower() or None
        muestras.append(m)
        info[hx(b["number"])] = (m["ts"], ocupacion(b))
    repo = MuestrasRepo(db)
    repo.guardar_bloques("tempo", sorted(muestras, key=lambda x: x["numero"]))
    repo.guardar_txs("tempo", [tx_tempo(r, *info[hx(r["blockNumber"])], fee_meta) for r in receipts])
    estado = EstadoRepo(db)
    estado.guardar("tempo", "validadores", {"n": cargar(RAW / "tempo" / "validator_config.json")["n_activos"]})
    estado.guardar("tempo", "fork_schedule", cargar(RAW / "tempo" / "fork_schedule.json")["result"])
    ahora = max(m["ts"] for m in muestras) + 1
    m = por_id(calcular_metricas("tempo", ctx_para(db, settings, ahora)))
    assert m["B1"].valor == pytest.approx(CSV[("tempo", "B1")], rel=1e-9)
    assert m["A1"].valor == pytest.approx(CSV[("tempo", "A1")], rel=1e-9)
    assert m["A2"].valor == pytest.approx(CSV[("tempo", "A2")] / CSV[("tempo", "A1")], rel=1e-9)
    assert m["A3"].valor == pytest.approx(CSV[("tempo", "A3")], rel=1e-9)
    assert m["C4"].valor == CSV[("tempo", "C4")]
    assert m["D1"].valor == CSV[("tempo", "D1")]
    assert m["D2"].valor == pytest.approx(CSV[("tempo", "D2")])
    assert m["D3"].valor == pytest.approx(CSV[("tempo", "D3")])
    assert m["C1"].valor == pytest.approx(CSV[("tempo", "C1b")]) and m["C2"].valor == CSV[("tempo", "C2")]
    assert m["B3"].valor * 18 == pytest.approx(CSV[("tempo", "B3")] * 48, rel=5e-3)


def test_aptos_reproduce_metrics_csv(db, settings):
    blocks = cargar(RAW / "aptos" / "blocks_sample.json")
    precio = cargar(RAW / "aptos" / "pyth_apt_usd_price.json")["price_info"]["price_feed"]["price"]
    usd = int(precio["price"]["magnitude"]) / 10 ** int(precio["expo"]["magnitude"])
    stores = cargar(RAW / "aptos" / "fa_store_to_asset.json")
    limite = decodificar_execution_config(cargar(RAW / "aptos" / "execution_config.json")["data"]["config"])[
        "block_gas_limit_type"]["effective_block_gas_limit"]
    assert limite == 300000
    bloques, txs = [], []
    for b in blocks:
        bl, tx = procesar_bloque(b, limite, usd, stores)
        bloques.append(bl)
        txs += tx
    repo = MuestrasRepo(db)
    repo.guardar_bloques("aptos", sorted(bloques, key=lambda x: x["numero"]))
    repo.guardar_txs("aptos", txs)
    estado = EstadoRepo(db)
    vs = cargar(RAW / "aptos" / "validator_set.json")
    estado.guardar("aptos", "validator_set", {"pesos": [int(v["voting_power"]) for v in vs["data"]["active_validators"]]})
    estado.guardar("aptos", "execution_config", {"limite_gas": limite})
    ahora = max(b["ts"] for b in bloques) + 1
    m = por_id(calcular_metricas("aptos", ctx_para(db, settings, ahora)))
    assert m["B1"].valor == pytest.approx(CSV[("aptos", "B1")], rel=1e-5)
    assert m["A1"].valor == pytest.approx(CSV[("aptos", "A1")], rel=1e-9)
    assert m["A2"].valor == pytest.approx(CSV[("aptos", "A2")] / CSV[("aptos", "A1")], rel=1e-9)
    assert m["A3"].valor == pytest.approx(CSV[("aptos", "A3")], rel=1e-9)
    assert m["C4"].valor == CSV[("aptos", "C4")]
    assert m["D1"].valor == pytest.approx(CSV[("aptos", "D1")])
    assert m["D3"].valor == CSV[("aptos", "D3")]
    assert m["C1"].valor == pytest.approx(CSV[("aptos", "C1b")]) and m["C2"].valor == CSV[("aptos", "C2")]
    assert m["B3"].valor * 18 == pytest.approx(CSV[("aptos", "B3")] * 48, rel=5e-3)
    assert m["B2"].estado.value == "no_computable" and m["D2"].estado.value == "no_computable"


def test_canton_reproduce_metrics_csv(db, settings):
    eventos = cargar(RAW / "canton" / "events_sample.json")
    dso = cargar(RAW / "canton" / "dso_state.json")
    precio = precio_trafico_usd_por_mb(dso)
    txs, fin = [], []
    for e in eventos:
        p = procesar_evento(e, precio)
        txs += p["txs"]
        if p["finalidad"]:
            fin.append(p["finalidad"])
    repo = MuestrasRepo(db)
    repo.guardar_txs("canton", txs)
    repo.guardar_finalidad("canton", fin)
    burst, ventana = trafico_base(dso)
    EstadoRepo(db).guardar("canton", "dso", {"pesos": pesos_super_validators(dso), "precio_mb": precio,
                                              "burst_bytes": burst, "burst_ventana_s": ventana})
    ahora = max(f["tau_f"] for f in fin) + 1
    m = por_id(calcular_metricas("canton", ctx_para(db, settings, ahora)))
    assert m["B1"].valor == pytest.approx(CSV[("canton", "B1")], rel=1e-6)
    assert m["B2"].valor == pytest.approx(st.median(f["delta_s"] for f in fin))
    assert m["A1"].valor == pytest.approx(CSV[("canton", "A1")], rel=1e-9)
    assert m["A2"].valor == pytest.approx(CSV[("canton", "A2")] / CSV[("canton", "A1")], rel=1e-9)
    assert m["A3"].valor == pytest.approx(CSV[("canton", "A3")], rel=1e-6)
    assert m["C4"].valor == CSV[("canton", "C4")]
    assert m["D2"].valor == pytest.approx(CSV[("canton", "D2")])
    assert m["D3"].valor == CSV[("canton", "D3")]
    assert m["C1"].valor == pytest.approx(CSV[("canton", "C1b")]) and m["C2"].valor == CSV[("canton", "C2")]
    assert m["B3"].valor * 18 == pytest.approx(CSV[("canton", "B3")] * 48, rel=1e-6) and m["B3"].cota_inferior
