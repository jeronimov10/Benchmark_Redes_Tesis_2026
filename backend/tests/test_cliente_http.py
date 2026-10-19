"""Pruebas del cliente HTTP: exito, 429 con reintento, backoff exponencial, timeouts, errores 4xx sin reintento, JSON malformado y JSON-RPC."""

import asyncio
import dataclasses

import httpx
import pytest

from app.pipelines.collectors.base import ClienteHTTP, ErrorFuente


def cliente(settings, manejador, esperas):
    async def dormir(s):
        esperas.append(s)
    cfg = dataclasses.replace(settings, http_reintentos=3, http_backoff_base_s=1.0)
    return ClienteHTTP(cfg, transport=httpx.MockTransport(manejador), dormir=dormir)


def correr(coro):
    return asyncio.run(coro)


def test_exito_devuelve_json(settings):
    c = cliente(settings, lambda r: httpx.Response(200, json={"ok": 1}), [])
    assert correr(c.get("https://x.test/a")) == {"ok": 1}


def test_reintenta_ante_429_y_se_recupera(settings):
    llamadas, esperas = [], []

    def h(req):
        llamadas.append(1)
        return httpx.Response(429) if len(llamadas) < 3 else httpx.Response(200, json={"v": 7})

    assert correr(cliente(settings, h, esperas).get("https://x.test")) == {"v": 7}
    assert len(llamadas) == 3 and len(esperas) == 2


def test_backoff_crece_exponencialmente_y_se_agota(settings):
    esperas = []
    c = cliente(settings, lambda r: httpx.Response(503), esperas)
    with pytest.raises(ErrorFuente, match="agotados 4 intentos"):
        correr(c.get("https://x.test"))
    assert len(esperas) == 3
    for i, e in enumerate(esperas):
        base = 2 ** i
        assert 0.5 * base <= e <= base


def test_respeta_retry_after(settings):
    esperas, n = [], []

    def h(req):
        n.append(1)
        return httpx.Response(429, headers={"retry-after": "7"}) if len(n) == 1 else httpx.Response(200, json={})

    correr(cliente(settings, h, esperas).get("https://x.test"))
    assert esperas == [7.0]


def test_timeout_se_reintenta_y_falla(settings):
    def h(req):
        raise httpx.ReadTimeout("lento", request=req)

    with pytest.raises(ErrorFuente, match="ReadTimeout"):
        correr(cliente(settings, h, []).get("https://x.test"))


def test_error_4xx_no_se_reintenta(settings):
    n, esperas = [], []

    def h(req):
        n.append(1)
        return httpx.Response(404, text="no existe")

    with pytest.raises(ErrorFuente, match="HTTP 404"):
        correr(cliente(settings, h, esperas).get("https://x.test"))
    assert len(n) == 1 and not esperas


def test_respuesta_no_json(settings):
    with pytest.raises(ErrorFuente, match="no JSON"):
        correr(cliente(settings, lambda r: httpx.Response(200, text="<html>"), []).get("https://x.test"))


def test_rpc_error_y_lote_en_desorden(settings):
    def h(req):
        import json
        cuerpo = json.loads(req.content)
        if isinstance(cuerpo, dict):
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}})
        resp = [{"jsonrpc": "2.0", "id": x["id"], "result": f"r{x['id']}"} for x in cuerpo][::-1]
        resp[0] = {"jsonrpc": "2.0", "id": resp[0]["id"], "error": {"message": "x"}}
        return httpx.Response(200, json=resp)

    c = cliente(settings, h, [])
    with pytest.raises(ErrorFuente, match="boom"):
        correr(c.rpc("https://x.test", "eth_x"))
    salida = correr(c.rpc_lote("https://x.test", [("m", []), ("m", []), ("m", [])]))
    assert salida == ["r0", "r1", None]
