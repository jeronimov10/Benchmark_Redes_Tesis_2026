#!/usr/bin/env python3
"""
Pruebas del modelo sobre los perfiles medidos (perfiles.json).
No consulta ninguna red.

  1. Benchmark: puntaje de cada red en los tres escenarios, con los pesos
     exactos de cada escenario (sin interpolar).
  2. Barrido de pagos: el modelo sobre una malla de pagos que cubre los
     cuatro atributos. Cuenta que red queda en la banda 1 y con que
     certidumbre.
  3. Punto de quiebre: cuanto tendria que empeorar Polygon en una metrica
     (todo lo demas igual) para perder el primer lugar en cada escenario, y
     que red lo toma.

Uso:
    python pruebas_modelo.py
"""

import copy
import json
import random

import modelo

REPLICAS = 2000
TRM = 4000.0
ESCENARIOS = {
    "remesas":   ("Remesa USD 300", 300 * TRM),
    "comercio":  ("Tienda COP 15.000", 15_000),
    "altovalor": ("Alto valor COP 80 M", 80_000_000),
}


def correr(perfiles, W, ticket_usd, replicas=REPLICAS, semilla=42):
    rng = random.Random(semilla)
    muestras = {r: [] for r in perfiles}
    for _ in range(replicas):
        Wp = modelo.perturbar(W, rng)
        for r, p in perfiles.items():
            muestras[r].append(modelo.puntuar(p, Wp, ticket_usd, rng)[0])
    grupos, sep = modelo.bandas(muestras)
    med = {r: modelo.mediana(v) for r, v in muestras.items()}
    return grupos, med, sep


def benchmark(perfiles):
    print("\n1. BENCHMARK POR ESCENARIO (pesos exactos del escenario)")
    filas = {}
    for e, (nombre, monto) in ESCENARIOS.items():
        W = modelo.REFERENCIAS[e]["W"]
        grupos, med, sep = correr(perfiles, W, monto / TRM)
        txt = "  |  ".join("banda %d: %s" % (i + 1, ", ".join(
            "%s %.3f" % (r, med[r]) for r in g)) for i, g in enumerate(grupos))
        p12 = sep(grupos[0][0], grupos[1][0])[1] if len(grupos) > 1 else None
        print(f"  {nombre:<22} {txt}" + (f"   P(1>2) {p12:.2f}" if p12 else ""))
        filas[e] = {"bandas": grupos, "medianas": med}
    return filas


def barrido(perfiles):
    print("\n2. BARRIDO DE PAGOS")
    montos = [10 ** (4 + k / 2) for k in range(11)]          # 10 mil a 1.000 M
    esperas = [3, 60, 3600, 86400]
    irrev = ["baja", "media", "alta"]
    total = 0
    primero = {}
    empates = 0
    por_cert = {"alta": [0, 0], "media": [0, 0], "baja": [0, 0]}
    segundo = {}
    casos = []
    for m in montos:
        for x in (False, True):
            for l in esperas:
                for i in irrev:
                    a = modelo.vector_caso(m, x, l, i)
                    lam, W, kappa, _ = modelo.interpolar(a)
                    grupos, med, _ = correr(perfiles, W, m / TRM, replicas=500)
                    total += 1
                    b1 = tuple(sorted(grupos[0]))
                    primero[b1] = primero.get(b1, 0) + 1
                    if len(grupos[0]) > 1:
                        empates += 1
                    if len(grupos) > 1:
                        s = tuple(sorted(grupos[1]))
                        segundo[s] = segundo.get(s, 0) + 1
                    nivel = "alta" if kappa >= .75 else ("media" if kappa >= .45 else "baja")
                    por_cert[nivel][0] += 1
                    por_cert[nivel][1] += "polygon" in grupos[0] and len(grupos[0]) == 1
                    casos.append((m, x, l, i, round(kappa, 2), grupos))
    print(f"  {total} pagos evaluados")
    for k, n in sorted(primero.items(), key=lambda t: -t[1]):
        print(f"    banda 1 = {', '.join(k):<25} {n:4d}  ({100*n/total:.1f} %)")
    print(f"    con empate en la banda 1: {empates}")
    for k, n in sorted(segundo.items(), key=lambda t: -t[1]):
        print(f"    banda 2 = {', '.join(k):<25} {n:4d}  ({100*n/total:.1f} %)")
    for nivel, (n, p) in por_cert.items():
        if n:
            print(f"    certidumbre {nivel:<6} {n:4d} pagos, Polygon sola en banda 1 en {p}")
    return casos


def quiebre(perfiles):
    print("\n3. PUNTO DE QUIEBRE DE POLYGON (cuanto tendria que empeorar)")
    pruebas = {
        "A1 costo (x veces)":              ("A1", "mult"),
        "A2 dispersion (x veces)":         ("A2", "mult"),
        "B2b irrevocabilidad (x veces)":   ("B2b", "mult"),
        "C1 concentracion (HHI)":          ("C1", "valor"),
    }
    for nombre_e, (etq, monto) in ESCENARIOS.items():
        W = modelo.REFERENCIAS[nombre_e]["W"]
        print(f"  {etq}")
        for nombre, (mid, modo) in pruebas.items():
            base = perfiles["polygon"][mid]["valor"]
            if modo == "mult":
                pasos = [1.5, 2, 3, 5, 10, 20, 50, 100, 300, 1000]
            else:
                pasos = [0.25, 0.33, 0.5, 0.75, 1.0]
            hallado = None
            for f in pasos:
                p = copy.deepcopy(perfiles)
                p["polygon"][mid]["valor"] = base * f if modo == "mult" else f
                if modo == "mult":
                    p["polygon"][mid]["sigma"] = (p["polygon"][mid].get("sigma") or 0) * f
                grupos, med, _ = correr(p, W, monto / TRM, replicas=500)
                if not (grupos[0] == ["polygon"]):
                    hallado = (f, grupos[0], med)
                    break
            if hallado:
                f, g, med = hallado
                lado = f"x{f:g}" if modo == "mult" else f"HHI {f:g}"
                print(f"    {nombre:<32} pierde la banda 1 en {lado:<10} "
                      f"-> banda 1: {', '.join(g)}")
            else:
                tope = f"x{pasos[-1]:g}" if modo == "mult" else "HHI 1"
                print(f"    {nombre:<32} conserva la banda 1 aun en {tope}")


def main():
    perfiles = json.load(open("perfiles.json", encoding="utf-8"))
    benchmark(perfiles)
    barrido(perfiles)
    quiebre(perfiles)


if __name__ == "__main__":
    main()
