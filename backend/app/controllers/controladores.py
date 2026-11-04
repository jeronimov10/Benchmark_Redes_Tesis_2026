"""Controladores (C de MVC): validan parametros, delegan en los servicios y traducen errores de dominio a respuestas HTTP consistentes.
No contienen logica de recoleccion ni del modelo de decision."""

import asyncio
import hmac

from fastapi import HTTPException
from fastapi.responses import FileResponse

from ..models.dominio import PeticionLote, PeticionModelo, PeticionRecalibracion
from ..services.network.registry import REDES
from ..services.recalibracion.trabajos import RecalibracionOcupada
from ..utils.tiempo import ahora, iso
from simulacion.servicio import LoteOcupado


class ControladorSalud:
    def __init__(self, c):
        self.c = c

    def estado(self):
        c = self.c
        salud = c.servicio_instantanea.construir()
        redes = {r["id"]: r["salud"]["estado"] for r in salud["redes"]}
        t = ahora()
        return {
            "estado": "ok" if all(v == "ok" for v in redes.values()) else ("degradado" if any(v in ("ok", "degradada") for v in redes.values()) else "caido"),
            "hora": iso(t), "base_de_datos": {"ruta": str(c.db.ruta), "version_esquema": c.db.version(),
                                              "muestras": c.repos["muestras"].conteos()},
            "monitor": {"corriendo": c.monitor.corriendo, "colectores_activos": c.settings.colectores_activos,
                        "redes": list(c.colectores)},
            "redes": redes, "detalle": {r["id"]: r["salud"] for r in salud["redes"]},
            "cache": {"entradas_recomendaciones": len(c.recomendador.cache), "aciertos": c.recomendador.cache.aciertos,
                      "fallos": c.recomendador.cache.fallos},
            "frescura": salud["frescura"],
        }


class ControladorRedes:
    def __init__(self, c):
        self.c = c

    def listar(self):
        return {"redes": [{"id": k, **{x: v[x] for x in ("nombre", "responsable", "familia", "fuente", "metricas_vivo", "metricas_base")}}
                          for k, v in REDES.items()],
                "activas": list(self.c.colectores)}


class ControladorMediciones:
    def __init__(self, c):
        self.c = c

    def todas(self):
        return self.c.servicio_instantanea.construir()

    def una(self, red):
        if red not in REDES:
            raise HTTPException(status_code=404, detail=f"red desconocida: {red}")
        inst = self.c.servicio_instantanea.construir()
        datos = next(r for r in inst["redes"] if r["id"] == red)
        desde = ahora() - self.c.settings.ventana_distribucion_s
        series = {m["id"]: self.c.repos["metricas"].serie(red, m["id"], desde, 120) for m in datos["metricas"] if m["origen"] == "vivo"}
        return {"generado_en": inst["generado_en"], "version_perfil": inst["version_perfil"], "red": datos, "series": series}


class ControladorModelo:
    def __init__(self, c):
        self.c = c

    def info(self):
        return self.c.recomendador.info()

    async def ejecutar(self, p: PeticionModelo):
        entrada = p.model_dump()
        if p.accion == "interpretar":
            return await asyncio.to_thread(self.c.recomendador.interpretar, entrada)
        return await self.c.recomendador.recomendar_async(entrada)


class ControladorRecalibracion:
    def __init__(self, c):
        self.c = c

    async def iniciar(self, p: PeticionRecalibracion):
        if p.redes:
            desconocidas = [r for r in p.redes if r not in REDES]
            if desconocidas:
                raise HTTPException(status_code=422, detail=f"redes desconocidas: {desconocidas}")
        try:
            return await self.c.recalibracion.iniciar(p)
        except RecalibracionOcupada as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    def estado(self):
        return self.c.recalibracion.estado()

    async def cancelar(self):
        if not await self.c.recalibracion.cancelar():
            raise HTTPException(status_code=409, detail="no hay una recalibracion en curso")
        return {"cancelando": True}


class ControladorIntegraciones:
    def __init__(self, c):
        self.c = c

    async def verificar(self):
        return await self.c.integraciones.verificar()


class ControladorSimulacion:
    def __init__(self, c):
        self.c = c

    def autorizar(self, authorization):
        token = self.c.settings.simulacion_token
        if not token:
            return
        entregado = (authorization or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(entregado.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="token invalido o ausente (Authorization: Bearer <SIMULACION_TOKEN>)")

    def estado(self):
        return self.c.simulacion.estado()

    async def iniciar_lote(self, p: PeticionLote):
        try:
            return await self.c.simulacion.iniciar_lote(p)
        except LoteOcupado as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    async def cancelar_lote(self):
        if not await self.c.simulacion.cancelar():
            raise HTTPException(status_code=409, detail="no hay un lote en curso")
        return {"cancelando": True}

    def iniciar_continuo(self):
        return {"iniciado": self.c.simulacion.iniciar_continuo(), **self.c.simulacion.estado()["continuo"]}

    async def detener_continuo(self):
        return {"detenido": await self.c.simulacion.detener_continuo()}

    async def informe(self):
        return {"archivos": await self.c.simulacion.generar_informe()}

    def archivos(self):
        return {"archivos": self.c.simulacion.archivos()}

    def archivo(self, nombre):
        ruta = self.c.simulacion.ruta_archivo(nombre)
        if ruta is None:
            raise HTTPException(status_code=404, detail=f"archivo no disponible: {nombre}")
        return FileResponse(ruta, filename=nombre)
