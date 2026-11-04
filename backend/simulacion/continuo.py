"""Panel continuo (P7): reevalua cada ciclo los mismos usuarios con el perfil en vivo para que cualquier cambio de recomendacion solo pueda venir
de la red. Un ciclo con menos de la mitad de las metricas vivas esperadas se guarda como invalido y no entra en los indicadores."""

import asyncio
import logging

from app.utils.tiempo import ahora

from .evaluador import banda1, filtrar
from .personas import panel as generar_panel

LOG = logging.getLogger("simulacion.continuo")
FRACCION_MINIMA_VIVAS = 0.5
PANEL_POR_PERFIL = 10


def _valores(perfiles):
    return {r: {m: d.get("valor") for m, d in p.items()} for r, p in perfiles.items()}


def causa_probable(anterior, actual):
    mejor, delta = None, 0.0
    for red, metricas in actual.items():
        for mid, v in metricas.items():
            previo = anterior.get(red, {}).get(mid)
            if v is None or previo is None or previo == 0:
                continue
            cambio = abs(v - previo) / abs(previo)
            if cambio > delta:
                mejor, delta = f"{red}.{mid}", cambio
    return {"metrica": mejor, "cambio_relativo": round(delta, 4)} if mejor else None


class PanelContinuo:
    def __init__(self, settings, fuentes, evaluador, almacen):
        self.settings = settings
        self.fuentes = fuentes
        self.evaluador = evaluador
        self.almacen = almacen
        self._tarea = None
        self.ultimo_error = None

    @property
    def activo(self):
        return self._tarea is not None and not self._tarea.done()

    def iniciar(self):
        if self.activo:
            return False
        self._tarea = asyncio.get_running_loop().create_task(self._bucle())
        self.almacen.fijar("continuo_activo", True)
        return True

    async def detener(self, persistir=True):
        if persistir:
            self.almacen.fijar("continuo_activo", False)
        if self._tarea is not None:
            self._tarea.cancel()
            try:
                await self._tarea
            except (asyncio.CancelledError, Exception):
                pass
            self._tarea = None

    async def _bucle(self):
        while True:
            inicio = ahora()
            try:
                await self.ciclo()
                self.ultimo_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.ultimo_error = f"{type(exc).__name__}: {exc}"
                LOG.exception("fallo el ciclo del panel continuo")
            await asyncio.sleep(max(1.0, self.settings.sim_intervalo_s - (ahora() - inicio)))

    async def _bandas_base(self, usuarios):
        base = self.fuentes.base()
        version = self.fuentes.version(base)
        guardado = self.almacen.leer("bandas_base")
        if guardado and guardado["version"] == version and guardado["n"] == len(usuarios):
            return guardado["bandas"]
        registros = await self.evaluador.evaluar_varios(filtrar(base), usuarios, self.settings.replicas_monte_carlo)
        bandas = {f"{r['perfil']}:{r['indice']}": list(banda1(r)) for r in registros}
        self.almacen.fijar("bandas_base", {"version": version, "n": len(usuarios), "bandas": bandas})
        return bandas

    async def ciclo(self):
        t = ahora()
        perfiles, procedencia = self.fuentes.vivo()
        if perfiles is None:
            return None
        vivas, esperadas = self.fuentes.vivas(procedencia), self.fuentes.esperadas()
        version = self.fuentes.version(perfiles)
        if esperadas == 0 or vivas < FRACCION_MINIMA_VIVAS * esperadas:
            self.almacen.guardar_ciclo(t, False, vivas, esperadas, version, {"motivo": "menos de la mitad de las metricas vivas esperadas"})
            return {"valido": False, "vivas": vivas, "esperadas": esperadas}
        usuarios = generar_panel(PANEL_POR_PERFIL, self.settings.sim_semilla)
        registros = await self.evaluador.evaluar_varios(filtrar(perfiles), usuarios, self.settings.replicas_monte_carlo)
        bandas = {f"{r['perfil']}:{r['indice']}": list(banda1(r)) for r in registros}
        base = await self._bandas_base(usuarios)
        valores = _valores(perfiles)
        anterior = self.almacen.leer("ultimo_ciclo", {})
        cambios = {k: v for k, v in bandas.items() if anterior.get("bandas", {}).get(k) not in (None, v)}
        causa = causa_probable(anterior.get("valores", {}), valores) if cambios else None
        self.almacen.guardar_ciclo(t, True, vivas, esperadas, version, {
            "bandas": bandas, "cambios": sorted(cambios), "causa": causa,
            "distintos_de_base": sorted(k for k, v in bandas.items() if base.get(k) != v),
            "ajuste_req": {f"{r['perfil']}:{r['indice']}": r["ajuste_requisito"] for r in registros}})
        self.almacen.fijar("ultimo_ciclo", {"bandas": bandas, "valores": valores, "ts": t})
        return {"valido": True, "vivas": vivas, "esperadas": esperadas, "cambios": len(cambios)}

    def estado(self):
        conteo = self.almacen.conteo_ciclos()
        ultimo = self.almacen.ultimo_ciclo()
        return {"activo": self.activo, "ciclos": conteo["total"], "ciclos_validos": conteo["validos"],
                "intervalo_s": self.settings.sim_intervalo_s, "ultimo_ciclo_ts": ultimo["ts"] if ultimo else None,
                "ultimo_error": self.ultimo_error}
