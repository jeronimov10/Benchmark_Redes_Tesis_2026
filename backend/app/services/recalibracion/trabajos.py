"""Recalibracion bajo demanda (boton). Tempo, Aptos y Canton: ejecuta el pipeline de benchmark por lotes (recoleccion, calculo, entregables) en un
subproceso aislado y, al terminar, reconstruye sus perfiles de linea base en SQLite. Polygon, Celo y Arbitrum: relleno por lotes de una ventana
reciente (bloques, pagos y anclaje en Ethereum) que acelera sus metricas en vivo; su linea base de 90 dias (tesis) no se modifica. Un solo
trabajo a la vez, con avance y cancelacion."""

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
REDES_EVM = tuple(r for r in REDES if r not in REDES_TEMPO_APTOS_CANTON)
MINUTOS_EVM_DEFECTO = 10


class RecalibracionOcupada(Exception):
    pass


class ServicioRecalibracion:
    def __init__(self, settings, trabajos_repo, perfiles_repo, al_terminar=None, colectores=None, calcular_metricas=None):
        self.settings = settings
        self.trabajos = trabajos_repo
        self.perfiles = perfiles_repo
        self.al_terminar = al_terminar
        self.colectores = colectores or {}
        self.calcular_metricas = calcular_metricas
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

    def alcance(self):
        return {
            "recalibra": list(REDES_TEMPO_APTOS_CANTON),
            "rellena": [r for r in REDES_EVM if r in self.colectores],
            "no_disponible": [r for r in REDES_EVM if r not in self.colectores],
            "motivo_no_disponible": "el colector de esa red no esta activo en este despliegue (REDES_ACTIVAS)",
            "nota_rellena": "relleno por lotes de una ventana reciente (bloques, pagos y anclaje en Ethereum) para acelerar las metricas en vivo; "
                            "la linea base de 90 dias de la tesis no se modifica",
            "no_resuelve": ["aptos.B2 (imposible por HTTP)", "aptos.D2 (definicion A-5 pendiente)",
                            "polygon/celo/arbitrum: B3, D2, D3 (definiciones de la tesis no reproducibles) y B2b de Celo y Arbitrum"],
        }

    async def iniciar(self, peticion):
        if self.ocupado:
            raise RecalibracionOcupada("ya hay una recalibracion en curso")
        solicitadas = peticion.redes or list(REDES_TEMPO_APTOS_CANTON) + [r for r in REDES_EVM if r in self.colectores]
        validas = [r for r in solicitadas if r in REDES_TEMPO_APTOS_CANTON or r in self.colectores]
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
        bench = [r for r in validas if r in REDES_TEMPO_APTOS_CANTON]
        evm = [r for r in validas if r in REDES_EVM]
        notas = []
        try:
            peso_bench = 0.6 if bench and evm else (0.94 if bench else 0.0)
            if bench:
                for red in ("tempo", "aptos", "canton"):
                    (directorio / "resultados" / "raw" / red).mkdir(parents=True, exist_ok=True)
                self.trabajos.actualizar(id_, etapa="benchmark", progreso=0.02)
                codigo, cola = await asyncio.to_thread(self._correr_benchmark, id_, directorio, p, peso_bench)
                if self._cancelado:
                    self.trabajos.actualizar(id_, estado="cancelado", fin=ahora(), etapa="cancelado", log_tail=cola)
                    return
                if codigo != 0:
                    self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), etapa="benchmark",
                                             log_tail=f"codigo de salida {codigo}\n{cola}")
                    return
                self.trabajos.actualizar(id_, etapa="perfiles", progreso=peso_bench + 0.01)
                nuevos = perfiles_desde_metrics_csv(directorio / "resultados" / "metrics.csv")
                elegidos = {r: nuevos[r] for r in bench if r in nuevos}
                if not elegidos:
                    self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), etapa="perfiles",
                                             log_tail="el benchmark no produjo perfiles para las redes solicitadas")
                    return
                version = self.perfiles.reemplazar_redes(elegidos, "recalibracion")
                notas.append(f"perfiles base actualizados (version {version}) para {', '.join(elegidos)}")
            else:
                cola = ""
            if evm:
                resumen, fallidas = await self._rellenar_evm(id_, evm, p, peso_bench)
                if self._cancelado:
                    self.trabajos.actualizar(id_, estado="cancelado", fin=ahora(), etapa="cancelado", log_tail="\n".join(notas + resumen))
                    return
                notas += resumen
                if fallidas and not bench and len(fallidas) == len(evm):
                    self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), etapa="relleno", log_tail="\n".join(notas))
                    return
            omitidas = [r for r in solicitadas if r not in validas]
            if omitidas:
                notas.append(f"no disponible: {', '.join(omitidas)}")
            self.trabajos.actualizar(id_, estado="completado", fin=ahora(), etapa="listo", progreso=1.0,
                                     log_tail="\n".join(notas + ([cola] if cola else [])))
            if self.al_terminar:
                self.al_terminar()
        except Exception as exc:
            self.trabajos.actualizar(id_, estado="fallido", fin=ahora(), log_tail=f"{type(exc).__name__}: {exc}")

    async def _rellenar_evm(self, id_, redes, p, desde):
        minutos = p.minutos_evm or MINUTOS_EVM_DEFECTO
        resumen, fallidas = [], []
        for i, red in enumerate(redes):
            if self._cancelado:
                break
            inicio = desde + (0.94 - desde) * i / len(redes)
            fin = desde + (0.94 - desde) * (i + 1) / len(redes)
            self.trabajos.actualizar(id_, etapa=f"relleno {red}", progreso=inicio)
            col = self.colectores[red]

            def avance(f, inicio=inicio, fin=fin, red=red):
                self.trabajos.actualizar(id_, progreso=inicio + (fin - inicio) * 0.8 * f, etapa=f"relleno {red}")

            try:
                r = await col.rellenar(minutos, progreso=avance, cancelado=lambda: self._cancelado)
                self.trabajos.actualizar(id_, etapa=f"anclaje {red}", progreso=inicio + (fin - inicio) * 0.8)
                a = await col.anclaje.ciclo(consultas=40, recibos=self.settings.anclaje_recibos_objetivo)
                resumen.append(f"{red}: {r['bloques']} bloques y {r['pagos']} pagos de los ultimos {minutos} min "
                               f"({r['segundos_por_bloque']} s/bloque); anclaje: {a['anclajes_nuevos']} publicaciones, "
                               f"{a['costos']} costos; la linea base de 90 dias no se modifica")
            except Exception as exc:
                fallidas.append(red)
                resumen.append(f"{red}: fallo el relleno ({type(exc).__name__}: {exc})")
        if self.calcular_metricas:
            await asyncio.to_thread(self.calcular_metricas)
        return resumen, fallidas

    def _correr_benchmark(self, id_, directorio, p, peso=0.94):
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
                self.trabajos.actualizar(id_, progreso=min(peso, 0.02 + (peso - 0.02) * pasos / PASOS_ESPERADOS),
                                         etapa=linea[4:], log_tail="\n".join(cola))
        codigo = self._proceso.wait()
        self._proceso = None
        return codigo, "\n".join(cola)
