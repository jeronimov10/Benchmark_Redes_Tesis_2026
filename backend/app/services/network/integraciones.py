"""Verificacion de las integraciones externas desde el propio despliegue: JSON-RPC de cada red y de Ethereum, REST de Aptos, Scan API de Canton,
lista de feeds de Pyth y los precios en cadena (Chainlink y Pyth en Aptos). Solo lecturas; devuelve latencia y error exacto por fuente."""

import asyncio
import dataclasses
import time

from ...pipelines.collectors.base import ClienteHTTP
from ...pipelines.collectors.precios import ServicioPrecios
from ...utils.cache import CacheTTL

REINTENTOS = 1
TIMEOUT_S = 12
TTL_CACHE_S = 30
AVISO_LIMITE = "la fuente respondio pero limita por IP (HTTP 429); el colector de la red comparte esa cuota. No es una caida: revisa /api/salud"


class VerificadorIntegraciones:
    def __init__(self, settings, transporte=None):
        self.settings = dataclasses.replace(settings, http_reintentos=REINTENTOS, http_timeout_s=TIMEOUT_S, http_backoff_base_s=0.2)
        self.transporte = transporte
        self.cache = CacheTTL(max_entradas=1, ttl_s=TTL_CACHE_S)

    async def _medir(self, id_, tipo, url, coro):
        t0 = time.perf_counter()
        try:
            detalle = await coro
            return {"id": id_, "tipo": tipo, "url": url, "estado": "ok", "ok": True,
                    "latencia_ms": round((time.perf_counter() - t0) * 1000), "detalle": detalle}
        except Exception as exc:
            limitado = "HTTP 429" in str(exc)
            fila = {"id": id_, "tipo": tipo, "url": url, "estado": "limitado" if limitado else "error", "ok": False,
                    "latencia_ms": round((time.perf_counter() - t0) * 1000), "error": f"{type(exc).__name__}: {exc}"}
            if limitado:
                fila["aviso"] = AVISO_LIMITE
            return fila

    async def verificar(self):
        hit = self.cache.obtener("ultima")
        if hit is not None:
            return {**hit, "desde_cache": True}
        resultado = await self._verificar()
        self.cache.guardar("ultima", resultado)
        return resultado

    async def _verificar(self):
        s = self.settings
        http = ClienteHTTP(s, transport=self.transporte)
        precios = ServicioPrecios(s, http)
        try:
            async def bloque(url):
                return {"bloque": int(await http.rpc(url, "eth_blockNumber"), 16)}

            async def aptos():
                d = await http.get(s.rest_aptos)
                return {"altura_bloque": d.get("block_height"), "chain_id": d.get("chain_id"), "con_clave": bool(s.aptos_api_key)}

            async def canton_dso():
                d = await http.get(f"{s.scan_canton}/v0/dso")
                return {"claves": sorted(d)[:5]}

            async def canton_eventos():
                d = await http.post(f"{s.scan_canton}/v0/events", json={"page_size": 1})
                return {"eventos": len(d.get("events", []))}

            async def hermes():
                lista = await http.get(f"{s.hermes_pyth}/v2/price_feeds", params={"query": "APT/USD", "asset_type": "crypto"})
                return {"feeds": len(lista)}

            async def precio(activo):
                p = await precios.precio(activo)
                return {"usd": p["usd"], "edad_s": round(time.time() - p["publicado"]), "congelado": p["congelado"]}

            tareas = [self._medir(f"rpc_{r}", "json-rpc", u, bloque(u)) for r, u in (
                ("tempo", s.rpc_tempo), ("polygon", s.rpc_polygon), ("celo", s.rpc_celo), ("arbitrum", s.rpc_arbitrum),
                ("ethereum", s.rpc_ethereum), ("ethereum_respaldo", s.rpc_ethereum_respaldo))]
            tareas += [
                self._medir("aptos_rest", "rest", s.rest_aptos, aptos()),
                self._medir("canton_dso", "rest", f"{s.scan_canton}/v0/dso", canton_dso()),
                self._medir("canton_eventos", "rest", f"{s.scan_canton}/v0/events", canton_eventos()),
                self._medir("pyth_hermes", "rest", s.hermes_pyth, hermes()),
                self._medir("precio_eth_chainlink_arbitrum", "chainlink", s.rpc_arbitrum, precio("ETH")),
                self._medir("precio_pol_chainlink_polygon", "chainlink", s.rpc_polygon, precio("POL")),
                self._medir("precio_celo_chainlink_celo", "chainlink", s.rpc_celo, precio("CELO")),
                self._medir("precio_apt_pyth_aptos", "pyth", s.rest_aptos, precio("APT")),
            ]
            fuentes = await asyncio.gather(*tareas)
        finally:
            await http.cerrar()
        ok = sum(1 for f in fuentes if f["ok"])
        estado = "ok" if ok == len(fuentes) else ("caido" if ok == 0 else "degradado")
        return {"estado": estado, "ok": ok, "total": len(fuentes), "fuentes": fuentes,
                "fallidas": [f["id"] for f in fuentes if f["estado"] == "error"],
                "limitadas": [f["id"] for f in fuentes if f["estado"] == "limitado"], "desde_cache": False}
