"""Instantanea de mediciones por red: une el perfil efectivo (linea base o en vivo) con el estado de cada metrica en vivo y la salud de los
colectores. Es lo que consume la vista de monitoreo; cada metrica indica su origen, edad, ventana y por que no esta en vivo cuando aplica."""

import sys

from ...config import RAIZ_BACKEND
from ...utils.cache import CacheTTL
from ...utils.tiempo import ahora, iso
from .registry import REDES

sys.path.insert(0, str(RAIZ_BACKEND / "modelo"))
import modelo  # noqa: E402

COMPONENTES_CRITICOS = ("bloques",)


class ServicioInstantanea:
    def __init__(self, settings, servicio_perfiles, metricas_repo, salud_repo, muestras_repo):
        self.settings = settings
        self.perfiles = servicio_perfiles
        self.metricas = metricas_repo
        self.salud = salud_repo
        self.muestras = muestras_repo
        self.cache = CacheTTL(max_entradas=8, ttl_s=settings.cache_ttl_s)

    def invalidar(self):
        self.cache.invalidar()

    def salud_red(self, red, filas):
        t = ahora()
        comps = []
        for f in filas:
            if f["red"] != red:
                continue
            ok = f["ultimo_ok"]
            comps.append({"componente": f["componente"], "ultimo_ok": iso(ok), "edad_ok_s": (t - ok) if ok else None,
                          "ultimo_error": iso(f["ultimo_error"]), "error": f["error"],
                          "fallos_consecutivos": f["fallos_consecutivos"], "latencia_ms": f["latencia_ms"]})
        if not comps:
            estado = "sin_datos"
        elif any(c["fallos_consecutivos"] > 0 and c["componente"] in COMPONENTES_CRITICOS for c in comps):
            estado = "caida"
        elif any(c["fallos_consecutivos"] > 0 for c in comps):
            estado = "degradada"
        else:
            estado = "ok"
        return {"estado": estado, "componentes": comps}

    def construir(self):
        hit = self.cache.obtener("instantanea")
        if hit is not None:
            return hit
        t = ahora()
        efectivo, procedencia = self.perfiles.construir("vivo")
        version = self.perfiles.version(efectivo)
        vivos = {(m["red"], m["metrica"]): m for m in self.metricas.ultimas()}
        salud = self.salud.todos()
        conteos = self.muestras.conteos()
        redes = []
        for red, defn in REDES.items():
            perfil = efectivo.get(red, {})
            metricas = []
            for mid in modelo.METRICAS:
                d = perfil.get(mid)
                prov = procedencia.get(red, {}).get(mid)
                vivo = vivos.get((red, mid))
                metricas.append({
                    "id": mid, "bloque": modelo.METRICAS[mid]["bloque"],
                    "valor": d.get("valor") if d else None, "sigma": d.get("sigma") if d else None,
                    "cota_inferior": bool(d.get("cota_inferior")) if d else False,
                    "origen": prov["origen"] if prov else None,
                    "fuente": prov["fuente"] if prov else None,
                    "ts": iso(prov["ts"]) if prov else None, "edad_s": prov["edad_s"] if prov else None,
                    "n": prov.get("n") if prov else None, "ventana_s": prov.get("ventana_s") if prov else None,
                    "nota": d.get("nota") if d else None,
                    "vivo": None if vivo is None else {
                        "estado": vivo["estado"], "valor": vivo["valor"], "n": vivo["n"], "ts": iso(vivo["ts"]),
                        "edad_s": t - vivo["ts"], "nota": vivo["nota"], "unidad": vivo["unidad"]},
                    "razon_solo_base": defn["metricas_base"].get(mid),
                    "estado_vivo_esperado": mid in defn["metricas_vivo"],
                })
            redes.append({
                "id": red, "nombre": defn["nombre"], "responsable": defn["responsable"], "fuente": defn["fuente"],
                "salud": self.salud_red(red, salud), "muestras": conteos.get(red, {}), "metricas": metricas,
                "metricas_vivo_activas": sum(1 for m in metricas if m["origen"] == "vivo"),
            })
        res = {"generado_en": iso(t), "version_perfil": version, "frescura": self.perfiles.frescura(procedencia),
               "obsolescencia_s": self.settings.obsolescencia_s, "redes": redes}
        self.cache.guardar("instantanea", res)
        return res
