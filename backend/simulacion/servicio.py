"""Servicio del banco de usuarios simulados: un lote P1-P6 a la vez (tarea asincrona con avance y cancelacion), el panel continuo P7 que se
reanuda tras un reinicio, y la entrega de los archivos del informe. Lee los perfiles de la aplicacion sin escribir en su base."""

import asyncio
import logging
from pathlib import Path

from app.utils.tiempo import ahora

from . import experimentos, informe
from .almacen import Almacen
from .continuo import PanelContinuo
from .evaluador import Evaluador
from .fuentes import Fuentes

LOG = logging.getLogger("simulacion")


class LoteOcupado(Exception):
    pass


class ServicioSimulacion:
    def __init__(self, settings, servicio_perfiles=None, redes_activas=None):
        self.settings = settings
        self.fuentes = Fuentes(settings, servicio_perfiles, redes_activas)
        self.evaluador = Evaluador(settings.sim_procesos)
        self._almacen = None
        self._panel = None
        self._tarea = None
        self._cancelado = False
        self._lote = None

    @property
    def almacen(self):
        if self._almacen is None:
            self._almacen = Almacen(self.settings.ruta_sim_db)
            self._almacen.db.ejecutar("UPDATE corridas SET estado='interrumpido', fin=? WHERE estado='en_curso'", (ahora(),))
        return self._almacen

    @property
    def panel(self):
        if self._panel is None:
            self._panel = PanelContinuo(self.settings, self.fuentes, self.evaluador, self.almacen)
        return self._panel

    @property
    def ocupado(self):
        return self._tarea is not None and not self._tarea.done()

    def reanudar(self):
        ruta = self.settings.ruta_sim_db
        if str(ruta) != ":memory:" and Path(ruta).exists() and self.almacen.leer("continuo_activo", False):
            self.panel.iniciar()
            LOG.info("panel continuo reanudado")

    async def cerrar(self):
        if self._panel is not None:
            await self._panel.detener(persistir=False)
        if self.ocupado:
            self._cancelado = True
            self._tarea.cancel()
        self.evaluador.cerrar()
        if self._almacen is not None:
            self._almacen.cerrar()
            self._almacen = None

    async def iniciar_lote(self, p):
        if self.ocupado:
            raise LoteOcupado("ya hay un lote en curso")
        config = p.model_dump()
        config["semilla"] = p.semilla if p.semilla is not None else self.settings.sim_semilla
        config["replicas"] = p.replicas or self.settings.replicas_monte_carlo
        id_ = self.almacen.crear_corrida(config)
        self._cancelado = False
        self._lote = {"id": id_, "estado": "en_curso", "etapa": "iniciando", "progreso": 0.0, "evaluaciones": 0, "inicio": ahora(), "fin": None, "log": []}
        self._tarea = asyncio.get_running_loop().create_task(self._ejecutar(id_, config))
        return {"id": id_, "config": config}

    async def esperar(self):
        if self._tarea is not None:
            await self._tarea

    async def cancelar(self):
        if not self.ocupado:
            return False
        self._cancelado = True
        return True

    def _contexto(self, config):
        lote = self._lote

        def guardar(prueba, fuente, escenario, registros):
            self.almacen.guardar_evaluaciones(lote["id"], prueba, fuente, escenario, registros)

        def contar():
            lote["evaluaciones"] += 1

        def etapa(texto):
            lote["etapa"] = texto
            lote["log"] = (lote["log"] + [texto])[-30:]

        return experimentos.Contexto(
            evaluador=self.evaluador, replicas=config["replicas"], tope=config["tope"], panel_por_perfil=config["panel_por_perfil"],
            semilla=config["semilla"], niveles_replicas=tuple(config["niveles_replicas"]), guardar=guardar,
            cancelado=lambda: self._cancelado, al_evaluar=contar, al_etapa=etapa)

    async def _ejecutar(self, id_, config):
        lote = self._lote
        ctx = self._contexto(config)
        fuentes = ["base", "vivo"] if config["fuente"] == "ambas" else [config["fuente"]]
        pruebas = set(config["pruebas"])
        fases = [f for f in (("P1P2", pruebas & {"P1", "P2"}), ("REF", pruebas & {"P3", "P4", "P5"}), ("P3P4", pruebas & {"P3", "P4"}),
                             ("P5", pruebas & {"P5"}), ("P6", pruebas & {"P6"})) if f[1]]
        total, hechas = max(1, len(fuentes) * len(fases)), 0
        versiones, estado = {}, "completado"
        try:
            for fuente in fuentes:
                perfiles, procedencia = self.fuentes.por_fuente(fuente)
                if perfiles is None or (fuente == "vivo" and self.fuentes.vivas(procedencia) == 0):
                    ctx.notas.append(f"{fuente}: sin metricas vivas validas y frescas; se omite")
                    hechas += len(fases)
                    continue
                versiones[fuente] = self.fuentes.version(perfiles)
                if fuente == "vivo":
                    ctx.notas.append(f"vivo: {self.fuentes.vivas(procedencia)} de {self.fuentes.esperadas()} metricas vivas esperadas")
                for nombre, _ in fases:
                    if nombre == "P1P2":
                        await experimentos.muestreo(ctx, fuente, perfiles)
                    elif nombre == "REF":
                        await experimentos.referencia(ctx, fuente, perfiles)
                    elif nombre == "P3P4":
                        await experimentos.contrafactuales(ctx, fuente, perfiles)
                    elif nombre == "P5":
                        await experimentos.sensibilidad(ctx, fuente, perfiles)
                    elif nombre == "P6":
                        await experimentos.convergencia(ctx, fuente, perfiles)
                    hechas += 1
                    lote["progreso"] = round(hechas / total, 3)
        except experimentos.Cancelado:
            estado = "cancelado"
        except asyncio.CancelledError:
            estado = "interrumpido"
            raise
        except Exception as exc:
            estado = "fallido"
            lote["log"].append(f"{type(exc).__name__}: {exc}")
            LOG.exception("fallo el lote de simulacion")
        finally:
            manifiesto = {"notas": ctx.notas, "version_perfil": versiones, "commit": informe._commit(), "evaluaciones": lote["evaluaciones"]}
            try:
                self.almacen.cerrar_corrida(id_, estado, manifiesto, "\n".join(lote["log"]))
                if estado == "completado":
                    await asyncio.to_thread(informe.generar, self.almacen, self.settings.dir_simulacion, self.settings, id_)
            except Exception:
                LOG.exception("no se pudo cerrar la corrida")
            lote.update({"estado": estado, "fin": ahora(), "progreso": 1.0 if estado == "completado" else lote["progreso"], "etapa": estado})

    def estado(self):
        lote = self._lote
        if lote is None and (str(self.settings.ruta_sim_db) == ":memory:" or not Path(self.settings.ruta_sim_db).exists()):
            return {"lote": None, "ocupado": False, "continuo": self._estado_continuo_vacio()}
        if lote is None:
            c = self.almacen.ultima_corrida()
            if c:
                lote = {"id": c["id"], "estado": c["estado"], "etapa": c["estado"], "inicio": c["inicio"], "fin": c["fin"],
                        "log": (c["log"] or "").splitlines()[-30:], "config": c["config"]}
        return {"lote": lote, "ocupado": self.ocupado, "continuo": self.panel.estado()}

    def _estado_continuo_vacio(self):
        return {"activo": False, "ciclos": 0, "ciclos_validos": 0, "intervalo_s": self.settings.sim_intervalo_s, "ultimo_ciclo_ts": None, "ultimo_error": None}

    def iniciar_continuo(self):
        return self.panel.iniciar()

    async def detener_continuo(self):
        if self._panel is None and not self.almacen.leer("continuo_activo", False):
            return False
        await self.panel.detener()
        return True

    async def generar_informe(self):
        return await asyncio.to_thread(informe.generar, self.almacen, self.settings.dir_simulacion, self.settings)

    def archivos(self):
        d = self.settings.dir_simulacion
        if not d.exists():
            return []
        return [{"nombre": p.name, "bytes": p.stat().st_size, "modificado": p.stat().st_mtime}
                for p in sorted(d.iterdir()) if p.name in informe.ARCHIVOS]

    def ruta_archivo(self, nombre):
        if nombre not in informe.ARCHIVOS:
            return None
        ruta = self.settings.dir_simulacion / nombre
        return ruta if ruta.exists() else None
