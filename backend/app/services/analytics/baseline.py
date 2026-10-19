"""Linea base de perfiles: convierte resultados/metrics.csv (Tempo, Aptos, Canton) al formato de perfiles.json del modelo
y combina los perfiles medidos de Polygon, Celo y Arbitrum. Nunca inventa valores: lo no computable queda en null."""

import csv
import json

REDES_BENCHMARK = ("tempo", "aptos", "canton")
REDES_TESIS = ("polygon", "celo", "arbitrum")
FACTOR_B3 = 48.0 / 18.0
RECORTE_NOTA = 280


def _flotante(texto):
    try:
        return float(texto) if texto not in ("", None) else None
    except ValueError:
        return None


def _nota(fila, extra=""):
    partes = [f"metrics.csv: estado={fila['estado']}, modo_dato={fila['modo_dato']}, n={fila['n']}"]
    if extra:
        partes.append(extra)
    razon = (fila.get("razon_estado") or "").strip()
    if razon:
        partes.append(razon)
    return " | ".join(partes)[:RECORTE_NOTA]


def _entrada(fila, valor, extra="", cota=False):
    if valor is None:
        return {"valor": None, "nota": _nota(fila, extra)}
    d = {"valor": valor, "sigma": 0.0,
         "nota": _nota(fila, "; ".join(x for x in (extra, "sin estimacion de incertidumbre (sigma=0)") if x))}
    if cota:
        d["cota_inferior"] = True
    return d


def perfiles_desde_metrics_csv(ruta):
    filas = [f for f in csv.DictReader(open(ruta, encoding="utf-8")) if f["red"] in REDES_BENCHMARK]
    por_red = {r: {} for r in REDES_BENCHMARK}
    for f in filas:
        if f["metrica_id"] == "E1":
            continue
        por_red[f["red"]].setdefault(f["metrica_id"], f)

    perfiles = {}
    for red, mets in por_red.items():
        p = {}
        a1 = _flotante(mets["A1"]["valor"]) if "A1" in mets else None
        for mid, f in mets.items():
            v = _flotante(f["valor"])
            if mid == "A1":
                p["A1"] = _entrada(f, v)
            elif mid == "A2":
                p["A2"] = _entrada(f, v / a1 if (v is not None and a1) else None,
                                   "A2 del modelo = p95/mediana del costo")
            elif mid in ("A3", "B1", "B2", "C2", "C4", "C5", "D1", "D2", "D3"):
                p[mid] = _entrada(f, v)
            elif mid == "B3":
                p["B3"] = _entrada(f, v * FACTOR_B3 if v is not None else None,
                                   "capacidad H_cfg / 18 TPS requeridos (csv usa 48)",
                                   cota=(red == "canton"))
            elif mid == "C1b":
                p["C1"] = _entrada(f, v, "C1 del modelo = HHI de peso de consenso (C1b, D3 del plan)")
            elif mid == "C3":
                p["C3"] = _entrada(f, v * 100.0 if v is not None else None, "continuidad en porcentaje")
        perfiles[red] = p
    return perfiles


def perfiles_tesis(ruta):
    datos = json.loads(open(ruta, encoding="utf-8").read())
    return {r: datos[r] for r in REDES_TESIS if r in datos}


def construir_linea_base(ruta_perfiles_json, ruta_metrics_csv):
    base = perfiles_tesis(ruta_perfiles_json)
    base.update(perfiles_desde_metrics_csv(ruta_metrics_csv))
    return base
