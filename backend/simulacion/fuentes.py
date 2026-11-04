"""Fuentes de perfiles del banco, de solo lectura: la linea base (modo medicion de la aplicacion) y el perfil en vivo con su procedencia.
Nunca escribe en redes.db ni agrega valores que la aplicacion no tenga."""

from app.services.analytics.baseline import construir_linea_base
from app.services.network.registry import REDES


class Fuentes:
    def __init__(self, settings, servicio_perfiles=None, redes_activas=None):
        self.settings = settings
        self.servicio = servicio_perfiles
        self.redes_activas = tuple(redes_activas) if redes_activas else tuple(REDES)

    def base(self):
        if self.servicio is not None:
            perfiles, _ = self.servicio.construir("medicion")
            if perfiles:
                return perfiles
        return construir_linea_base(self.settings.perfiles_json, self.settings.dir_resultados / "metrics.csv")

    def vivo(self):
        if self.servicio is None:
            return None, None
        return self.servicio.construir("vivo")

    def version(self, perfiles):
        from app.services.decision.perfiles import ServicioPerfiles
        return ServicioPerfiles.version(perfiles)

    def esperadas(self):
        return sum(len(REDES[r]["metricas_vivo"]) for r in self.redes_activas if r in REDES)

    @staticmethod
    def vivas(procedencia):
        return sum(1 for red in procedencia.values() for m in red.values() if m["origen"] == "vivo")

    def por_fuente(self, fuente):
        if fuente == "base":
            return self.base(), None
        perfiles, procedencia = self.vivo()
        return perfiles, procedencia
