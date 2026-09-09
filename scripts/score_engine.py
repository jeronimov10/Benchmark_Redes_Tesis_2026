"""Motor de puntajes -- implementa Sec.5.6/5.7 (normalizacion, agregacion) y Sec.6
(compuertas) del plan de medicion, sobre lo que haya en resultados/metrics.csv.

No inventa nada que falte: una metrica marcada no_computable en metrics.csv
simplemente no entra al puntaje de su bloque, y el bloque se renormaliza sobre
los pesos de lo que si esta disponible (se documenta como supuesto, no se oculta).

Salidas: resultados/gates.csv, resultados/scores.csv, resultados/sensitivity.csv,
resultados/discrimination.csv
"""
import csv
import json
import math
import random
from collections import defaultdict

RES = "resultados"
REDES = ["tempo", "aptos", "canton"]
ESCENARIOS = ["E1", "E2", "E3"]
N_REPLICAS = 10000

# ---------------------------------------------------------------------------
# Catalogo de umbrales heredado sin cambios del documento de referencia (D8),
# salvo C5 que usa clip lineal por tener t=0 (log indefinido en cero).
# direccion: "menor" o "mayor" es mejor.
# ---------------------------------------------------------------------------
UMBRALES = {
    "A1": dict(t=0.001, w=0.01, direccion="menor"),      # fraccion del ticket
    "A2": dict(t=1.5, w=10, direccion="menor"),
    "A3": dict(t=0.2, w=2.0, direccion="menor", abs=True),
    "B1": dict(t=5, w=20, direccion="menor"),
    "B2": dict(t=60, w=604800, direccion="menor"),
    "B3": dict(t=5, w=1, direccion="mayor"),              # H_cfg
    "C1b": dict(t=0.10, w=1.00, direccion="menor"),
    "C2": dict(t=15, w=1, direccion="mayor"),
    "C3": dict(t=5.0, w=3.0, direccion="mayor", nines=True),  # en numero de nueves
    "C4": dict(t=0.001, w=0.05, direccion="menor"),
    "C5": dict(t=0, w=5, direccion="menor", lineal=True),
    "D1": dict(t=0.50, w=0.01, direccion="mayor"),
    "D2": dict(t=0.20, w=0.001, direccion="mayor"),
    "D3": dict(t=0.10, w=0.001, direccion="mayor"),
}

BLOQUE_DE = {
    "A1": "A", "A2": "A", "A3": "A",
    "B1": "B", "B2": "B", "B3": "B",
    "C1b": "C", "C2": "C", "C3": "C", "C4": "C", "C5": "C",
    "D1": "D", "D2": "D", "D3": "D",
}

# Pesos entre bloques, heredados de Sec.5.6 (A4 eliminada, redistribuida)
PESOS_BLOQUE = {
    "E1": {"A": 0.45, "B": 0.15, "C": 0.15, "D": 0.25},
    "E2": {"A": 0.35, "B": 0.35, "C": 0.15, "D": 0.15},
    "E3": {"A": 0.10, "B": 0.30, "C": 0.40, "D": 0.20},
}

# Pesos internos del bloque A (renormalizados tras eliminar A4, Sec.5.6)
PESOS_A = {
    "E1": {"A1": 0.526, "A2": 0.263, "A3": 0.211},
    "E2": {"A1": 0.389, "A2": 0.278, "A3": 0.333},
    "E3": {"A1": 1 / 3, "A2": 1 / 3, "A3": 1 / 3},
}

# Pesos internos del bloque B. El plan solo fija la metrica dominante por
# escenario (B1 domina E2 con 0.60; B2 domina E3 con 0.55); el resto se
# reparte uniforme. SUPUESTO EXPLICITO, no esta en el texto del plan letra
# por letra -- se declara aqui y en limitaciones.md.
PESOS_B = {
    "E1": {"B1": 1 / 3, "B2": 1 / 3, "B3": 1 / 3},
    "E2": {"B1": 0.60, "B2": 0.20, "B3": 0.20},
    "E3": {"B1": 0.225, "B2": 0.55, "B3": 0.225},
}

# Bloque C: C1b es la primaria (toma el peso que tenia C1 en el original),
# el resto uniforme entre las 5 metricas de C (C1 se reporta aparte, secundaria,
# no entra al puntaje: es no_computable en Canton y redundante con C1b).
PESOS_C = {e: {"C1b": 0.20, "C2": 0.20, "C3": 0.20, "C4": 0.20, "C5": 0.20} for e in ESCENARIOS}

# Bloque D: uniforme
PESOS_D = {e: {"D1": 1 / 3, "D2": 1 / 3, "D3": 1 / 3} for e in ESCENARIOS}

PESOS_INTERNOS = {"A": PESOS_A, "B": PESOS_B, "C": PESOS_C, "D": PESOS_D}

# Ticket de referencia por escenario para expresar A1/A2 como fraccion.
# E1/E2 vienen directo del Anexo del plan (umbrales del Banco de la Republica).
# E3 (>COP 100 millones) SI requiere una tasa de cambio aproximada que el plan
# no fija con un numero unico -- se documenta como supuesto de conversion,
# no como dato recolectado de ninguna red.
TICKET_USD = {"E1": 350, "E2": 40, "E3": 24000}
FX_NOTA_E3 = "E3 usa un tipo de cambio aproximado ~4.200 COP/USD para convertir el piso de COP 100M; es un supuesto de conversion declarado, no un dato de ninguna red."

GATES_POR_ESCENARIO = {
    "G1": ["E2"],
    "G2p": ["E1", "E2", "E3"],
    "G3": ["E1", "E2", "E3"],
    "G4": ["E2", "E3"],
}


def clip(z, a=0.0, b=1.0):
    return min(max(z, a), b)


def normaliza(metrica_id, valor):
    """Devuelve s_i en [0,1], o None si no se puede normalizar."""
    cfg = UMBRALES[metrica_id]
    t, w = cfg["t"], cfg["w"]
    if valor is None:
        return None
    x = valor
    if cfg.get("abs"):
        x = abs(x)
    if cfg.get("lineal"):
        # C5: t=0 hace indefinido el logaritmo -> clip lineal declarado
        if cfg["direccion"] == "menor":
            return clip((w - x) / (w - t), 0, 1)
        return clip((x - w) / (t - w), 0, 1)
    if cfg.get("nines"):
        # x llega como porcentaje (ej 99.999) -> se transforma a numero de nueves
        if x >= 100:
            x = 100 - 1e-9
        nu = -math.log10(1 - x / 100)
        x = nu
    try:
        if cfg["direccion"] == "menor":
            return clip((math.log(w) - math.log(x)) / (math.log(w) - math.log(t)), 0, 1)
        else:
            return clip((math.log(x) - math.log(w)) / (math.log(t) - math.log(w)), 0, 1)
    except (ValueError, ZeroDivisionError):
        return None


def carga_metrics():
    rows = list(csv.DictReader(open(f"{RES}/metrics.csv", encoding="utf-8")))
    # valor computable = estado in (computada, parcialmente_derivada) y valor numerico
    valores = defaultdict(dict)  # valores[red][metrica_id] = (valor, estado, unidad, activo)
    for r in rows:
        red = r["red"]
        mid = r["metrica_id"]
        if mid == "E1":
            continue  # E1 se maneja aparte (transversal, no bloque)
        estado = r["estado"]
        try:
            val = float(r["valor"]) if r["valor"] not in (None, "") else None
        except ValueError:
            val = None
        if val is not None and estado in ("computada", "parcialmente_derivada"):
            # si ya hay un valor para ese id (ej. filas duplicadas), se queda el primero
            if mid not in valores[red]:
                valores[red][mid] = dict(valor=val, estado=estado, unidad=r["unidad"], activo=r["activo"])
    return rows, valores


def aplica_conversion_A1_A2(valores):
    """A1/A2 en metrics.csv estan en USD absolutos (costo), no como fraccion
    del ticket todavia. Aqui se deriva, por escenario, la fraccion real que
    exige el catalogo (Sec.5.1), sin tocar el valor original."""
    fracciones = {}  # fracciones[red][escenario][metrica_id] = fraccion
    for red, metricas in valores.items():
        fracciones[red] = {}
        for esc in ESCENARIOS:
            fracciones[red][esc] = {}
            ticket = TICKET_USD[esc]
            for mid in ("A1", "A2"):
                if mid in metricas and metricas[mid]["unidad"] == "USD":
                    fracciones[red][esc][mid] = metricas[mid]["valor"] / ticket
    return fracciones


def evalua_gates(valores, fracciones):
    filas = []
    for red in REDES:
        m = valores.get(red, {})
        for esc in ESCENARIOS:
            b1 = m.get("B1", {}).get("valor")
            if esc in GATES_POR_ESCENARIO["G1"]:
                if b1 is None:
                    filas.append((red, esc, "G1", "no_evaluable", ""))
                else:
                    filas.append((red, esc, "G1", "pasa" if b1 <= 20 else "falla", b1))
            # G3: D2 > 0
            if esc in GATES_POR_ESCENARIO["G3"]:
                d2 = m.get("D2", {}).get("valor")
                if d2 is None:
                    filas.append((red, esc, "G3", "no_evaluable", ""))
                else:
                    filas.append((red, esc, "G3", "pasa" if d2 > 0 else "falla", d2))
            # G4: B3 (H_cfg) >= 1
            if esc in GATES_POR_ESCENARIO["G4"]:
                hv = m.get("B3", {}).get("valor")
                if hv is None:
                    filas.append((red, esc, "G4", "no_evaluable", ""))
                else:
                    filas.append((red, esc, "G4", "pasa" if hv >= 1 else "falla", hv))
    return filas


def evalua_G2p(metrics_rows):
    """G2' = E1 (observabilidad por tercero) == 1 Y tau_F computable (B2
    computada o parcialmente_derivada) para ese activo."""
    filas = []
    e1_rows = [r for r in metrics_rows if r["metrica_id"] == "E1"]
    b2_por_red = {}
    for r in metrics_rows:
        if r["metrica_id"] == "B2":
            b2_por_red[r["red"]] = r["estado"] in ("computada", "parcialmente_derivada")
    for r in e1_rows:
        red = r["red"]
        activo = r["activo"]
        try:
            e1_val = float(r["valor"])
        except (ValueError, TypeError):
            e1_val = None
        tau_f_ok = b2_por_red.get(red, False)
        if e1_val is None:
            estado = "no_evaluable"
        elif e1_val == 1 and tau_f_ok:
            estado = "pasa"
        elif e1_val == 1 and not tau_f_ok:
            estado = "no_evaluable"  # E1 ok pero B2 no ejecutada aun, no es que falle la red
        else:
            estado = "falla"
        for esc in ESCENARIOS:
            filas.append((red, activo, esc, "G2p", estado, e1_val))
    return filas


def agrega_puntajes(valores, fracciones):
    filas_scores = []
    for red in REDES:
        m = valores.get(red, {})
        for esc in ESCENARIOS:
            bloque_scores = {}
            bloque_n = {}
            for bloque in "ABCD":
                pesos = PESOS_INTERNOS[bloque][esc]
                acumulado = 0.0
                peso_total_disponible = 0.0
                n_disp = 0
                for mid, peso in pesos.items():
                    if mid in ("A1", "A2"):
                        valor = fracciones.get(red, {}).get(esc, {}).get(mid)
                    else:
                        valor = m.get(mid, {}).get("valor")
                    if valor is None:
                        continue
                    s = normaliza(mid, valor)
                    if s is None:
                        continue
                    acumulado += peso * s
                    peso_total_disponible += peso
                    n_disp += 1
                if peso_total_disponible > 0:
                    bloque_scores[bloque] = acumulado / peso_total_disponible
                    bloque_n[bloque] = n_disp
                else:
                    bloque_scores[bloque] = None
                    bloque_n[bloque] = 0
            filas_scores.append(dict(red=red, escenario=esc, **{f"S_{b}": bloque_scores[b] for b in "ABCD"},
                                      **{f"n_{b}": bloque_n[b] for b in "ABCD"}))
    return filas_scores


def agrega_S(fila_bloque, escenario, eps=0.05):
    pesos = PESOS_BLOQUE[escenario]
    prod = 1.0
    algun_bloque = False
    for b, w in pesos.items():
        sd = fila_bloque.get(f"S_{b}")
        if sd is None:
            continue
        algun_bloque = True
        prod *= max(sd, eps) ** w
    return prod if algun_bloque else None


def main():
    metrics_rows, valores = carga_metrics()
    fracciones = aplica_conversion_A1_A2(valores)

    # -------- gates.csv --------
    gates = evalua_gates(valores, fracciones)
    g2p = evalua_G2p(metrics_rows)
    with open(f"{RES}/gates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["red", "activo", "escenario", "compuerta", "resultado", "valor_medido"])
        for red, esc, gate, resultado, val in gates:
            w.writerow([red, "n/a", esc, gate, resultado, val])
        for red, activo, esc, gate, resultado, val in g2p:
            w.writerow([red, activo, esc, gate, resultado, val])
    print(f"gates.csv escrito con {len(gates) + len(g2p)} filas")

    # admisibilidad por red x escenario (falla si cualquier compuerta aplicable falla)
    inadmisible = defaultdict(set)
    for red, esc, gate, resultado, _ in gates:
        if resultado == "falla":
            inadmisible[(red, esc)].add(gate)
    g2p_por_red_esc = defaultdict(list)
    for red, activo, esc, gate, resultado, _ in g2p:
        g2p_por_red_esc[(red, esc)].append((activo, resultado))
    for (red, esc), activos in g2p_por_red_esc.items():
        if activos and all(r == "falla" for _, r in activos):
            inadmisible[(red, esc)].add("G2p")

    # -------- scores.csv --------
    filas_scores = agrega_puntajes(valores, fracciones)
    with open(f"{RES}/scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["red", "escenario", "S_A", "n_A", "S_B", "n_B", "S_C", "n_C", "S_D", "n_D", "S_total", "admisible", "compuertas_fallidas"])
        for fila in filas_scores:
            key = (fila["red"], fila["escenario"])
            admisible = key not in inadmisible
            s_total = agrega_S(fila, fila["escenario"]) if admisible else None
            w.writerow([
                fila["red"], fila["escenario"],
                fila["S_A"], fila["n_A"], fila["S_B"], fila["n_B"],
                fila["S_C"], fila["n_C"], fila["S_D"], fila["n_D"],
                s_total, "si" if admisible else "no",
                ";".join(sorted(inadmisible.get(key, []))),
            ])
    print(f"scores.csv escrito con {len(filas_scores)} filas")

    # -------- sensitivity.csv (Dirichlet sobre los pesos ENTRE bloques) --------
    with open(f"{RES}/sensitivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["red", "escenario", "n_replicas", "S_p5", "S_mediana", "S_p95", "nota"])
        for fila in filas_scores:
            red, esc = fila["red"], fila["escenario"]
            key = (red, esc)
            if key in inadmisible:
                w.writerow([red, esc, 0, "", "", "", "inadmisible: " + ",".join(sorted(inadmisible[key]))])
                continue
            base_pesos = PESOS_BLOQUE[esc]
            bloques_disp = [b for b in "ABCD" if fila.get(f"S_{b}") is not None]
            if not bloques_disp:
                w.writerow([red, esc, 0, "", "", "", "sin bloques computables"])
                continue
            kappa = 50
            alpha = [kappa * base_pesos[b] for b in bloques_disp]
            muestras = []
            for _ in range(N_REPLICAS):
                pesos_muestreados = dirichlet(alpha)
                prod = 1.0
                for b, wgt in zip(bloques_disp, pesos_muestreados):
                    prod *= max(fila[f"S_{b}"], 0.05) ** wgt
                muestras.append(prod)
            muestras.sort()
            n = len(muestras)
            nota = "renormalizado sobre " + "+".join(bloques_disp) if len(bloques_disp) < 4 else ""
            w.writerow([red, esc, N_REPLICAS,
                        muestras[int(0.05 * n)], muestras[int(0.5 * n)], muestras[int(0.95 * n) - 1],
                        nota])
    print("sensitivity.csv escrito")

    # -------- discrimination.csv --------
    with open(f"{RES}/discrimination.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metrica_id", "valores_por_red", "rango", "discrimino"])
        for mid in UMBRALES:
            vals = {}
            for red in REDES:
                v = valores.get(red, {}).get(mid, {}).get("valor")
                if v is not None:
                    vals[red] = v
            if len(vals) < 2:
                w.writerow([mid, json.dumps(vals), "", "no_evaluable (menos de 2 redes con dato)"])
                continue
            rango = max(vals.values()) - min(vals.values())
            rel = rango / (abs(max(vals.values(), key=abs)) + 1e-12)
            discrimino = "si" if rel > 0.05 else "no"
            w.writerow([mid, json.dumps(vals), rango, discrimino])
    print("discrimination.csv escrito")


def dirichlet(alpha):
    xs = [random.gammavariate(a, 1.0) for a in alpha]
    s = sum(xs)
    return [x / s for x in xs]


if __name__ == "__main__":
    main()
