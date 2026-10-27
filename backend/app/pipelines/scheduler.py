"""Orquestador de la recoleccion casi en tiempo real: una tarea asyncio por red y componente (bloques, estado, finalidad), una tarea de calculo
de metricas y otra de poda. Un candado por componente impide ciclos solapados; los fallos aplican backoff y quedan registrados en salud_colector;
al detener la aplicacion todas las tareas se cancelan limpiamente."""

import asyncio
import logging
import time

from ..services.analytics.continuidad import resumen_ciclo
from ..services.analytics.metricas import Contexto, calcular_metricas
from ..utils.tiempo import ahora

log = logging.getLogger("scheduler")
BACKOFF_MAX = 8


class Monitor:
    def __init__(self, settings, repos, colectores, al_actualizar=None):
        self.settings = settings
        self.repos = repos
        self.colectores = colectores
        self.al_actualizar = al_actualizar
        self._tareas = []
        self._candados = {}
        self._previo_c3 = {}
        self.corriendo = False

    def _candado(self, clave):
        return self._candados.setdefault(clave, asyncio.Lock())

    async def ejecutar_componente(self, red, componente, fn):
        candado = self._candado((red, componente))
        if candado.locked():
            return None
        async with candado:
            t0 = time.perf_counter()
            try:
                res = await fn()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.repos["salud"].fallo(red, componente, f"{type(exc).__name__}: {exc}")
                log.warning("%s/%s fallo: %s", red, componente, exc)
                return None
            self.repos["salud"].ok(red, componente, (time.perf_counter() - t0) * 1000)
            return res

    async def _bucle(self, red, componente, fn, intervalo, retardo_inicial=0.0):
        await asyncio.sleep(retardo_inicial)
        fallos = 0
        while True:
            ok = await self.ejecutar_componente(red, componente, fn) is not None
            fallos = 0 if ok else fallos + 1
            await asyncio.sleep(intervalo * min(2 ** fallos, BACKOFF_MAX) if fallos else intervalo)

    async def ciclo_bloques(self, red):
        res = await self.colectores[red].ciclo_bloques()
        self._acumular_continuidad(red, res)
        return res

    def _acumular_continuidad(self, red, res):
        if red == "canton":
            puntos = res.get("latidos") or []
            exigir = False
        else:
            puntos = [(m["numero"], m["ts"]) for m in res.get("muestras", [])]
            exigir = True
        if not puntos:
            return
        resumen = resumen_ciclo(puntos, self._previo_c3.get(red), exigir)
        self._previo_c3[red] = puntos[-1]
        if resumen["n"] or resumen["saltados"]:
            self.repos["estado"].guardar(red, "c3_ciclo", resumen)

    def calcular_todas(self):
        ctx = Contexto(self.settings, self.repos["muestras"], self.repos["estado"], ahora(), self.repos.get("anclajes"))
        total = 0
        for red in self.colectores:
            try:
                metricas = calcular_metricas(red, ctx)
            except Exception as exc:
                self.repos["salud"].fallo(red, "metricas", f"{type(exc).__name__}: {exc}")
                log.exception("calculo de metricas de %s", red)
                continue
            self.repos["metricas"].guardar(metricas)
            self.repos["salud"].ok(red, "metricas")
            total += len(metricas)
        if self.al_actualizar:
            self.al_actualizar()
        return total

    async def _bucle_metricas(self):
        await asyncio.sleep(min(10.0, self.settings.intervalo_metricas_s))
        while True:
            try:
                await asyncio.to_thread(self.calcular_todas)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("ciclo de metricas")
            await asyncio.sleep(self.settings.intervalo_metricas_s)

    async def _bucle_poda(self):
        while True:
            await asyncio.sleep(3600)
            t = ahora()
            s = self.settings
            try:
                await asyncio.to_thread(self.repos["muestras"].podar, t - s.ventana_distribucion_s * 1.1,
                                        t - s.ventana_finalidad_s * 1.1, t - s.ventana_continuidad_s * 1.1,
                                        t - s.ventana_continuidad_s * 1.1)
            except Exception:
                log.exception("poda")

    def iniciar(self):
        if self.corriendo:
            return
        self.corriendo = True
        s = self.settings
        for i, red in enumerate(self.colectores):
            c = self.colectores[red]
            desfase = i * 1.5
            self._tareas.append(asyncio.create_task(
                self._bucle(red, "bloques", lambda r=red: self.ciclo_bloques(r), s.intervalo_bloques(red), desfase)))
            self._tareas.append(asyncio.create_task(
                self._bucle(red, "estado", c.ciclo_estado, s.intervalo_estado_s, desfase / 2)))
            if red == "tempo":
                self._tareas.append(asyncio.create_task(
                    self._bucle(red, "finalidad", c.ciclo_finalidad, s.intervalo_finalidad_s, 3.0)))
            if hasattr(c, "ciclo_anclaje"):
                self._tareas.append(asyncio.create_task(
                    self._bucle(red, "anclaje", c.ciclo_anclaje, s.intervalo_anclaje_s, desfase + 5.0)))
        self._tareas.append(asyncio.create_task(self._bucle_metricas()))
        self._tareas.append(asyncio.create_task(self._bucle_poda()))

    async def detener(self):
        for t in self._tareas:
            t.cancel()
        await asyncio.gather(*self._tareas, return_exceptions=True)
        self._tareas.clear()
        self.corriendo = False
