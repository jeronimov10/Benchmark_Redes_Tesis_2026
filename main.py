#!/usr/bin/env python3
"""Punto de entrada unico del benchmark Tempo / Aptos / Canton.

    python main.py                 -> usa los datos crudos ya descargados en
                                       resultados/raw/ (rapido, no toca la red)
    python main.py --collect        -> vuelve a consultar las tres APIs en vivo
                                       antes de calcular (lento, sujeto a rate
                                       limit; ver scripts/collect_*.py)

En cualquier caso, al terminar corre compute_*_metrics -> build_deliverables
-> score_engine, y despues imprime un reporte diferenciado por red y por
bloque (A/B/C/D) de exactamente que se pudo medir, con que n, y por que no
se pudo medir el resto. Los mismos numeros quedan en resultados/*.csv.

Nada de lo que imprime este script viene de documentacion: cada valor sale
de metrics.csv, que a su vez sale de una consulta reproducible registrada en
resultados/run_manifest.json.
"""
import argparse
import csv
import subprocess
import sys
from collections import defaultdict

SCRIPTS = "scripts"
RES = "resultados"

COLLECTORS = ["collect_tempo.py", "collect_aptos.py", "collect_canton.py"]
COMPUTERS = ["compute_tempo_metrics.py", "compute_aptos_metrics.py", "compute_canton_metrics.py"]
BLOQUES = {"A": "Costo", "B": "Tiempo y caudal", "C": "Concentracion y continuidad", "D": "Primitivas en uso"}


def run(script):
    print(f"\n{'=' * 70}\n>>> {script}\n{'=' * 70}")
    r = subprocess.run([sys.executable, f"{SCRIPTS}/{script}"])
    if r.returncode != 0:
        print(f"AVISO: {script} termino con codigo {r.returncode} -- revisa el log de arriba.")


def cargar_metrics():
    filas = list(csv.DictReader(open(f"{RES}/metrics.csv", encoding="utf-8")))
    por_red = defaultdict(list)
    for f in filas:
        por_red[f["red"]].append(f)
    return por_red


def cargar_scores():
    try:
        return list(csv.DictReader(open(f"{RES}/scores.csv", encoding="utf-8")))
    except FileNotFoundError:
        return []


def cargar_gates():
    try:
        return list(csv.DictReader(open(f"{RES}/gates.csv", encoding="utf-8")))
    except FileNotFoundError:
        return []


def estado_pill(estado):
    return {
        "computada": "[OK]  ",
        "parcialmente_derivada": "[PARC]",
        "no_computable": "[----]",
        "degenerada": "[DEGE]",
        "no_homogenea": "[NOHM]",
    }.get(estado, "[??? ]")


def imprime_reporte(por_red, scores, gates):
    print(f"\n\n{'#' * 70}")
    print("#  REPORTE DIFERENCIADO -- Tempo / Aptos / Canton")
    print(f"{'#' * 70}")

    for red in ["tempo", "aptos", "canton"]:
        filas = por_red.get(red, [])
        print(f"\n\n{'-' * 70}")
        print(f" RED: {red.upper()}")
        print(f"{'-' * 70}")

        por_bloque = defaultdict(list)
        for f in filas:
            mid = f["metrica_id"]
            bloque = mid[0] if mid[0] in "ABCD" else "E"
            por_bloque[bloque].append(f)

        for bloque, nombre in list(BLOQUES.items()) + [("E", "Transversal")]:
            filas_b = por_bloque.get(bloque, [])
            if not filas_b:
                continue
            print(f"\n  Bloque {bloque} -- {nombre}")
            for f in sorted(filas_b, key=lambda x: x["metrica_id"]):
                pill = estado_pill(f["estado"])
                valor = f["valor"] if f["valor"] not in (None, "") else "--"
                n = f["n"] if f["n"] not in (None, "") else "--"
                activo = f"  [{f['activo']}]" if f["activo"] and f["activo"] != "n/a" else ""
                print(f"    {pill} {f['metrica_id']:5s} = {valor:<22s} n={n:<6s}{activo}")
                if f["estado"] != "computada" and f["razon_estado"]:
                    razon = f["razon_estado"]
                    if len(razon) > 110:
                        razon = razon[:107] + "..."
                    print(f"           -> {razon}")

        # compuertas de esta red
        gates_red = [g for g in gates if g["red"] == red]
        if gates_red:
            print(f"\n  Compuertas:")
            vistos = set()
            for g in gates_red:
                key = (g["escenario"], g["compuerta"], g.get("activo", ""))
                if key in vistos:
                    continue
                vistos.add(key)
                activo = f" [{g['activo']}]" if g.get("activo") and g["activo"] != "n/a" else ""
                print(f"    {g['escenario']} {g['compuerta']:5s}{activo:35s} -> {g['resultado']}")

        # puntajes de esta red
        scores_red = [s for s in scores if s["red"] == red]
        if scores_red:
            print(f"\n  Puntajes (S por bloque, S_total geometrico, admisible):")
            for s in scores_red:
                sa = s["S_A"] or "--"
                sb = s["S_B"] or "--"
                sc = s["S_C"] or "--"
                sd = s["S_D"] or "--"
                st = s["S_total"] or "--"
                print(f"    {s['escenario']}: A={sa[:5]:<6s} B={sb[:5]:<6s} C={sc[:5]:<6s} D={sd[:5]:<6s}  "
                      f"S={st[:5] if st != '--' else '--':<6s}  admisible={s['admisible']}")

    print(f"\n\n{'#' * 70}")
    print("#  Archivos completos: resultados/metrics.csv, gates.csv, scores.csv,")
    print("#  sensitivity.csv, discrimination.csv, limitaciones.md, run_manifest.json")
    print(f"{'#' * 70}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collect", action="store_true", help="Vuelve a consultar las tres redes en vivo antes de calcular")
    args = ap.parse_args()

    if args.collect:
        for c in COLLECTORS:
            run(c)

    for c in COMPUTERS:
        run(c)

    run("build_deliverables.py")
    run("score_engine.py")

    por_red = cargar_metrics()
    scores = cargar_scores()
    gates = cargar_gates()
    imprime_reporte(por_red, scores, gates)


if __name__ == "__main__":
    main()
