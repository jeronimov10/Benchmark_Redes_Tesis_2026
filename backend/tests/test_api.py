"""Pruebas de la API (TestClient): formas de respuesta, validacion de peticiones, salud, mediciones con procedencia, recomendacion en ambos
modos, datos insuficientes y ciclo de vida de la recalibracion con el subproceso simulado."""

import shutil
import time

import pytest
from fastapi.testclient import TestClient

from app.container import Contenedor
from app.main import crear_app
from app.models.dominio import EstadoMetrica, MetricaValor
from app.services.recalibracion.trabajos import ServicioRecalibracion
from conftest import REPO

CASO = {"accion": "recomendar", "monto_cop": 1_200_000, "transfronterizo": True, "espera_s": 3600,
        "irrevocabilidad": "baja", "trm": 4000}


@pytest.fixture
def cliente(settings, db):
    c = Contenedor(settings, db=db)
    with TestClient(crear_app(c)) as tc:
        tc.contenedor = c
        yield tc


def test_salud_y_redes(cliente):
    s = cliente.get("/api/salud").json()
    assert s["base_de_datos"]["version_esquema"] == 1 and s["monitor"]["corriendo"] is False
    assert set(s["redes"]) == {"polygon", "celo", "arbitrum", "tempo", "aptos", "canton"}
    r = cliente.get("/api/redes").json()["redes"]
    assert {x["id"] for x in r} == set(s["redes"])
    assert {x["responsable"] for x in r} == {"Dilan", "Jeronimo"}
    aptos = next(x for x in r if x["id"] == "aptos")
    assert "B2" in aptos["metricas_base"] and "B2" not in aptos["metricas_vivo"]


def test_mediciones_listan_16_metricas_con_origen_base_sin_vivo(cliente):
    d = cliente.get("/api/mediciones").json()
    assert len(d["redes"]) == 6 and d["version_perfil"]
    for red in d["redes"]:
        assert len(red["metricas"]) == 16
        assert all(m["origen"] in ("base", None) for m in red["metricas"])
    aptos = next(r for r in d["redes"] if r["id"] == "aptos")
    b2 = next(m for m in aptos["metricas"] if m["id"] == "B2")
    assert b2["valor"] is None and "HTTP" in b2["razon_solo_base"]


def test_mediciones_reflejan_metrica_en_vivo_con_procedencia(cliente):
    c = cliente.contenedor
    c.repos["metricas"].guardar([MetricaValor(red="tempo", metrica="B1", valor=0.5, sigma=0.01, unidad="s",
                                              estado=EstadoMetrica.VALIDA, n=300, ventana_s=900, ts=time.time(),
                                              fuente="tempo:rpc", nota="p95")])
    c.invalidar_caches()
    tempo = next(r for r in cliente.get("/api/mediciones").json()["redes"] if r["id"] == "tempo")
    b1 = next(m for m in tempo["metricas"] if m["id"] == "B1")
    assert b1["origen"] == "vivo" and b1["valor"] == 0.5 and b1["n"] == 300 and b1["vivo"]["estado"] == "valida"
    detalle = cliente.get("/api/mediciones/tempo").json()
    assert detalle["red"]["id"] == "tempo" and "B1" in detalle["series"]
    assert cliente.get("/api/mediciones/nada").status_code == 404


def test_modelo_info_e_interpretar(cliente):
    info = cliente.get("/api/modelo").json()
    assert len(info["redes"]) == 6 and "A1" in info["metricas"] and set(info["escenarios"]) == {"remesas", "comercio", "altovalor"}
    r = cliente.post("/api/modelo", json={**CASO, "accion": "interpretar"}).json()
    assert r["nivel_certidumbre"] == "alta" and r["ticket_usd"] == 300


@pytest.mark.parametrize("cuerpo", [{}, {**CASO, "monto_cop": -1}, {**CASO, "irrevocabilidad": "x"}, {**CASO, "espera_s": 0}])
def test_modelo_rechaza_peticiones_invalidas(cliente, cuerpo):
    r = cliente.post("/api/modelo", json=cuerpo)
    assert r.status_code == 400 and r.json()["error"] == "peticion invalida"


def test_recomendar_en_los_dos_modos(cliente):
    medicion = cliente.post("/api/modelo", json={**CASO, "modo": "medicion"}).json()
    vivo = cliente.post("/api/modelo", json={**CASO, "modo": "vivo"}).json()
    for r in (medicion, vivo):
        assert r["estado"] == "ok" and r["resultado"]["bandas"] and r["nivel_certidumbre"] == "alta"
        assert set(r["detalle"]) == {"polygon", "celo", "arbitrum", "tempo", "aptos", "canton"} - set(r["resultado"]["inadmisibles"]) | set(r["resultado"]["inadmisibles"])
        assert r["procedencia"]["polygon"]["A1"]["origen"] == "base"
    assert "aptos" in medicion["resultado"]["inadmisibles"]
    assert medicion["frescura"]["metricas_vivo"] == 0
    assert medicion["detalle"]["polygon"]["metricas"][0]["procedencia"]["origen"] == "base"


def test_recomendar_un_vivo_cambia_la_version_e_invalida_cache(cliente):
    c = cliente.contenedor
    antes = cliente.post("/api/modelo", json=CASO).json()["version_perfil"]
    c.repos["metricas"].guardar([MetricaValor(red="polygon", metrica="B1", valor=2.5, unidad="s", estado=EstadoMetrica.VALIDA,
                                              n=100, ventana_s=900, ts=time.time(), fuente="polygon:rpc")])
    c.invalidar_caches()
    despues = cliente.post("/api/modelo", json=CASO).json()
    assert despues["version_perfil"] != antes and despues["frescura"]["metricas_vivo"] == 1
    assert despues["procedencia"]["polygon"]["B1"]["origen"] == "vivo"


def test_recomendacion_con_datos_insuficientes(settings, db):
    c = Contenedor(settings, db=db)
    with TestClient(crear_app(c)) as tc:
        db.ejecutar("DELETE FROM perfiles_base WHERE red != 'polygon'")
        c.invalidar_caches()
        r = tc.post("/api/modelo", json=CASO).json()
    assert r["estado"] == "datos_insuficientes" and r["resultado"] is None


def test_recalibracion_ciclo_de_vida(cliente, monkeypatch):
    c = cliente.contenedor
    version_antes = c.repos["perfiles"].version()

    def falso(self, id_, directorio, p):
        shutil.copy(REPO / "resultados" / "metrics.csv", directorio / "resultados" / "metrics.csv")
        self.trabajos.actualizar(id_, progreso=0.5, etapa=">>> falso")
        return 0, "salida simulada"

    monkeypatch.setattr(ServicioRecalibracion, "_correr_benchmark", falso)
    inicio = cliente.post("/api/recalibracion", json={"redes": ["tempo", "polygon"]})
    assert inicio.status_code == 200 and inicio.json()["redes"] == ["tempo"] and inicio.json()["no_disponible"] == ["polygon"]
    for _ in range(100):
        estado = cliente.get("/api/recalibracion").json()
        if estado["trabajo"]["estado"] != "en_curso":
            break
        time.sleep(0.05)
    assert estado["trabajo"]["estado"] == "completado" and estado["trabajo"]["progreso"] == 1.0
    assert c.repos["perfiles"].version() == version_antes + 1
    assert "polygon" in estado["alcance"]["no_disponible"]
    assert cliente.delete("/api/recalibracion").status_code == 409
    assert cliente.post("/api/recalibracion", json={"redes": ["xyz"]}).status_code == 422


def test_recalibracion_fallida_se_reporta(cliente, monkeypatch):
    monkeypatch.setattr(ServicioRecalibracion, "_correr_benchmark", lambda self, i, d, p: (3, "boom"))
    cliente.post("/api/recalibracion", json={})
    for _ in range(100):
        estado = cliente.get("/api/recalibracion").json()
        if estado["trabajo"]["estado"] != "en_curso":
            break
        time.sleep(0.05)
    assert estado["trabajo"]["estado"] == "fallido" and "boom" in estado["trabajo"]["log_tail"]
