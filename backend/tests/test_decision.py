"""Pruebas del modelo de decision: casos de referencia de la tesis (misma banda, determinante y medianas con tolerancia 0,005), perfil efectivo
(sobreescritura en vivo, respaldo por obsolescencia, procedencia), datos insuficientes y cache por version de perfil."""

import json
import time

import pytest

from app.db.repositorios import MetricasRepo, PerfilesRepo
from app.models.dominio import EstadoMetrica, MetricaValor
from app.services.analytics.baseline import REDES_TESIS, perfiles_tesis
from app.services.decision.perfiles import ServicioPerfiles
from app.services.decision.recomendador import Recomendador
from app.services.decision.trabajador import ejecutar_modelo
from conftest import BACKEND

CASOS = json.loads((BACKEND / "modelo" / "casos_referencia.json").read_text(encoding="utf-8"))
TOL = 0.005


@pytest.fixture(scope="module")
def perfiles_tres():
    return perfiles_tesis(BACKEND / "modelo" / "perfiles.json")


@pytest.mark.parametrize("nombre", list(CASOS))
def test_casos_de_referencia_de_la_tesis(nombre, perfiles_tres):
    esperado = CASOS[nombre]
    r = ejecutar_modelo(perfiles_tres, {**esperado["entrada"], "trm": 4000.0}, 10000)
    assert [b["redes"] for b in r["bandas"]] == esperado["bandas"]
    assert r["determinante"]["metrica"] == esperado["determinante"]
    assert r["certidumbre"] == pytest.approx(esperado["certidumbre"], abs=TOL)
    medianas = {red: p["mediana"] for b in r["bandas"] for red, p in b["puntajes"].items()}
    assert set(medianas) == set(esperado["medianas"])
    for red, m in esperado["medianas"].items():
        assert medianas[red] == pytest.approx(m, abs=TOL)


def test_modelo_es_determinista(perfiles_tres):
    e = {"monto_cop": 80_000_000, "transfronterizo": False, "espera_s": 600, "irrevocabilidad": "alta", "trm": 4000.0}
    a = ejecutar_modelo(perfiles_tres, e, 500)
    b = ejecutar_modelo(perfiles_tres, e, 500)
    assert a == b


def montar(db, perfiles):
    repo = PerfilesRepo(db)
    repo.reemplazar_redes(perfiles, "prueba")
    metricas = MetricasRepo(db)
    from app.config import Settings
    import dataclasses
    s = dataclasses.replace(Settings(), obsolescencia_s=900, obsolescencia_estado_s=7200)
    return repo, metricas, ServicioPerfiles(s, repo, metricas), s


def vivo(red, metrica, valor, ts, estado=EstadoMetrica.VALIDA, sigma=None):
    return MetricaValor(red=red, metrica=metrica, valor=valor, sigma=sigma, unidad="u", estado=estado, n=100,
                        ventana_s=900, ts=ts, fuente="prueba", nota="n")


def test_perfil_efectivo_usa_vivo_valido_y_fresco(db, perfiles_tres):
    _, metricas, svc, _ = montar(db, perfiles_tres)
    metricas.guardar([vivo("polygon", "B1", 1.7, time.time(), sigma=0.01)])
    efectivo, prov = svc.construir("vivo")
    assert efectivo["polygon"]["B1"]["valor"] == 1.7 and efectivo["polygon"]["B1"]["sigma"] == 0.01
    assert prov["polygon"]["B1"]["origen"] == "vivo" and prov["polygon"]["B1"]["n"] == 100
    assert prov["polygon"]["B2"]["origen"] == "base"
    assert "EN VIVO" in efectivo["polygon"]["B1"]["nota"]


def test_modo_medicion_ignora_vivo(db, perfiles_tres):
    _, metricas, svc, _ = montar(db, perfiles_tres)
    metricas.guardar([vivo("polygon", "B1", 1.7, time.time())])
    efectivo, prov = svc.construir("medicion")
    assert efectivo["polygon"]["B1"]["valor"] == 1.5 and prov["polygon"]["B1"]["origen"] == "base"


@pytest.mark.parametrize("estado,edad", [(EstadoMetrica.VALIDA, 2000), (EstadoMetrica.INSUFICIENTE, 0),
                                         (EstadoMetrica.OBSOLETA, 0), (EstadoMetrica.FALLIDA, 0),
                                         (EstadoMetrica.NO_COMPUTABLE, 0)])
def test_vivo_no_vigente_cae_a_linea_base(db, perfiles_tres, estado, edad):
    _, metricas, svc, _ = montar(db, perfiles_tres)
    metricas.guardar([vivo("polygon", "B1", 9.9, time.time() - edad, estado=estado)])
    efectivo, prov = svc.construir("vivo")
    assert efectivo["polygon"]["B1"]["valor"] == 1.5
    assert prov["polygon"]["B1"]["origen"] == "base" and "vivo_descartado" in prov["polygon"]["B1"]


def test_version_cambia_con_datos_vivos(db, perfiles_tres):
    _, metricas, svc, _ = montar(db, perfiles_tres)
    v0 = svc.version(svc.construir("vivo")[0])
    metricas.guardar([vivo("polygon", "B1", 1.7, time.time())])
    assert svc.version(svc.construir("vivo")[0]) != v0


def test_datos_insuficientes_no_fabrica_recomendacion(db, settings):
    repo = PerfilesRepo(db)
    repo.reemplazar_redes({"polygon": {"B1": {"valor": 1.5}}, "celo": {"B1": {"valor": None}}}, "prueba")
    svc = ServicioPerfiles(settings, repo, MetricasRepo(db))
    rec = Recomendador(settings, svc)
    r = rec.recomendar({"monto_cop": 1e6, "transfronterizo": False, "espera_s": 60, "irrevocabilidad": "media",
                        "trm": 4000.0, "modo": "vivo"})
    rec.cerrar()
    assert r["estado"] == "datos_insuficientes" and r["resultado"] is None and "motivo" in r


def test_recomendador_servicio_coincide_con_modelo_y_usa_cache(db, settings, perfiles_tres):
    repo = PerfilesRepo(db)
    repo.reemplazar_redes(perfiles_tres, "perfiles.json")
    rec = Recomendador(settings, ServicioPerfiles(settings, repo, MetricasRepo(db)))
    e = {"monto_cop": 1_200_000, "transfronterizo": True, "espera_s": 3600, "irrevocabilidad": "baja", "trm": 4000.0,
         "modo": "medicion"}
    r1 = rec.recomendar(e, replicas=400)
    r2 = rec.recomendar(e, replicas=400)
    rec.cerrar()
    assert r1 is r2 and rec.cache.aciertos == 1
    directo = ejecutar_modelo(perfiles_tres, {k: e[k] for k in ("monto_cop", "transfronterizo", "espera_s", "irrevocabilidad", "trm")}, 400)
    assert r1["resultado"] == directo
    assert set(r1["detalle"]) == set(REDES_TESIS) and r1["procedencia"]["polygon"]["A1"]["origen"] == "base"
    assert r1["estado"] == "ok" and r1["nivel_certidumbre"] == "alta"
