#!/usr/bin/env python3
"""
Modelo de recomendacion de red para pagos en Colombia.

Recibe la descripcion de un caso y devuelve que red conviene, con que
confianza y por que. No mueve dinero ni consulta ninguna red: es una
funcion de decision sobre perfiles ya medidos.

Implementa la especificacion del documento del modelo:

  * Cuatro atributos describen el caso.
  * Los tres escenarios del benchmark son puntos de referencia en el
    espacio de atributos; los pesos del caso se interpolan entre ellos.
    Asi la ponderacion responde al caso real y sigue siendo trazable.
  * La certidumbre combina proximidad al escenario mas cercano y
    concentracion de la composicion.
  * Las compuertas se aplican antes de puntuar.
  * El puntaje se propaga por Monte Carlo y se reporta por bandas, no
    por puestos.

Uso:
    python modelo.py                      # ejemplos
    python modelo.py --monto 1200000 --espera 60
    python modelo.py --monto 300 --moneda usd --transfronterizo --espera 3600
"""

import argparse
import json
import math
import random
from pathlib import Path

random.seed(42)

# ==========================================================================
# ESCENARIOS DE REFERENCIA  (§4.2 del documento del modelo)
# ==========================================================================

# Posicion de cada escenario en el espacio de atributos, tomada de la tabla
# de escenarios del documento (seccion 5.3.1):
#   E1 remesas    USD 300 (centro de USD 200 a 500), transfronterizo,
#                 espera de horas (3.600 s), irrevocabilidad baja
#   E2 comercio   COP 48.906 (centro geometrico de 15.000 a 159.456),
#                 espera de 20 s (techo de Bre-B), irrevocabilidad media
#   E3 alto valor COP 100 millones, espera de minutos (600 s),
#                 irrevocabilidad alta
# Coordenadas = vector_caso() de esos valores, redondeadas a dos decimales.
REFERENCIAS = {
    "remesas":   {"a": (0.42, 1.0, 0.72, 0.0),
                  "W": {"A": 0.45, "B": 0.15, "C": 0.15, "D": 0.25}},
    "comercio":  {"a": (0.14, 0.0, 0.26, 0.5),
                  "W": {"A": 0.35, "B": 0.35, "C": 0.15, "D": 0.15}},
    "altovalor": {"a": (0.80, 0.0, 0.56, 1.0),
                  "W": {"A": 0.10, "B": 0.30, "C": 0.40, "D": 0.20}},
}
ETIQUETA = {"remesas": "remesas", "comercio": "comercio doméstico",
            "altovalor": "alto valor"}

GAMMA = (1.0, 1.5, 1.0, 1.2)   # peso por atributo en la distancia
P_INV = 2                       # exponente de la proximidad
EPS_D = 0.05
D0 = 0.6                        # escala de distancia para la certidumbre

M_MIN, M_MAX = 1e4, 1e9         # pesos colombianos
L_MIN, L_MAX = 1.0, 86400.0     # segundos

# ==========================================================================
# METRICAS  (§8 del documento del benchmark)
# ==========================================================================
# t = valor objetivo (puntaje 1); w = umbral inaceptable (puntaje 0)
# "ticket" en t/w significa fraccion del ticket del caso.

METRICAS = {
    "A1": dict(bloque="A", dir="menor", t=("ticket", 0.001), w=("ticket", 0.01)),
    "A2": dict(bloque="A", dir="menor", t=1.5,     w=10),
    "A3": dict(bloque="A", dir="menor", t=0.2,     w=2.0),
    "A4": dict(bloque="A", dir="menor", t=0.001,   w=0.10),
    "B1": dict(bloque="B", dir="menor", t=3,       w=20),
    # B2 y B2b: CPMI-IOSCO (2012), Principio 8, consideracion 8.2: firmeza
    # "como minimo al final del dia valor", preferiblemente "intradia o en
    # tiempo real". w = un dia; t = tiempo real, el estandar de Bre-B (20 s).
    "B2": dict(bloque="B", dir="menor", t=20,      w=86400),
    "B2b": dict(bloque="B", dir="menor", t=20,     w=86400),
    "B3": dict(bloque="B", dir="mayor", t=5,       w=1),
    # C1: t = HHI de 1.000, umbral de mercado no concentrado de las guias de
    # fusiones de EE. UU. (DOJ y FTC, 2023, nota 15); w = productor unico.
    "C1": dict(bloque="C", dir="menor", t=0.10,    w=1.00),
    "C2": dict(bloque="C", dir="mayor", t=15,      w=1),
    "C3": dict(bloque="C", dir="nueves", t=99.999, w=99.9),
    "C4": dict(bloque="C", dir="menor", t=0.001,   w=0.05),
    "C5": dict(bloque="C", dir="menor", t=0.5,     w=5),
    "D1": dict(bloque="D", dir="mayor", t=0.50,    w=0.01),
    "D2": dict(bloque="D", dir="mayor", t=0.20,    w=0.001),
    "D3": dict(bloque="D", dir="mayor", t=0.10,    w=0.001),
}
BLOQUES = ["A", "B", "C", "D"]
EPS_S = 0.05      # piso de la media geometrica

# ==========================================================================
# ENTRADA
# ==========================================================================

def normalizar_log(v, lo, hi):
    if v <= 0:
        return 0.0
    return max(0.0, min(1.0, (math.log(v) - math.log(lo)) /
                        (math.log(hi) - math.log(lo))))


def vector_caso(monto_cop, transfronterizo, espera_s, irrevocabilidad):
    """Convierte la descripcion del caso en su posicion en el espacio."""
    return (normalizar_log(monto_cop, M_MIN, M_MAX),
            1.0 if transfronterizo else 0.0,
            normalizar_log(espera_s, L_MIN, L_MAX),
            {"baja": 0.0, "media": 0.5, "alta": 1.0}[irrevocabilidad])


def interpolar(a):
    """Devuelve composicion, pesos de bloque y certidumbre."""
    d = {e: math.sqrt(sum(g * (a[k] - r["a"][k]) ** 2
                          for k, g in enumerate(GAMMA)))
         for e, r in REFERENCIAS.items()}
    inv = {e: (v + EPS_D) ** -P_INV for e, v in d.items()}
    tot = sum(inv.values())
    lam = {e: v / tot for e, v in inv.items()}

    W = {b: sum(lam[e] * REFERENCIAS[e]["W"][b] for e in REFERENCIAS)
         for b in BLOQUES}

    H = -sum(v * math.log(v) for v in lam.values() if v > 0)
    proximidad = math.exp(-min(d.values()) / D0)
    concentracion = math.sqrt(max(0.0, 1 - H / math.log(len(REFERENCIAS))))
    return lam, W, proximidad * concentracion, min(d.values())


# ==========================================================================
# PUNTUACION
# ==========================================================================

def umbral(valor, ticket_usd):
    return valor[1] * ticket_usd if isinstance(valor, tuple) else valor


def normalizar(mid, x, ticket_usd):
    """Lleva una medicion a [0,1] segun los umbrales de la metrica."""
    m = METRICAS[mid]
    t, w = umbral(m["t"], ticket_usd), umbral(m["w"], ticket_usd)
    if x is None:
        return None
    if m["dir"] == "nueves":
        nu = lambda A: -math.log10(max(1 - A / 100, 1e-12))
        z = (nu(x) - nu(w)) / (nu(t) - nu(w))
    elif m["dir"] == "menor":
        x = max(x, 1e-12)
        z = (math.log(w) - math.log(x)) / (math.log(w) - math.log(t))
    else:
        x = max(x, 1e-12)
        z = (math.log(x) - math.log(w)) / (math.log(t) - math.log(w))
    return max(0.0, min(1.0, z))


def puntuar(perfil, W, ticket_usd, rng):
    """Un puntaje sobre una realizacion del perfil."""
    por_bloque = {}
    for b in BLOQUES:
        vals = []
        for mid, m in METRICAS.items():
            if m["bloque"] != b or mid not in perfil:
                continue
            d = perfil[mid]
            if d.get("valor") is None:
                continue                       # no concluyente: se excluye
            x = rng.gauss(d["valor"], d.get("sigma", 0) or 0)
            s = normalizar(mid, x, ticket_usd)
            if s is not None:
                vals.append(s)
        por_bloque[b] = sum(vals) / len(vals) if vals else None

    # Bloques sin ninguna metrica: su peso se redistribuye
    validos = {b: v for b, v in por_bloque.items() if v is not None}
    if not validos:
        return 0.0, por_bloque
    peso_total = sum(W[b] for b in validos)
    s = 1.0
    for b, v in validos.items():
        s *= max(v, EPS_S) ** (W[b] / peso_total)
    return s, por_bloque


def compuertas(red, perfil, escenario_dominante, ticket_usd):
    """Devuelve la lista de compuertas falladas, con su motivo."""
    fallas = []
    b1 = perfil.get("B1", {}).get("valor")
    if escenario_dominante == "comercio" and b1 is not None and b1 > 20:
        fallas.append(("G1", f"latencia de inclusión {b1:.1f} s, "
                             f"por encima del techo de 20 s"))
    if perfil.get("B2", {}).get("valor") is None:
        fallas.append(("G2", "sin anclaje verificable en Ethereum"))
    d2 = perfil.get("D2", {}).get("valor")
    if d2 is not None and d2 <= 0:
        fallas.append(("G3", "sin referencia de conciliación en uso"))
    # G4 solo descarta cuando B3 es una medida de capacidad, no una cota
    # inferior. Un caudal observado bajo refleja demanda, no incapacidad:
    # descartar una red por estar poco usada seria un error de lectura.
    b3d = perfil.get("B3", {})
    b3 = b3d.get("valor")
    if (escenario_dominante != "remesas" and b3 is not None and b3 < 1
            and not b3d.get("cota_inferior")):
        fallas.append(("G4", f"margen de capacidad {b3:.2f}, insuficiente"))
    return fallas


# ==========================================================================
# BANDAS
# ==========================================================================

def bandas(muestras, umbral_sep=0.85):
    """Agrupa redes cuyo desempeno no se distingue."""
    redes = sorted(muestras, key=lambda r: -mediana(muestras[r]))
    n = len(next(iter(muestras.values())))

    def separadas(x, y):
        gana = sum(1 for i in range(n) if muestras[x][i] > muestras[y][i]) / n
        return gana >= umbral_sep, gana

    grupos, actual = [], [redes[0]]
    for r in redes[1:]:
        if all(separadas(m, r)[0] for m in actual):
            grupos.append(actual)
            actual = [r]
        else:
            actual.append(r)
    grupos.append(actual)
    return grupos, separadas


def mediana(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def percentil(v, p):
    s = sorted(v)
    k = (len(s) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


# ==========================================================================
# MODELO
# ==========================================================================

def recomendar(perfiles, monto_cop, transfronterizo=False, espera_s=60,
               irrevocabilidad="media", trm=4000.0, replicas=10000):
    a = vector_caso(monto_cop, transfronterizo, espera_s, irrevocabilidad)
    lam, W, kappa, d_min = interpolar(a)
    dominante = max(lam, key=lam.get)
    ticket_usd = monto_cop / trm

    admisibles, inadmisibles = {}, {}
    for red, perfil in perfiles.items():
        f = compuertas(red, perfil, dominante, ticket_usd)
        (inadmisibles if f else admisibles)[red] = f or perfil

    resultado = {
        "caso": {"monto_cop": monto_cop, "ticket_usd": round(ticket_usd, 2),
                 "transfronterizo": transfronterizo, "espera_s": espera_s,
                 "irrevocabilidad": irrevocabilidad},
        "composicion": {ETIQUETA[e]: round(v, 3) for e, v in
                        sorted(lam.items(), key=lambda x: -x[1])},
        "pesos": {b: round(w, 3) for b, w in W.items()},
        "certidumbre": round(kappa, 3),
        "inadmisibles": {r: f for r, f in inadmisibles.items()},
        "advertencias": [],
    }
    if kappa < 0.45:
        resultado["advertencias"].append(
            f"certidumbre de interpretación baja ({kappa:.2f}): el caso no está "
            f"bien cubierto por los escenarios evaluados")
    elif kappa < 0.75:
        resultado["advertencias"].append(
            f"certidumbre media ({kappa:.2f}): el caso queda entre escenarios")

    if not admisibles:
        resultado["bandas"] = []
        resultado["advertencias"].append(
            "ninguna red admisible para este caso bajo los umbrales declarados")
        return resultado

    rng = random.Random(42)
    muestras = {r: [] for r in admisibles}
    for _ in range(replicas):
        Wp = perturbar(W, rng)
        for r, perfil in admisibles.items():
            s, _ = puntuar(perfil, Wp, ticket_usd, rng)
            muestras[r].append(s)

    grupos, sep = bandas(muestras)
    resultado["bandas"] = [
        {"banda": i + 1, "redes": g,
         "puntajes": {r: {"mediana": round(mediana(muestras[r]), 3),
                          "p05": round(percentil(muestras[r], 5), 3),
                          "p95": round(percentil(muestras[r], 95), 3)}
                      for r in g}}
        for i, g in enumerate(grupos)]

    for i in range(len(grupos) - 1):
        _, p = sep(grupos[i][0], grupos[i + 1][0])
        resultado["bandas"][i]["separacion_con_siguiente"] = round(p, 3)
    if len(grupos[0]) > 1:
        _, p = sep(grupos[0][0], grupos[0][1])
        resultado["bandas"][0]["no_distinguibles"] = (
            f"P({grupos[0][0]} > {grupos[0][1]}) = {p:.2f}")

    resultado["determinante"] = determinante(admisibles, grupos, W, ticket_usd)
    faltantes = sorted({m for p in admisibles.values() for m in METRICAS
                        if p.get(m, {}).get("valor") is None})
    if faltantes:
        resultado["advertencias"].append(
            f"métricas no concluyentes, excluidas del cálculo: {', '.join(faltantes)}")
    return resultado


def perturbar(W, rng, kappa_w=50):
    """Dirichlet sobre los pesos: la ponderacion es un juicio, no una constante."""
    g = {b: rng.gammavariate(max(kappa_w * W[b], 1e-3), 1.0) for b in W}
    t = sum(g.values())
    return {b: v / t for b, v in g.items()}


def determinante(admisibles, grupos, W, ticket_usd):
    """Metrica que mas contribuye a separar la banda 1 de la 2."""
    if len(grupos) < 2:
        return None
    def medio(redes, mid):
        vals = []
        for r in redes:
            d = admisibles[r].get(mid, {})
            if d.get("valor") is not None:
                s = normalizar(mid, d["valor"], ticket_usd)
                if s is not None:
                    vals.append(s)
        return sum(vals) / len(vals) if vals else None

    # Solo se consideran metricas disponibles en TODAS las redes comparadas.
    # Si una red carece de la metrica, el promedio de su banda se calcula sobre
    # las demas y la comparacion mezcla conjuntos distintos, lo que puede
    # senalar como determinante algo que el modelo excluyo por no concluyente.
    todas = list(grupos[0]) + list(grupos[1])
    completas = {mid for mid in METRICAS
                 if all(admisibles[r].get(mid, {}).get("valor") is not None
                        for r in todas)}
    mejor, delta = None, 0
    for mid, m in METRICAS.items():
        if mid not in completas:
            continue
        s1, s2 = medio(grupos[0], mid), medio(grupos[1], mid)
        if s1 is None or s2 is None:
            continue
        n = sum(1 for k, v in METRICAS.items() if v["bloque"] == m["bloque"])
        d = (W[m["bloque"]] / n) * (s1 - s2)
        if d > delta:
            mejor, delta = mid, d
    return {"metrica": mejor, "contribucion": round(delta, 4)} if mejor else None


# ==========================================================================
# PERFILES
# ==========================================================================

def cargar_perfiles(ruta="perfiles.json"):
    p = Path(ruta)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    print(f"  [aviso] {ruta} no existe: se usan perfiles PROVISIONALES.\n"
          f"          Las recomendaciones no tienen validez empirica hasta\n"
          f"          sustituirlos por los que produzca el motor de calculo.\n")
    return PERFILES_PROVISIONALES


def v(x, s=0.0):
    return {"valor": x, "sigma": s}


# Provisionales, coherentes en orden de magnitud con lo observado en las
# pruebas. NO son resultados: sirven para ejercitar la logica.
PERFILES_PROVISIONALES = {
    "polygon":  {"A1": v(0.0073, 0.0020), "A2": v(8.3, 1.2), "A3": v(0.45, 0.20),
                 "A4": v(0.004, 0.001),  "B1": v(2.0, 0.3), "B2": v(1056, 200),
                 "B2b": v(1056, 200),    "B3": v(8.0, 1.0), "C1": v(0.2512, 0.02),
                 "C2": v(2, 0),          "C3": v(None),     "C4": v(0.002, 0.001),
                 "C5": v(0, 0),          "D1": v(0.001, 0.001), "D2": v(0.80, 0.05),
                 "D3": v(0.33, 0.04)},
    "celo":     {"A1": v(0.0042, 0.0025), "A2": v(6.8, 2.0), "A3": v(0.30, 0.25),
                 "A4": v(0.002, 0.001),  "B1": v(1.0, 0.1), "B2": v(1872, 300),
                 "B2b": v(1872, 300),    "B3": v(12.0, 1.5), "C1": v(1.0, 0.0),
                 "C2": v(1, 0),          "C3": v(None),     "C4": v(0.001, 0.001),
                 "C5": v(0, 0),          "D1": v(0.001, 0.001), "D2": v(1.00, 0.02),
                 "D3": v(0.00, 0.01)},
    "arbitrum": {"A1": v(0.0085, 0.0015), "A2": v(11.5, 1.5), "A3": v(None),
                 "A4": v(0.006, 0.001),  "B1": v(0.25, 0.05), "B2": v(156, 40),
                 "B2b": v(604800, 0),    "B3": v(20.0, 2.0), "C1": v(1.0, 0.0),
                 "C2": v(1, 0),          "C3": v(None),     "C4": v(0.001, 0.001),
                 "C5": v(0, 0),          "D1": v(0.001, 0.001), "D2": v(0.33, 0.06),
                 "D3": v(0.29, 0.05)},
}


# ==========================================================================
# PRESENTACION
# ==========================================================================

def imprimir(r):
    c = r["caso"]
    print(f"\n{'=' * 72}")
    print(f"  CASO  COP {c['monto_cop']:,}  (~USD {c['ticket_usd']:,.2f})  |  "
          f"{'transfronterizo' if c['transfronterizo'] else 'doméstico'}  |  "
          f"espera {c['espera_s']} s  |  irrevocabilidad {c['irrevocabilidad']}")
    print(f"{'=' * 72}")
    comp = "  ".join(f"{k} {v:.2f}" for k, v in r["composicion"].items())
    print(f"  composición   {comp}")
    print(f"  pesos         " + "  ".join(f"{b} {w:.2f}" for b, w in r["pesos"].items()))
    k = r["certidumbre"]
    nivel = "ALTA" if k >= 0.75 else ("MEDIA" if k >= 0.45 else "BAJA")
    print(f"  certidumbre   {k:.2f}  {nivel}")

    if r["inadmisibles"]:
        print(f"\n  inadmisibles:")
        for red, fallas in r["inadmisibles"].items():
            for cid, motivo in fallas:
                print(f"    {red:<10} {cid}  {motivo}")

    for b in r["bandas"]:
        redes = ", ".join(b["redes"])
        print(f"\n  banda {b['banda']}:  {redes}")
        for red, p in b["puntajes"].items():
            print(f"    {red:<10} {p['mediana']:.3f}   "
                  f"[{p['p05']:.3f} – {p['p95']:.3f}]")
        if "no_distinguibles" in b:
            print(f"    no distinguibles entre sí: {b['no_distinguibles']}")
        if "separacion_con_siguiente" in b:
            print(f"    separada de la siguiente con P = "
                  f"{b['separacion_con_siguiente']:.2f}")

    if r.get("determinante"):
        d = r["determinante"]
        print(f"\n  determinante: {d['metrica']}  "
              f"(contribución {d['contribucion']:.4f})")
    for adv in r["advertencias"]:
        print(f"  aviso: {adv}")


def main():
    ap = argparse.ArgumentParser(description="Modelo de recomendación de red")
    ap.add_argument("--monto", type=float, help="monto de la operación")
    ap.add_argument("--moneda", choices=["cop", "usd"], default="cop")
    ap.add_argument("--transfronterizo", action="store_true")
    ap.add_argument("--espera", type=float, default=60,
                    help="espera tolerable en segundos")
    ap.add_argument("--irrevocabilidad", choices=["baja", "media", "alta"],
                    default="media")
    ap.add_argument("--trm", type=float, default=4000.0)
    ap.add_argument("--perfiles", default="perfiles.json")
    a = ap.parse_args()

    perfiles = cargar_perfiles(a.perfiles)

    if a.monto:
        monto = a.monto * a.trm if a.moneda == "usd" else a.monto
        imprimir(recomendar(perfiles, monto, a.transfronterizo, a.espera,
                            a.irrevocabilidad, a.trm))
        return

    print("Modelo de recomendación — casos de ejemplo")
    ejemplos = [
        ("Remesa de USD 300", 300 * 4000, True, 3600, "baja"),
        ("Pago en tienda, COP 15.000", 15000, False, 3, "media"),
        ("Pago doméstico de COP 1,2 M", 1_200_000, False, 60, "media"),
        ("Liquidación de COP 80 M", 80_000_000, False, 600, "alta"),
    ]
    for nombre, monto, tf, esp, irr in ejemplos:
        print(f"\n\n### {nombre}")
        imprimir(recomendar(perfiles, monto, tf, esp, irr, a.trm))


if __name__ == "__main__":
    main()
