"""Recalibracion bajo demanda (boton): ejecuta el pipeline de benchmark por lotes (recoleccion, calculo, entregables) en un subproceso aislado,
sigue su avance, permite cancelarlo y, al terminar, reconstruye los perfiles de linea base de Tempo, Aptos y Canton en SQLite. Un solo trabajo a la vez."""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

from ...config import RAIZ_REPO
from ...utils.tiempo import ahora
from ..analytics.baseline import perfiles_desde_metrics_csv
from ..network.registry import REDES, REDES_TEMPO_APTOS_CANTON

PASOS_ESPERADOS = 8
MINUTOS_ATRAS_CANTON = 15


class RecalibracionOcupada(Exception):
    pass


class ServicioRecalibracion:
    def __init__(self, settings, trabajos_repo, perfiles_repo, al_terminar=None):
        self.settings = settings
        self.trabajos = trabajos_repo
        self.perfiles = perfiles_repo
        self.al_terminar = al_terminar
        self._proceso = None
        self._tarea = None
        self._cancelado = False
        self.trabajos.marcar_huerfanos()

    @property
    def ocupado(self):
        return self._tarea is not None and not self._tarea.done()

    def estado(self):
        t = self.trabajos.ultimo()
        if not t:
            return {"trabajo": None, "ocupado": False, "alcance": self.alcance()}
        t["redes"] = json.loads(t["redes"]) if t.get("redes") else []
        return {"trabajo": t, "ocupado": self.ocupado, "alcance": self.alcance()}

    @staticmethod
    def alcance():
        return {
            "recalibra": list(REDES_TEMPO_APTOS_CANTON),
            "no_disponible": [r for r in REDES if r not in REDES_TEMPO_APTOS_CANTON],
            "motivo_no_disponible": "el colector por lotes de Polygon, Celo y Arbitrum no esta en este repositorio; sus metricas en vivo se acumulan normalmente",
            "no_resuelve": ["aptos.B2 (imposible por HTTP)", "aptos.D2 (definicion A-5 pendiente)"],
        }

    async def iniciar(self, peticion):
        if self.ocupado:
            raise RecalibracionOcupada("ya hay una recalibracion en curso")
        solicitadas = peticion.redes or list(REDES_TEMPO_APTOS_CANTON)
        validas = [r for r in solicitadas if r in REDES_TEMPO_APTOS_CANTON]
        id_ = uuid.uuid4().hex[:12]
        self.trabajos.crear(id_, solicitadas)
        self._cancelado = False
        self._tarea = asyncio.create_task(self._ejecutar(id_, validas, solicitadas, peticion))
        return {"id": id_, "redes": validas, "no_disponible": [r for r in solicitadas if r not in validas]}

    async def cancelar(self):
        if not self.ocupado:
            return False
        self._cancelado = True
        if self._proceso is not None:
            self._proceso.terminate()
        return True

    async def _ejecutar(self, id_, validas, solicitadas, p):
        directorio = self.settings.db_path.parent / "recalibracion" / id_
        try:
            for red in ("tempo", "aptos", "canton"):
                (directorio / "resultados" / "raw" / red).mkdir(parents=True, exist_ok=True)
            self.trabajos.actualizar(id_, etapa="benchmark", progreso=0.02)
            codigo, cola = await asyncio.to_thread(self._correr_benchmark, id_, directorio, p)
            if self._cancelado:
                self.trabajos.actualizar(id_, estado="cancelado", fin=ahora(), etapa="cancelado", log_tail=cola)
                return
            if codigo != 0:
                self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), etapa="benchmark",
                                         log_tail=f"codigo de salida {codigo}\n{cola}")
                return
            self.trabajos.actualizar(id_, etapa="perfiles", progreso=0.95)
            nuevos = perfiles_desde_metrics_csv(directorio / "resultados" / "metrics.csv")
            elegidos = {r: nuevos[r] for r in validas if r in nuevos}
            if not elegidos:
                self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), etapa="perfiles",
                                         log_tail="el benchmark no produjo perfiles para las redes solicitadas")
                return
            version = self.perfiles.reemplazar_redes(elegidos, "recalibracion")
            nota = f"perfiles base actualizados (version {version}) para {', '.join(elegidos)}"
            omitidas = [r for r in solicitadas if r not in REDES_TEMPO_APTOS_CANTON]
            if omitidas:
                nota += f"; no disponible: {', '.join(omitidas)}"
            self.trabajos.actualizar(id_, estado="completado", fin=ahora(), etapa="listo", progreso=1.0,
                                     log_tail=f"{nota}\n{cola}")
            if self.al_terminar:
                self.al_terminar()
        except Exception as exc:
            self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), log_tail=f"{type(exc).__name__}: {exc}")

    def _correr_benchmark(self, id_, directorio, p):
        entorno = dict(os.environ)
        entorno["PYTHONIOENCODING"] = "utf-8"
        entorno["PYTHONUNBUFFERED"] = "1"
        if p.bloques_tempo:
            entorno["N_BLOCKS_TEMPO"] = str(p.bloques_tempo)
        if p.bloques_aptos:
            entorno["N_BLOCKS_APTOS"] = str(p.bloques_aptos)
        inicio = datetime.now(timezone.utc) - timedelta(minutes=MINUTOS_ATRAS_CANTON)
        entorno["CANTON_START_AFTER"] = inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
        if p.paginas_canton:
            entorno["MAX_PAGES"] = str(p.paginas_canton)
        script = str(RAIZ_REPO / "backend" / "benchmark" / "main.py")
        pasos = 0
        cola = []
        self._proceso = subprocess.Popen(
            [sys.executable, script, "--collect"], cwd=str(directorio), env=entorno, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for linea in self._proceso.stdout:
            linea = linea.rstrip()
            cola.append(linea)
            cola = cola[-40:]
            if linea.startswith(">>> "):
                pasos += 1
                self.trabajos.actualizar(id_, progreso=min(0.94, 0.02 + 0.92 * pasos / PASOS_ESPERADOS),
                                         etapa=linea[4:], log_tail="\n".join(cola))
        codigo = self._proceso.wait()
        self._proceso = None
        return codigo, "\n".join(cola)
