"""Pruebas de infraestructura: migraciones y repositorios SQLite, poda por retencion, cache TTL/LRU, linea base (metrics.csv -> perfiles) y validadores."""

import time

import pytest

from app.db.connection import Database
from app.db.repositorios import EstadoRepo, MetricasRepo, MuestrasRepo, PerfilesRepo
from app.models.dominio import EstadoMetrica, MetricaValor
from app.pipelines.validators.validadores import estado_por_muestras, fee_usd_valido, ocupacion_valida, timestamp_valido
from app.services.analytics.baseline import construir_linea_base, perfiles_desde_metrics_csv
from app.utils.cache import CacheTTL
from conftest import BACKEND, REPO


def test_migracion_idempotente_en_disco(tmp_path):
    ruta = tmp_path / "m.db"
    Database(ruta).cerrar()
    d = Database(ruta)
    assert d.version() == 1
    assert {r["name"] for r in d.consultar("SELECT name FROM sqlite_master WHERE type='table'")} >= {
        "muestras_bloque", "muestras_tx", "muestras_finalidad", "lecturas_estado", "metricas_vivo", "perfiles_base",
        "salud_colector", "trabajos_recalibracion", "recomendaciones", "redes", "meta"}
    d.cerrar()


def test_muestras_ignoran_duplicados_y_podan(db):
    r = MuestrasRepo(db)
    b = {"numero": 1, "ts": 100.0, "productor": "p", "gas_usado": 1.0, "gas_limite": 2.0, "n_tx": 1, "fuente": "x"}
    assert r.guardar_bloques("tempo", [b, b]) == 2
    assert len(r.bloques_desde("tempo", 0)) == 1
    r.guardar_bloques("tempo", [{**b, "numero": 2, "ts": 5000.0}])
    r.guardar_txs("tempo", [{"hash": "h", "ts": 100.0, "estado_ok": True}])
    r.guardar_finalidad("tempo", [{"bloque": 1, "tau_1": 1.0, "tau_f": 100.0, "delta_s": 99.0}])
    EstadoRepo(db).guardar("tempo", "k", {"a": 1}, ts=100.0)
    MetricasRepo(db).guardar([MetricaValor(red="tempo", metrica="B1", valor=1, ts=100.0)])
    assert r.podar(1000, 1000, 1000, 1000) >= 5
    assert [x["numero"] for x in r.bloques_desde("tempo", 0)] == [2]
    assert r.txs_desde("tempo", 0) == [] and r.finalidad_desde("tempo", 0) == []
    assert EstadoRepo(db).ultima("tempo", "k") == (None, None)


def test_metricas_ultimas_devuelve_la_mas_reciente(db):
    m = MetricasRepo(db)
    m.guardar([MetricaValor(red="a", metrica="B1", valor=1, ts=1.0, estado=EstadoMetrica.VALIDA)])
    m.guardar([MetricaValor(red="a", metrica="B1", valor=2, ts=2.0, estado=EstadoMetrica.VALIDA)])
    assert [x["valor"] for x in m.ultimas("a")] == [2]
    assert len(m.serie("a", "B1", 0)) == 2


def test_perfiles_base_versionan_y_reemplazan(db):
    p = PerfilesRepo(db)
    assert p.vacio() and p.version() == 0
    assert p.reemplazar_redes({"x": {"A1": {"valor": 1.0, "sigma": 0.1, "nota": "n", "cota_inferior": True}}}, "o") == 1
    assert p.reemplazar_redes({"x": {"A1": {"valor": 2.0}}, "y": {"B1": {"valor": None}}}, "o2") == 2
    perfiles, origenes = p.todos()
    assert perfiles["x"]["A1"] == {"valor": 2.0, "nota": None} and perfiles["y"]["B1"]["valor"] is None
    assert origenes["x"]["A1"]["origen"] == "o2"


def test_cache_ttl_lru_e_invalidacion():
    c = CacheTTL(max_entradas=2, ttl_s=0.05)
    c.guardar("a", 1)
    c.guardar("b", 2)
    c.guardar("c", 3)
    assert c.obtener("a") is None and c.obtener("b") == 2
    time.sleep(0.08)
    assert c.obtener("b") is None
    c.guardar("p:1", 1, ttl_s=10)
    c.guardar("q:1", 1, ttl_s=10)
    c.invalidar("p:")
    assert c.obtener("p:1") is None and c.obtener("q:1") == 1
    c.invalidar()
    assert len(c) == 0


def test_linea_base_convierte_unidades_y_respeta_lo_no_computable():
    b = construir_linea_base(BACKEND / "modelo" / "perfiles.json", REPO / "resultados" / "metrics.csv")
    assert set(b) == {"polygon", "celo", "arbitrum", "tempo", "aptos", "canton"}
    t = b["tempo"]
    assert t["A2"]["valor"] == pytest.approx(0.0001785474 / 0.0000201522) and t["C3"]["valor"] == 100.0
    assert t["B3"]["valor"] == pytest.approx(556.8040922656879 * 48 / 18) and t["C1"]["valor"] == pytest.approx(1 / 15)
    assert t["A1"]["sigma"] == 0.0 and "sigma=0" in t["A1"]["nota"] and "B2b" not in t
    assert b["aptos"]["B2"]["valor"] is None and b["aptos"]["D2"]["valor"] is None and "sigma" not in b["aptos"]["B2"]
    assert b["canton"]["B3"]["cota_inferior"] is True and "C1" in b["canton"] and b["canton"]["C1"]["valor"] == pytest.approx(0.2958638860937225)
    assert b["polygon"]["B1"]["valor"] == 1.5


def test_validadores():
    assert fee_usd_valido(0.01) and not fee_usd_valido(-1) and not fee_usd_valido(float("nan")) and not fee_usd_valido(1e6)
    assert ocupacion_valida(0.5) and not ocupacion_valida(1.5)
    assert timestamp_valido(time.time(), time.time()) and not timestamp_valido(5, time.time())
    assert estado_por_muestras(5, 30, 1.0, 2.0, 10) == EstadoMetrica.INSUFICIENTE
    assert estado_por_muestras(50, 30, 1.0, 100.0, 10) == EstadoMetrica.OBSOLETA
    assert estado_por_muestras(50, 30, 99.0, 100.0, 10) == EstadoMetrica.VALIDA
