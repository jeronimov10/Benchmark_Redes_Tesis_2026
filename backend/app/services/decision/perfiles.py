"""Perfil efectivo por red: linea base (medicion larga) sobreescrita por metricas en vivo validas y frescas, con procedencia por metrica."""

import hashlib
import json

from ...models.dominio import EstadoMetrica
from ...utils.tiempo import ahora

ESTADOS_ESTADO = {"B3", "C1", "C2", "C5"}


class ServicioPerfiles:
    def __init__(self, settings, perfiles_repo, metricas_repo):
        self.settings = settings
        self.perfiles = perfiles_repo
        self.metricas = metricas_repo

    def _vigente(self, fila, t):
        if fila["estado"] != EstadoMetrica.VALIDA.value or fila["valor"] is None:
            return False
        limite = self.settings.obsolescencia_estado_s if fila["metrica"] in ESTADOS_ESTADO else self.settings.obsolescencia_s
        return (t - fila["ts"]) <= limite

    def construir(self, modo="vivo"):
        base, origenes_base = self.perfiles.todos()
        t = ahora()
        efectivo = {red: {m: dict(d) for m, d in p.items()} for red, p in base.items()}
        procedencia = {red: {} for red in base}
        for red, p in base.items():
            for mid in p:
                o = origenes_base[red][mid]
                procedencia[red][mid] = {"origen": "base", "fuente": o["origen"], "ts": o["ts"],
                                         "edad_s": t - o["ts"], "estado": "base", "n": None, "ventana_s": None}
        if modo == "vivo":
            for fila in self.metricas.ultimas():
                red, mid = fila["red"], fila["metrica"]
                if red not in efectivo:
                    continue
                if self._vigente(fila, t):
                    nota = f"EN VIVO {fila['fuente']} n={fila['n']} ventana={int(fila['ventana_s'] or 0)}s"
                    if fila["nota"]:
                        nota += f" | {fila['nota']}"
                    d = {"valor": fila["valor"], "nota": nota}
                    if fila["sigma"] is not None:
                        d["sigma"] = fila["sigma"]
                    if fila["cota_inferior"]:
                        d["cota_inferior"] = True
                    efectivo[red][mid] = d
                    procedencia[red][mid] = {"origen": "vivo", "fuente": fila["fuente"], "ts": fila["ts"],
                                             "edad_s": t - fila["ts"], "estado": fila["estado"],
                                             "n": fila["n"], "ventana_s": fila["ventana_s"]}
                else:
                    previo = procedencia[red].get(mid)
                    if previo is not None:
                        previo["vivo_descartado"] = {"estado": fila["estado"], "ts": fila["ts"],
                                                     "edad_s": t - fila["ts"], "nota": fila["nota"]}
        return efectivo, procedencia

    @staticmethod
    def version(perfiles):
        crudo = json.dumps(
            {r: {m: [d.get("valor"), d.get("sigma"), bool(d.get("cota_inferior"))] for m, d in sorted(p.items())}
             for r, p in sorted(perfiles.items())}, sort_keys=True)
        return hashlib.sha1(crudo.encode()).hexdigest()[:12]

    @staticmethod
    def frescura(procedencia):
        edades = [m["edad_s"] for red in procedencia.values() for m in red.values() if m["origen"] == "vivo"]
        vivas = len(edades)
        total = sum(len(r) for r in procedencia.values())
        return {"metricas_vivo": vivas, "metricas_total": total,
                "edad_vivo_max_s": max(edades) if edades else None,
                "edad_vivo_min_s": min(edades) if edades else None}
