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

Cada metrica se marca ademas con COMO se obtuvo, en el vocabulario del plan
(Sec.7.1 de docs/plan_medicion_tempo_aptos_canton.md):
    [HIST]  dato reconstruido de bloques/eventos/estado ya producidos por la
            red (ventana W_H) -- aunque la consulta se haga en vivo contra un
            nodo, lo que se mide ya ocurrio.
    [VIVO]  requiere sondeo continuo mientras el evento ocurre (ventana W_L).
            Hoy eso es solo B2 en Tempo y Aptos (scripts/poll_finality.py).
    [N/A]   transversal o degenerada por diseno de la red, sin ventana
            temporal (E1, D1 en Canton, C1 en Canton).

Al final se escribe ademas resultados/benchmark_final.csv: una fila por
red x escenario con los puntajes, la admisibilidad y un resumen de cuantas
metricas de esa red son historicas / en vivo / no computables -- el
entregable unico para citar en la tesis.

Nada de lo que imprime este script viene de documentacion: cada valor sale
de metrics.csv, que a su vez sale de una consulta reproducible registrada en
resultados/run_manifest.json.
"""
import argparse
import csv
import os
import subprocess
import sys
from collections import defaultdict

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
RES = "resultados"

COLLECTORS = ["collect_tempo.py", "collect_aptos.py", "collect_canton.py"]
COMPUTERS = ["compute_tempo_metrics.py", "compute_aptos_metrics.py", "compute_canton_metrics.py"]
BLOQUES = {"A": "Costo", "B": "Tiempo y caudal", "C": "Concentracion y continuidad", "D": "Primitivas en uso"}

MODO_TAG = {
    "historico": "[HIST]",
    "tiempo_real": "[VIVO]",
    "no_aplica": "[N/A ]",
}

# Que metrica sustenta cada compuerta, para poder avisar en consola cuando una
# compuerta se decide con un dato parcialmente_derivada (ej. B3 en Canton).
GATE_METRICA = {"G1": "B1", "G3": "D2", "G4": "B3"}


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
    print("#  [HIST]=historico (W_H)  [VIVO]=sondeo en tiempo real (W_L)  [N/A]=transversal/degenerada")
    print(f"{'#' * 70}")

    resumen_modo = defaultdict(lambda: defaultdict(int))  # resumen_modo[red][modo] = conteo

    for red in ["tempo", "aptos", "canton"]:
        filas = por_red.get(red, [])
        estado_por_metrica = {f["metrica_id"]: f for f in filas if f["activo"] in ("n/a", "")}
        print(f"\n\n{'-' * 70}")
        print(f" RED: {red.upper()}")
        print(f"{'-' * 70}")

        por_bloque = defaultdict(list)
        for f in filas:
            mid = f["metrica_id"]
            bloque = mid[0] if mid[0] in "ABCD" else "E"
            por_bloque[bloque].append(f)
            resumen_modo[red][f.get("modo_dato", "historico")] += 1

        for bloque, nombre in list(BLOQUES.items()) + [("E", "Transversal")]:
            filas_b = por_bloque.get(bloque, [])
            if not filas_b:
                continue
            print(f"\n  Bloque {bloque} -- {nombre}")
            for f in sorted(filas_b, key=lambda x: x["metrica_id"]):
                pill = estado_pill(f["estado"])
                modo = MODO_TAG.get(f.get("modo_dato", "historico"), "[HIST]")
                valor = f["valor"] if f["valor"] not in (None, "") else "--"
                n = f["n"] if f["n"] not in (None, "") else "--"
                activo = f"  [{f['activo']}]" if f["activo"] and f["activo"] != "n/a" else ""
                print(f"    {modo} {pill} {f['metrica_id']:5s} = {valor:<22s} n={n:<6s}{activo}")
                if f["estado"] != "computada" and f["razon_estado"]:
                    razon = f["razon_estado"]
                    if len(razon) > 110:
                        razon = razon[:107] + "..."
                    print(f"                 -> {razon}")

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
                mid = GATE_METRICA.get(g["compuerta"])
                base = estado_por_metrica.get(mid)
                if base and base["estado"] == "parcialmente_derivada":
                    print(f"           ADVERTENCIA: {g['compuerta']} se decide con {mid}, marcada "
                          f"parcialmente_derivada -- ver razon_estado en metrics.csv antes de leer "
                          f"esta compuerta como definitiva.")

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
    print("#  Resumen de procedencia del dato, por red (cuantas filas de metrics.csv):")
    for red in ["tempo", "aptos", "canton"]:
        rm = resumen_modo[red]
        print(f"    {red:8s} historico={rm.get('historico', 0):<3d} tiempo_real={rm.get('tiempo_real', 0):<3d} "
              f"n/a={rm.get('no_aplica', 0):<3d}")
    print(f"{'#' * 70}")
    print("#  Archivos completos: resultados/metrics.csv, gates.csv, scores.csv,")
    print("#  sensitivity.csv, discrimination.csv, limitaciones.md, run_manifest.json")
    print("#  Entregable definitivo (una fila por red x escenario): resultados/benchmark_final.csv")
    print(f"{'#' * 70}\n")


def escribir_benchmark_final(por_red, scores):
    """Entregable unico y definitivo: una fila por red x escenario con el
    puntaje, la admisibilidad y de donde sale el dato de esa red (cuantas
    metricas historicas, cuantas en vivo, cuantas sin computar todavia).
    No reemplaza metrics.csv/scores.csv/gates.csv (siguen siendo la fuente
    de verdad por metrica); esto es la lectura ejecutiva para citar."""
    resumen = {}
    for red, filas in por_red.items():
        conteo = defaultdict(int)
        for f in filas:
            conteo[f.get("modo_dato", "historico")] += 1
            conteo[f"estado_{f['estado']}"] += 1
        resumen[red] = conteo

    out_path = f"{RES}/benchmark_final.csv"
    campos = [
        "red", "escenario", "admisible", "compuertas_fallidas", "S_total",
        "S_A", "S_B", "S_C", "S_D",
        "metricas_historicas", "metricas_tiempo_real", "metricas_no_aplica",
        "metricas_computadas", "metricas_parcialmente_derivadas", "metricas_no_computables",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for s in scores:
            red = s["red"]
            r = resumen.get(red, {})
            w.writerow({
                "red": red,
                "escenario": s["escenario"],
                "admisible": s["admisible"],
                "compuertas_fallidas": s.get("compuertas_fallidas", ""),
                "S_total": s["S_total"],
                "S_A": s["S_A"], "S_B": s["S_B"], "S_C": s["S_C"], "S_D": s["S_D"],
                "metricas_historicas": r.get("historico", 0),
                "metricas_tiempo_real": r.get("tiempo_real", 0),
                "metricas_no_aplica": r.get("no_aplica", 0),
                "metricas_computadas": r.get("estado_computada", 0),
                "metricas_parcialmente_derivadas": r.get("estado_parcialmente_derivada", 0),
                "metricas_no_computables": r.get("estado_no_computable", 0),
            })
    print(f"benchmark_final.csv escrito en {out_path} ({len(scores)} filas: red x escenario)")


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
    escribir_benchmark_final(por_red, scores)


if __name__ == "__main__":
    main()
