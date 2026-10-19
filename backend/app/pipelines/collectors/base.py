"""Cliente HTTP asincrono con timeout, reintentos con backoff exponencial y jitter (429/5xx/red), helpers JSON-RPC y clase base de colectores."""

import asyncio
import random
import ssl
import time
from abc import ABC

import httpx


class ErrorFuente(Exception):
    pass


class _Reintentable(Exception):
    def __init__(self, mensaje, espera=None):
        super().__init__(mensaje)
        self.espera = espera


class ClienteHTTP:
    def __init__(self, settings, transport=None, dormir=asyncio.sleep):
        self.settings = settings
        self._dormir = dormir
        self._cli = httpx.AsyncClient(timeout=settings.http_timeout_s, transport=transport,
                                      verify=ssl.create_default_context(),
                                      headers={"User-Agent": "redes-monitor/1.0"})
        self.ultima_latencia_ms = None

    async def cerrar(self):
        await self._cli.aclose()

    async def solicitar(self, metodo, url, **kw):
        intentos = self.settings.http_reintentos
        ultimo = None
        for i in range(intentos + 1):
            t0 = time.perf_counter()
            try:
                r = await self._cli.request(metodo, url, **kw)
                self.ultima_latencia_ms = (time.perf_counter() - t0) * 1000
                if r.status_code in (429, 500, 502, 503, 504):
                    espera = None
                    if r.headers.get("retry-after", "").isdigit():
                        espera = float(r.headers["retry-after"])
                    raise _Reintentable(f"HTTP {r.status_code}", espera)
                if r.status_code >= 400:
                    raise ErrorFuente(f"HTTP {r.status_code} en {url}: {r.text[:200]}")
                try:
                    return r.json()
                except ValueError as exc:
                    raise ErrorFuente(f"respuesta no JSON de {url}") from exc
            except _Reintentable as exc:
                ultimo = exc
                espera = exc.espera
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                ultimo = exc
                espera = None
            if i == intentos:
                break
            base = self.settings.http_backoff_base_s * (2 ** i)
            await self._dormir(espera if espera is not None else min(60.0, base) * (0.5 + random.random() / 2))
        raise ErrorFuente(f"agotados {intentos + 1} intentos en {url}: {type(ultimo).__name__}: {ultimo}")

    async def get(self, url, **kw):
        return await self.solicitar("GET", url, **kw)

    async def post(self, url, **kw):
        return await self.solicitar("POST", url, **kw)

    async def rpc(self, url, metodo, params=None):
        d = await self.post(url, json={"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or []})
        if not isinstance(d, dict):
            raise ErrorFuente(f"respuesta JSON-RPC inesperada de {url}")
        if d.get("error"):
            raise ErrorFuente(f"{metodo}: {d['error']}")
        return d.get("result")

    async def rpc_lote(self, url, llamadas, tamano=25):
        salida = []
        for i in range(0, len(llamadas), tamano):
            trozo = llamadas[i:i + tamano]
            carga = [{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(trozo)]
            d = await self.post(url, json=carga)
            if not isinstance(d, list):
                raise ErrorFuente(f"lote JSON-RPC rechazado por {url}: {str(d)[:200]}")
            por_id = {x.get("id"): x for x in d}
            for j in range(len(trozo)):
                x = por_id.get(j)
                salida.append(None if (x is None or x.get("error")) else x.get("result"))
        return salida


class Colector(ABC):
    red = ""

    def __init__(self, settings, cliente, repos):
        self.settings = settings
        self.http = cliente
        self.repos = repos

    async def ciclo_bloques(self):
        return {}

    async def ciclo_estado(self):
        return {}

    async def ciclo_finalidad(self):
        return {}

    async def verificar(self):
        return {}
