"""Evaluador del banco: llama a modelo.recomendar (sin modificar) en un pool de procesos propio, sin tocar la cache ni la auditoria del
Recomendador de la aplicacion, y reduce cada resultado a un registro con bandas, certidumbre y estado de ajuste en las dos lecturas de la espera."""

import asyncio
from concurrent.futures import ProcessPoolExecutor

from app.services.decision.recomendador import nivel_certidumbre, redes_con_datos
from app.services.decision.trabajador import ejecutar_modelo, calentar

from .ajuste import LECTURAS, estado_ajuste

CLAVES_ENTRADA = ("monto_cop", "transfronterizo", "espera_s", "irrevocabilidad", "trm")
MINIMO_REDES = 2


def filtrar(perfiles, excluir=(), solo=None):
    con_datos = [r for r in redes_con_datos(perfiles) if r not in excluir and (solo is None or r in solo)]
    return {r: perfiles[r] for r in con_datos}


def resumir(usuario, perfiles, resultado):
    registro = {"perfil": usuario["perfil"], "indice": usuario["indice"], "monto_cop": usuario["monto_cop"],
                "espera_s": usuario["espera_s"], "irrevocabilidad": usuario["irrevocabilidad"],
                "transfronterizo": usuario["transfronterizo"]}
    if resultado is None:
        registro.update({"bandas": [], "medianas": {}, "certidumbre": None, "nivel": None, "determinante": None,
                         "inadmisibles": [], "advertencias": 0, "datos_insuficientes": True})
    else:
        bandas = resultado.get("bandas") or []
        registro.update({
            "bandas": [b["redes"] for b in bandas],
            "medianas": {r: p["mediana"] for b in bandas for r, p in b["puntajes"].items()},
            "certidumbre": resultado["certidumbre"], "nivel": nivel_certidumbre(resultado["certidumbre"]),
            "determinante": (resultado.get("determinante") or {}).get("metrica"),
            "inadmisibles": sorted(resultado.get("inadmisibles", {})),
            "advertencias": len(resultado.get("advertencias", [])), "datos_insuficientes": False,
        })
    for lectura in LECTURAS:
        estado, fallos = estado_ajuste(perfiles, usuario, resultado, lectura)
        registro[f"ajuste_{lectura}"] = estado
        registro[f"fallos_{lectura}"] = fallos
    return registro


def banda1(registro):
    return tuple(sorted(registro["bandas"][0])) if registro["bandas"] else ()


class Evaluador:
    def __init__(self, procesos):
        self.procesos = max(1, procesos)
        self._pool = None

    def _obtener_pool(self):
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=self.procesos)
            self._pool.submit(calentar)
        return self._pool

    def cerrar(self):
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None

    async def evaluar(self, perfiles, usuario, replicas):
        if len(perfiles) < MINIMO_REDES:
            return resumir(usuario, perfiles, None)
        entrada = {k: usuario[k] for k in CLAVES_ENTRADA}
        loop = asyncio.get_running_loop()
        resultado = await loop.run_in_executor(self._obtener_pool(), ejecutar_modelo, perfiles, entrada, replicas)
        return resumir(usuario, perfiles, resultado)

    async def evaluar_varios(self, perfiles, usuarios, replicas, al_terminar=None):
        async def uno(u):
            r = await self.evaluar(perfiles, u, replicas)
            if al_terminar:
                al_terminar()
            return r
        return await asyncio.gather(*(uno(u) for u in usuarios))
