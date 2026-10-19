"""Contenedor de dependencias: construye base de datos, repositorios, cache, colectores, monitor y servicios de decision/recalibracion,
siembra la linea base la primera vez y los entrega a los controladores. Es el unico lugar donde se ensamblan los componentes."""

from .config import Settings
from .db.connection import Database
from .db.repositorios import (EstadoRepo, MetricasRepo, MuestrasRepo, PerfilesRepo, RecomendacionesRepo, RedesRepo,
                              SaludRepo, TrabajosRepo)
from .pipelines.collectors.aptos import ColectorAptos
from .pipelines.collectors.base import ClienteHTTP
from .pipelines.collectors.canton import ColectorCanton
from .pipelines.collectors.evm import ColectorEVM
from .pipelines.collectors.precios import ServicioPrecios
from .pipelines.collectors.tempo import ColectorTempo
from .pipelines.scheduler import Monitor
from .services.analytics.baseline import REDES_BENCHMARK, REDES_TESIS, perfiles_desde_metrics_csv, perfiles_tesis
from .services.decision.perfiles import ServicioPerfiles
from .services.decision.recomendador import Recomendador
from .services.network.registry import definiciones
from .services.network.snapshot import ServicioInstantanea
from .services.recalibracion.trabajos import ServicioRecalibracion


class Contenedor:
    def __init__(self, settings=None, db=None, transporte_http=None):
        self.settings = settings or Settings()
        self.db = db or Database(self.settings.db_path)
        self.http = ClienteHTTP(self.settings, transport=transporte_http)
        self.repos = {
            "muestras": MuestrasRepo(self.db), "estado": EstadoRepo(self.db), "metricas": MetricasRepo(self.db),
            "salud": SaludRepo(self.db), "trabajos": TrabajosRepo(self.db), "recomendaciones": RecomendacionesRepo(self.db),
            "perfiles": PerfilesRepo(self.db), "redes": RedesRepo(self.db),
        }
        self.precios = ServicioPrecios(self.settings, self.http)
        self.servicio_perfiles = ServicioPerfiles(self.settings, self.repos["perfiles"], self.repos["metricas"])
        self.recomendador = Recomendador(self.settings, self.servicio_perfiles, self.repos["recomendaciones"])
        self.servicio_instantanea = ServicioInstantanea(self.settings, self.servicio_perfiles, self.repos["metricas"],
                                                        self.repos["salud"], self.repos["muestras"])
        self.colectores = self._construir_colectores()
        self.monitor = Monitor(self.settings, self.repos, self.colectores, al_actualizar=self.invalidar_caches)
        self.recalibracion = ServicioRecalibracion(self.settings, self.repos["trabajos"], self.repos["perfiles"],
                                                   al_terminar=self.invalidar_caches)

    def invalidar_caches(self):
        self.recomendador.invalidar()
        self.servicio_instantanea.invalidar()

    def _construir_colectores(self):
        s, h, r = self.settings, self.http, self.repos
        todos = {
            "tempo": lambda: ColectorTempo(s, h, r),
            "aptos": lambda: ColectorAptos(s, h, r, self.precios),
            "canton": lambda: ColectorCanton(s, h, r),
            "polygon": lambda: ColectorEVM("polygon", s, h, r, self.precios),
            "celo": lambda: ColectorEVM("celo", s, h, r, self.precios),
            "arbitrum": lambda: ColectorEVM("arbitrum", s, h, r, self.precios),
        }
        return {red: todos[red]() for red in s.redes_activas if red in todos}

    def sembrar(self):
        self.repos["redes"].sembrar(definiciones())
        if self.repos["perfiles"].vacio():
            self.repos["perfiles"].reemplazar_redes(perfiles_tesis(self.settings.perfiles_json), "perfiles.json")
            todos = perfiles_desde_metrics_csv(self.settings.dir_resultados / "metrics.csv")
            self.repos["perfiles"].reemplazar_redes({r: todos[r] for r in REDES_BENCHMARK}, "metrics.csv")

    def iniciar(self):
        self.sembrar()
        self.recomendador.precalentar()
        if self.settings.colectores_activos:
            self.monitor.iniciar()

    async def detener(self):
        await self.monitor.detener()
        self.recomendador.cerrar()
        await self.http.cerrar()
        self.db.cerrar()
