"""Pruebas del banco de usuarios simulados: generacion determinista, reproduccion de los casos de referencia de la tesis a traves del evaluador,
clasificacion del ajuste (con nulos), contrafactuales que solo quitan, aislamiento de la base de la aplicacion y los endpoints /api/simulacion e /api/integraciones."""

import asyncio
import dataclasses
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.container import Contenedor
from app.main import crear_app
from app.services.analytics.baseline import construir_linea_base, perfiles_tesis
from conftest import BACKEND, REPO
from simulacion import experimentos, informe
from simulacion.ajuste import cumple_red, estado_ajuste
from simulacion.almacen import Almacen
from simulacion.evaluador import Evaluador, filtrar
from simulacion.personas import PERSONAS, panel, usuario, usuarios

CASOS = json.loads((BACKEND / "modelo" / "casos_referencia.json").read_text(encoding="utf-8"))
TOL = 0.005


@pytest.fixture(scope="module")
def base():
    return construir_linea_base(BACKEND / "modelo" / "perfiles.json", REPO / "resultados" / "metrics.csv")


def test_misma_semilla_genera_los_mismos_usuarios():
    a = panel(5, 2026)
    assert a == panel(5, 2026) and a != panel(5, 7)
    assert usuarios(PERSONAS[0], 0, 5, 2026) == usuarios(PERSONAS[0], 0, 5, 2026)
    assert usuario(PERSONAS[0], 3, 2026) == usuarios(PERSONAS[0], 0, 10, 2026)[3]


def test_usuarios_dentro_de_los_rangos_de_su_perfil():
    for p in PERSONAS:
        for u in usuarios(p, 0, 200, 2026):
            lo, hi = p.monto
            factor = 4000.0 if p.moneda == "USD" else 1.0
            assert lo * factor * 0.999 <= u["monto_cop"] <= hi * factor * 1.001
            assert p.espera_s[0] * 0.999 <= u["espera_s"] <= p.espera_s[1] * 1.001
            assert u["irrevocabilidad"] == p.irrevocabilidad and u["transfronterizo"] == p.transfronterizo


def test_son_doce_perfiles_con_ids_unicos():
    assert [p.id for p in PERSONAS] == list(range(1, 13))


@pytest.mark.parametrize("nombre", list(CASOS))
def test_el_evaluador_reproduce_los_casos_de_referencia(nombre):
    esperado = CASOS[nombre]
    perfiles = perfiles_tesis(BACKEND / "modelo" / "perfiles.json")
    u = {"perfil": 0, "indice": 0, "trm": 4000.0, **esperado["entrada"]}
    ev = Evaluador(1)
    try:
        r = asyncio.run(ev.evaluar(perfiles, u, 10000))
    finally:
        ev.cerrar()
    assert r["bandas"] == esperado["bandas"] and r["determinante"] == esperado["determinante"]
    assert r["certidumbre"] == pytest.approx(esperado["certidumbre"], abs=TOL)
    for red, m in esperado["medianas"].items():
        assert r["medianas"][red] == pytest.approx(m, abs=TOL)


U = {"monto_cop": 4_000_000.0, "trm": 4000.0, "espera_s": 100.0, "irrevocabilidad": "baja", "transfronterizo": False}


def _perfil(a1=0.001, b1=1.0, b2=10.0, b2b=None):
    p = {"A1": {"valor": a1}, "B1": {"valor": b1}, "B2": {"valor": b2}}
    if b2b is not None:
        p["B2b"] = {"valor": b2b}
    return p


def _res(*bandas):
    return {"bandas": [{"banda": i + 1, "redes": list(b), "puntajes": {}} for i, b in enumerate(bandas)]}


def test_ajuste_cumple_parcial_brecha_y_sin_solucion():
    perfiles = {"a": _perfil(), "b": _perfil(b2=500.0), "c": _perfil(a1=50.0), "d": _perfil(a1=50.0, b2=500.0)}
    assert estado_ajuste(perfiles, U, _res(["a"]), "requisito")[0] == "cumple"
    assert estado_ajuste(perfiles, U, _res(["a", "b"]), "requisito")[0] == "parcial"
    assert estado_ajuste(perfiles, U, _res(["a", "b"]), "preferencia")[0] == "cumple"
    assert estado_ajuste(perfiles, U, _res(["c"], ["a"]), "requisito") == ("brecha", ["costo"])
    assert estado_ajuste(perfiles, U, _res(["c", "d"]), "requisito")[0] == "sin_solucion"
    assert estado_ajuste(perfiles, U, _res(), "requisito")[0] == "sin_solucion"
    assert estado_ajuste(perfiles, U, None, "requisito")[0] == "no_evaluable"


def test_ajuste_con_valores_nulos_no_asume_nada():
    perfiles = {"a": {"A1": {"valor": None}, "B1": {"valor": 1.0}, "B2": {"valor": 1.0}}, "b": _perfil(a1=50.0)}
    assert cumple_red(perfiles["a"], U, "requisito")[0] is None
    assert estado_ajuste(perfiles, U, _res(["a"]), "requisito")[0] == "no_evaluable"
    assert estado_ajuste(perfiles, U, _res(["b"], ["a"]), "requisito")[0] == "no_evaluable"


def test_irrevocabilidad_alta_usa_b2b_o_b2_si_no_hay():
    alta = {**U, "irrevocabilidad": "alta"}
    assert cumple_red(_perfil(b2=1.0, b2b=200000.0), alta, "preferencia") == (False, ["irrevocabilidad"])
    assert cumple_red(_perfil(b2=1.0), alta, "preferencia")[0] is True
    assert cumple_red(_perfil(b2=1.0, b2b=1000.0), alta, "preferencia")[0] is True


def test_wilson_semiancho_decrece_con_n_y_es_menor_con_proporcion_extrema():
    assert experimentos.wilson_semiancho(25, 50) > experimentos.wilson_semiancho(250, 500)
    assert experimentos.wilson_semiancho(50, 50) < experimentos.wilson_semiancho(25, 50)
    assert experimentos.wilson_semiancho(0, 0) == 1.0


def test_contrafactuales_solo_quitan_nunca_agregan(base):
    original = filtrar(base)
    comunes, ids = experimentos._comunes(original)
    sin_sigma = experimentos._sin_sigma(original)
    escenarios = [comunes, filtrar(base, solo=experimentos.REDES_PCA), filtrar(base, solo=experimentos.REDES_TAC),
                  filtrar(base, excluir=("polygon",))]
    for esc in escenarios:
        assert set(esc) <= set(original)
        for red, perfil in esc.items():
            assert set(perfil) <= set(original[red])
            for mid, d in perfil.items():
                assert d["valor"] == original[red][mid]["valor"]
    assert ids and set(ids) < set(experimentos.modelo.METRICAS)
    for red, perfil in sin_sigma.items():
        for mid, d in perfil.items():
            assert d["valor"] == original[red][mid]["valor"] and d.get("sigma", 0) == 0


def test_variantes_de_sensibilidad():
    u = {**U, "irrevocabilidad": "baja"}
    assert experimentos.variante(u, "monto_x2")["monto_cop"] == u["monto_cop"] * 2
    assert experimentos.variante(u, "espera_div4")["espera_s"] == u["espera_s"] / 4
    assert experimentos.variante(u, "irrev_abajo") is None
    assert experimentos.variante(u, "irrev_arriba")["irrevocabilidad"] == "media"
    assert experimentos.variante(u, "transfronterizo_inverso")["transfronterizo"] is True


def _esperar(cliente, tope_s=240):
    fin = time.time() + tope_s
    while time.time() < fin:
        e = cliente.get("/api/simulacion").json()
        if not e["ocupado"]:
            return e
        time.sleep(0.5)
    raise AssertionError("el lote no termino")


@pytest.fixture
def cliente(settings, db):
    s = dataclasses.replace(settings, sim_procesos=2)
    c = Contenedor(s, db=db)
    with TestClient(crear_app(c)) as tc:
        tc.contenedor = c
        yield tc


def _conteos(db):
    return {t: db.uno(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in ("recomendaciones", "muestras_bloque", "muestras_tx", "metricas_vivo", "perfiles_base")}


def test_un_lote_no_agrega_filas_a_la_base_de_la_aplicacion_y_genera_el_informe(cliente, db, settings):
    antes = _conteos(db)
    cuerpo = {"fuente": "base", "replicas": 100, "tope": 50, "panel_por_perfil": 1, "niveles_replicas": [100, 200]}
    r = cliente.post("/api/simulacion/lote", json=cuerpo)
    assert r.status_code == 202
    e = _esperar(cliente)
    assert e["lote"]["estado"] == "completado", e["lote"]
    assert _conteos(db) == antes
    nombres = {a["nombre"] for a in cliente.get("/api/simulacion/archivos").json()["archivos"]}
    assert {"informe.md", "personas.csv", "contrafactuales.csv", "sensibilidad.csv", "convergencia.csv", "manifiesto.json"} <= nombres
    texto = cliente.get("/api/simulacion/archivos/informe.md").text
    assert "P1. Cobertura" in texto and "P6. Convergencia" in texto
    assert cliente.get("/api/simulacion/archivos/../redes.db").status_code in (404, 422)
    assert cliente.get("/api/simulacion/archivos/otro.txt").status_code == 404
    personas = cliente.get("/api/simulacion/archivos/personas.csv").text.splitlines()
    assert len(personas) == 13 and personas[0].startswith("fuente,perfil")


def test_endpoints_exigen_token_y_rechazan_un_segundo_lote(settings, db):
    s = dataclasses.replace(settings, sim_procesos=2, simulacion_token="secreto")
    with TestClient(crear_app(Contenedor(s, db=db))) as tc:
        cuerpo = {"fuente": "base", "replicas": 3000, "tope": 400}
        assert tc.post("/api/simulacion/lote", json=cuerpo).status_code == 401
        assert tc.post("/api/simulacion/lote", json=cuerpo, headers={"Authorization": "Bearer malo"}).status_code == 401
        h = {"Authorization": "Bearer secreto"}
        assert tc.post("/api/simulacion/lote", json=cuerpo, headers=h).status_code == 202
        assert tc.post("/api/simulacion/lote", json=cuerpo, headers=h).status_code == 409
        assert tc.delete("/api/simulacion/lote").status_code == 401
        assert tc.delete("/api/simulacion/lote", headers=h).status_code == 200
        assert _esperar(tc)["lote"]["estado"] == "cancelado"
        assert tc.get("/api/simulacion").status_code == 200


def test_peticiones_invalidas_de_lote(cliente):
    assert cliente.post("/api/simulacion/lote", json={"replicas": 5}).status_code == 400
    assert cliente.post("/api/simulacion/lote", json={"fuente": "x"}).status_code == 400
    assert cliente.delete("/api/simulacion/lote").status_code == 409


def test_estado_sin_actividad_no_crea_la_base_del_banco(cliente, settings):
    e = cliente.get("/api/simulacion").json()
    assert e["lote"] is None and e["continuo"]["activo"] is False
    assert not settings.ruta_sim_db.exists()


def test_panel_continuo_guarda_ciclos_validos_e_invalidos(settings, db):
    s = dataclasses.replace(settings, sim_procesos=2, replicas_monte_carlo=100, sim_intervalo_s=3600)
    c = Contenedor(s, db=db)
    c.sembrar()
    sim = c.simulacion

    async def correr():
        panel_ = sim.panel
        invalido = await panel_.ciclo()
        for red, mid in (("tempo", "B1"), ("polygon", "B1")):
            from app.models.dominio import EstadoMetrica, MetricaValor
            c.repos["metricas"].guardar([MetricaValor(red=red, metrica=mid, valor=1.0, unidad="s", estado=EstadoMetrica.VALIDA, n=100,
                                                      ventana_s=900, ts=time.time(), fuente="x")])
        sim.fuentes.esperadas = lambda: 2
        valido1 = await panel_.ciclo()
        valido2 = await panel_.ciclo()
        await sim.cerrar()
        return invalido, valido1, valido2

    invalido, v1, v2 = asyncio.run(correr())
    assert invalido["valido"] is False and v1["valido"] is True and v2["valido"] is True
    assert v2["cambios"] == 0


def test_endpoint_del_panel_continuo_inicia_y_detiene(cliente):
    r = cliente.post("/api/simulacion/continuo")
    assert r.status_code == 200 and r.json()["iniciado"] is True and r.json()["activo"] is True
    assert cliente.post("/api/simulacion/continuo").json()["iniciado"] is False
    assert cliente.get("/api/simulacion").json()["continuo"]["activo"] is True
    assert cliente.delete("/api/simulacion/continuo").json() == {"detenido": True}
    assert cliente.get("/api/simulacion").json()["continuo"]["activo"] is False


def test_integraciones_con_transporte_simulado(settings, db):
    def handler(request):
        cuerpo = json.loads(request.content) if request.content else {}
        if isinstance(cuerpo, dict) and cuerpo.get("method") == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x10"})
        if "aptoslabs" in str(request.url):
            return httpx.Response(200, json={"chain_id": 1, "block_height": "9"})
        if "cantonnodes" in str(request.url):
            return httpx.Response(200, json={"events": [{"x": 1}], "dso_party_id": "x"})
        return httpx.Response(500, json={"error": "no simulado"})

    c = Contenedor(dataclasses.replace(settings, http_reintentos=0), db=db, transporte_http=httpx.MockTransport(handler))
    with TestClient(crear_app(c)) as tc:
        r = tc.get("/api/integraciones")
    d = r.json()
    assert r.status_code == 200 and d["estado"] == "degradado" and d["total"] == len(d["fuentes"]) >= 14
    por_id = {f["id"]: f for f in d["fuentes"]}
    assert all(por_id[k]["ok"] for k in ("rpc_tempo", "rpc_polygon", "rpc_celo", "rpc_arbitrum", "rpc_ethereum", "aptos_rest", "canton_dso", "canton_eventos"))
    assert por_id["rpc_polygon"]["detalle"]["bloque"] == 16
    assert not por_id["pyth_hermes"]["ok"] and "pyth_hermes" in d["fallidas"]


def test_integraciones_distingue_limitada_de_caida_y_cachea(settings, db):
    llamadas = {"n": 0}

    def handler(request):
        llamadas["n"] += 1
        if "cantonnodes" in str(request.url):
            return httpx.Response(429, headers={"Retry-After": "0"}, text="rate limited")
        cuerpo = json.loads(request.content) if request.content else {}
        if isinstance(cuerpo, dict) and cuerpo.get("method") == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x10"})
        return httpx.Response(500, json={"error": "no simulado"})

    c = Contenedor(dataclasses.replace(settings, http_reintentos=0), db=db, transporte_http=httpx.MockTransport(handler))
    with TestClient(crear_app(c)) as tc:
        d = tc.get("/api/integraciones").json()
        n = llamadas["n"]
        otra = tc.get("/api/integraciones").json()
    por_id = {f["id"]: f for f in d["fuentes"]}
    assert por_id["canton_dso"]["estado"] == "limitado" and "aviso" in por_id["canton_dso"]
    assert set(d["limitadas"]) == {"canton_dso", "canton_eventos"} and "canton_dso" not in d["fallidas"]
    assert por_id["pyth_hermes"]["estado"] == "error" and por_id["rpc_tempo"]["estado"] == "ok"
    assert otra["desde_cache"] is True and llamadas["n"] == n


def test_el_informe_se_genera_sin_corridas(tmp_path):
    almacen = Almacen(":memory:")
    from types import SimpleNamespace
    archivos = informe.generar(almacen, tmp_path, SimpleNamespace())
    assert "informe.md" in archivos and "manifiesto.json" in archivos
    almacen.cerrar()
