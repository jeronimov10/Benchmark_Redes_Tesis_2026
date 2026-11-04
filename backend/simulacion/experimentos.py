"""Pruebas P1 a P6 del banco: muestreo adaptativo con intervalo de Wilson (P1, P2), referencia y contrafactuales de medicion y de caida de red
(P3, P4), sensibilidad por atributo (P5) y convergencia de replicas (P6). Los contrafactuales solo quitan redes, metricas o sigma: nunca agregan
un valor que el perfil original no tuviera."""

import copy
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from app.services.decision.recomendador import modelo

from .evaluador import banda1, filtrar
from .personas import PERSONAS, usuarios

TANDA = 50
SEMIANCHO_OBJETIVO = 0.05
REDES_PCA = ("polygon", "celo", "arbitrum")
REDES_TAC = ("tempo", "aptos", "canton")
NIVELES_IRREV = ["baja", "media", "alta"]
VARIANTES_P5 = ("monto_x2", "monto_div2", "espera_x4", "espera_div4", "irrev_arriba", "irrev_abajo", "transfronterizo_inverso")


class Cancelado(Exception):
    pass


class _Central:
    def gauss(self, mu, sigma):
        return mu


@dataclass
class Contexto:
    evaluador: object
    replicas: int
    tope: int
    panel_por_perfil: int
    semilla: int
    niveles_replicas: tuple
    guardar: Callable
    cancelado: Callable = lambda: False
    al_evaluar: Callable = lambda: None
    al_etapa: Callable = lambda texto: None
    notas: list = field(default_factory=list)

    def revisar(self):
        if self.cancelado():
            raise Cancelado()


def wilson_semiancho(k, n, z=1.96):
    if n == 0:
        return 1.0
    p = k / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)


def cuota_modal(registros):
    cuenta = Counter(banda1(r) for r in registros)
    modal, k = cuenta.most_common(1)[0]
    return modal, k


def panel(ctx):
    return [u for p in PERSONAS for u in usuarios(p, 0, ctx.panel_por_perfil, ctx.semilla)]


async def muestreo(ctx, fuente, perfiles):
    ctx.al_etapa(f"P1/P2 muestreo adaptativo ({fuente})")
    elegibles = filtrar(perfiles)
    for persona in PERSONAS:
        registros = []
        while True:
            ctx.revisar()
            desde = len(registros)
            lote = usuarios(persona, desde, desde + TANDA, ctx.semilla)
            registros += await ctx.evaluador.evaluar_varios(elegibles, lote, ctx.replicas, ctx.al_evaluar)
            _, k = cuota_modal(registros)
            if wilson_semiancho(k, len(registros)) <= SEMIANCHO_OBJETIVO or len(registros) >= ctx.tope:
                break
        ctx.guardar("P1P2", fuente, "muestreo", registros)


async def referencia(ctx, fuente, perfiles):
    ctx.al_etapa(f"referencia del panel ({fuente})")
    ctx.revisar()
    registros = await ctx.evaluador.evaluar_varios(filtrar(perfiles), panel(ctx), ctx.replicas, ctx.al_evaluar)
    ctx.guardar("REF", fuente, "referencia", registros)
    return registros


def _comunes(perfiles):
    con_b2 = [r for r, p in perfiles.items() if p.get("B2", {}).get("valor") is not None]
    base = con_b2 or list(perfiles)
    ids = set.intersection(*[{m for m, d in perfiles[r].items() if d.get("valor") is not None} for r in base])
    return {r: {m: d for m, d in p.items() if m in ids} for r, p in perfiles.items()}, sorted(ids)


def _sin_sigma(perfiles):
    out = copy.deepcopy(perfiles)
    for p in out.values():
        for d in p.values():
            if "sigma" in d:
                d["sigma"] = 0
    return out


def sombra_aptos(ctx, fuente, perfiles, usuarios_panel):
    if "aptos" not in perfiles:
        return []
    elegibles = filtrar(perfiles)
    registros = []
    for u in usuarios_panel:
        a = modelo.vector_caso(u["monto_cop"], u["transfronterizo"], u["espera_s"], u["irrevocabilidad"])
        _, W, _, _ = modelo.interpolar(a)
        ticket = u["monto_cop"] / u["trm"]
        centrales = {r: modelo.puntuar(p, W, ticket, _Central())[0] for r, p in elegibles.items()}
        if "aptos" not in centrales or len(centrales) < 2:
            continue
        otras = {r: v for r, v in centrales.items() if r != "aptos"}
        mejor = max(otras, key=otras.get)
        registros.append({"perfil": u["perfil"], "indice": u["indice"], "aptos_central": centrales["aptos"],
                          "mejor_otra": mejor, "mejor_otra_central": otras[mejor],
                          "aptos_supera": centrales["aptos"] > otras[mejor], "bandas": []})
    return registros


async def contrafactuales(ctx, fuente, perfiles):
    usuarios_panel = panel(ctx)
    ctx.al_etapa(f"P3 contrafactuales de medicion ({fuente})")
    comunes, ids = _comunes(filtrar(perfiles))
    ctx.notas.append(f"{fuente}: metricas comunes = {len(ids)} ({', '.join(ids)})")
    escenarios = {
        "metricas_comunes": comunes,
        "sin_sigma": _sin_sigma(filtrar(perfiles)),
        "solo_pca": filtrar(perfiles, solo=REDES_PCA),
        "solo_tac": filtrar(perfiles, solo=REDES_TAC),
    }
    for nombre, p in escenarios.items():
        ctx.revisar()
        registros = await ctx.evaluador.evaluar_varios(p, usuarios_panel, ctx.replicas, ctx.al_evaluar)
        ctx.guardar("P3", fuente, nombre, registros)
    ctx.guardar("P3", fuente, "aptos_sombra", sombra_aptos(ctx, fuente, perfiles, usuarios_panel))

    ctx.al_etapa(f"P4 caida de una red ({fuente})")
    for red in perfiles:
        ctx.revisar()
        registros = await ctx.evaluador.evaluar_varios(filtrar(perfiles, excluir=(red,)), usuarios_panel, ctx.replicas, ctx.al_evaluar)
        ctx.guardar("P4", fuente, f"sin_{red}", registros)


def variante(usuario, nombre):
    u = dict(usuario)
    if nombre == "monto_x2":
        u["monto_cop"] = usuario["monto_cop"] * 2
    elif nombre == "monto_div2":
        u["monto_cop"] = usuario["monto_cop"] / 2
    elif nombre == "espera_x4":
        u["espera_s"] = usuario["espera_s"] * 4
    elif nombre == "espera_div4":
        u["espera_s"] = usuario["espera_s"] / 4
    elif nombre in ("irrev_arriba", "irrev_abajo"):
        i = NIVELES_IRREV.index(usuario["irrevocabilidad"]) + (1 if nombre == "irrev_arriba" else -1)
        if not 0 <= i < len(NIVELES_IRREV):
            return None
        u["irrevocabilidad"] = NIVELES_IRREV[i]
    elif nombre == "transfronterizo_inverso":
        u["transfronterizo"] = not usuario["transfronterizo"]
    return u


async def sensibilidad(ctx, fuente, perfiles):
    ctx.al_etapa(f"P5 sensibilidad del usuario ({fuente})")
    elegibles = filtrar(perfiles)
    base = panel(ctx)
    for nombre in VARIANTES_P5:
        ctx.revisar()
        cambiados = [v for v in (variante(u, nombre) for u in base) if v is not None]
        registros = await ctx.evaluador.evaluar_varios(elegibles, cambiados, ctx.replicas, ctx.al_evaluar)
        ctx.guardar("P5", fuente, nombre, registros)


async def convergencia(ctx, fuente, perfiles):
    ctx.al_etapa(f"P6 convergencia de replicas ({fuente})")
    elegibles = filtrar(perfiles)
    usuarios_panel = panel(ctx)
    for nivel in sorted(ctx.niveles_replicas):
        ctx.revisar()
        registros = await ctx.evaluador.evaluar_varios(elegibles, usuarios_panel, nivel, ctx.al_evaluar)
        ctx.guardar("P6", fuente, f"replicas_{nivel}", registros)
