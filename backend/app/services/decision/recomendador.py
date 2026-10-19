"""Servicio de recomendacion: envuelve el modelo de la tesis (backend/modelo/modelo.py, sin modificar) con perfiles efectivos,
detalle por red, cache por version de perfil y estado explicito cuando no hay datos suficientes. Solo recomienda; no ejecuta transferencias."""

import asyncio
import json
import sys
from concurrent.futures import ProcessPoolExecutor

from ...config import RAIZ_BACKEND
from ...utils.cache import CacheTTL
from ...utils.tiempo import ahora, iso
from .trabajador import ejecutar_modelo, calentar

sys.path.insert(0, str(RAIZ_BACKEND / "modelo"))
import modelo  # noqa: E402

MEDICION_BASE = "perfiles de linea base: Polygon, Celo y Arbitrum medidos en 90 dias (octubre 2026); Tempo, Aptos y Canton de resultados/metrics.csv"
MINIMO_REDES_CON_DATOS = 2


class _ValorCentral:
    def gauss(self, mu, sigma):
        return mu


def nivel_certidumbre(kappa):
    return "alta" if kappa >= 0.75 else ("media" if kappa >= 0.45 else "baja")


def _contexto(e):
    a = modelo.vector_caso(e["monto_cop"], e["transfronterizo"], e["espera_s"], e["irrevocabilidad"])
    lam, W, kappa, _ = modelo.interpolar(a)
    return lam, W, kappa, max(lam, key=lam.get), e["monto_cop"] / e["trm"]


def detalle_redes(perfiles, e, procedencia):
    _, W, _, dominante, ticket_usd = _contexto(e)
    out = {}
    for red, perfil in perfiles.items():
        metricas = []
        for mid, m in modelo.METRICAS.items():
            d = perfil.get(mid, {})
            valor = d.get("valor")
            metricas.append({
                "id": mid, "bloque": m["bloque"], "direccion": m["dir"],
                "objetivo": modelo.umbral(m["t"], ticket_usd),
                "inaceptable": modelo.umbral(m["w"], ticket_usd),
                "valor": valor, "sigma": d.get("sigma"), "nota": d.get("nota"),
                "cota_inferior": bool(d.get("cota_inferior")),
                "puntaje": modelo.normalizar(mid, valor, ticket_usd) if valor is not None else None,
                "procedencia": procedencia.get(red, {}).get(mid),
            })
        central, por_bloque = modelo.puntuar(perfil, W, ticket_usd, _ValorCentral())
        out[red] = {
            "metricas": metricas, "bloques": por_bloque, "puntaje_central": central,
            "compuertas_falladas": [{"compuerta": c, "motivo": motivo}
                                    for c, motivo in modelo.compuertas(red, perfil, dominante, ticket_usd)],
        }
    return out


def redes_con_datos(perfiles):
    return [r for r, p in perfiles.items() if any(d.get("valor") is not None for d in p.values())]


class Recomendador:
    def __init__(self, settings, servicio_perfiles, recomendaciones_repo=None):
        self.settings = settings
        self.perfiles = servicio_perfiles
        self.repo = recomendaciones_repo
        self.cache = CacheTTL(max_entradas=500)
        self.cache_perfil = CacheTTL(max_entradas=4, ttl_s=settings.cache_ttl_s)
        self._pool = None
        self._en_vuelo = {}

    def _obtener_pool(self):
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=2)
        return self._pool

    def precalentar(self):
        self._obtener_pool().submit(calentar)

    def cerrar(self):
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None

    def invalidar(self):
        self.cache_perfil.invalidar()

    def perfil_efectivo(self, modo):
        hit = self.cache_perfil.obtener(modo)
        if hit is not None:
            return hit
        perfiles, procedencia = self.perfiles.construir(modo)
        version = self.perfiles.version(perfiles)
        valor = (perfiles, procedencia, version)
        self.cache_perfil.guardar(modo, valor)
        return valor

    def info(self):
        perfiles, procedencia, version = self.perfil_efectivo("vivo")
        return {
            "redes": list(perfiles),
            "medicion": MEDICION_BASE,
            "version_perfil": version,
            "frescura": self.perfiles.frescura(procedencia),
            "metricas": {mid: {"bloque": m["bloque"], "direccion": m["dir"],
                               "objetivo": m["t"] if not isinstance(m["t"], tuple) else {"fraccion_ticket": m["t"][1]},
                               "inaceptable": m["w"] if not isinstance(m["w"], tuple) else {"fraccion_ticket": m["w"][1]}}
                         for mid, m in modelo.METRICAS.items()},
            "escenarios": {k: {"punto": list(v["a"]), "pesos": v["W"]} for k, v in modelo.REFERENCIAS.items()},
            "gamma": list(modelo.GAMMA),
        }

    def interpretar(self, e):
        perfiles, _, version = self.perfil_efectivo(e["modo"])
        lam, W, kappa, _, ticket_usd = _contexto(e)
        return {
            "redes": list(perfiles),
            "composicion": {modelo.ETIQUETA[k]: v for k, v in sorted(lam.items(), key=lambda x: -x[1])},
            "pesos": W, "certidumbre": kappa, "nivel_certidumbre": nivel_certidumbre(kappa),
            "ticket_usd": ticket_usd, "version_perfil": version,
        }

    def recomendar(self, e, replicas=None):
        return asyncio.run(self.recomendar_async(e, replicas))

    async def recomendar_async(self, e, replicas=None):
        replicas = replicas or self.settings.replicas_monte_carlo
        perfiles, procedencia, version = self.perfil_efectivo(e["modo"])
        clave = json.dumps([e, replicas, version], sort_keys=True)
        hit = self.cache.obtener(clave)
        if hit is not None:
            return hit
        if clave in self._en_vuelo:
            return await self._en_vuelo[clave]
        tarea = asyncio.ensure_future(self._resolver(e, replicas, perfiles, procedencia, version, clave))
        self._en_vuelo[clave] = tarea
        try:
            return await tarea
        finally:
            self._en_vuelo.pop(clave, None)

    async def _resolver(self, e, replicas, perfiles, procedencia, version, clave):
        entrada = {k: e[k] for k in ("monto_cop", "transfronterizo", "espera_s", "irrevocabilidad", "trm")}
        con_datos = redes_con_datos(perfiles)
        resultado_modelo = None
        if len(con_datos) >= MINIMO_REDES_CON_DATOS:
            solo = {r: perfiles[r] for r in con_datos}
            loop = asyncio.get_running_loop()
            resultado_modelo = await loop.run_in_executor(self._obtener_pool(), ejecutar_modelo, solo, entrada, replicas)
        respuesta = self._armar(entrada, e["modo"], perfiles, procedencia, version, con_datos, resultado_modelo)
        self.cache.guardar(clave, respuesta)
        if self.repo is not None and respuesta["estado"] == "ok":
            self.repo.registrar(e, e["modo"], version, {"bandas": respuesta["resultado"].get("bandas"),
                                                        "certidumbre": respuesta["resultado"].get("certidumbre")})
        return respuesta

    def _armar(self, entrada, modo, perfiles, procedencia, version, con_datos, r):
        t = ahora()
        base = {"modo": modo, "version_perfil": version, "decidido_en": iso(t), "decidido_ts": t,
                "frescura": self.perfiles.frescura(procedencia), "medicion": MEDICION_BASE, "trm": entrada["trm"]}
        if r is None:
            return {**base, "estado": "datos_insuficientes",
                    "motivo": f"solo {len(con_datos)} red(es) con datos; se requieren al menos {MINIMO_REDES_CON_DATOS}",
                    "resultado": None, "nivel_certidumbre": None, "detalle": {}, "procedencia": procedencia}
        solo = {x: perfiles[x] for x in con_datos}
        admisibles = [x for g in r.get("bandas", []) for x in g["redes"]]
        estado = "ok" if admisibles else "sin_redes_admisibles"
        return {**base, "estado": estado, "motivo": None if estado == "ok" else "ninguna red supera las compuertas",
                "resultado": r, "nivel_certidumbre": nivel_certidumbre(r["certidumbre"]),
                "detalle": detalle_redes(solo, entrada, procedencia), "procedencia": procedencia,
                "redes_sin_datos": [x for x in perfiles if x not in con_datos]}
