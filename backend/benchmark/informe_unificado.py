"""Informe unificado de las seis redes (Polygon, Celo, Arbitrum, Tempo, Aptos, Canton): lee resultados/metrics.csv y backend/modelo/perfiles.json, construye la linea base con la misma conversion que usa la app y escribe resultados/benchmark.md, benchmark.html y limitaciones.md. Los valores salen de los archivos de resultados; no se completa nada con documentacion."""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "modelo"))

import modelo
from app.services.analytics.baseline import construir_linea_base
from app.utils.md_html import kpis, md_a_html, pagina

RES = RAIZ / "resultados"
REDES = ["polygon", "celo", "arbitrum", "tempo", "aptos", "canton"]
NOMBRE = {"polygon": "Polygon", "celo": "Celo", "arbitrum": "Arbitrum", "tempo": "Tempo", "aptos": "Aptos", "canton": "Canton"}
TAC = ("tempo", "aptos", "canton")
METRICAS = [
    ("A1", "Costo mediano / ticket", "USD"), ("A2", "Cola de costo (p95 / mediana)", "razon"), ("A3", "Sensibilidad del costo a la congestion (beta)", "indice"),
    ("A4", "Costo de anclaje por transaccion", "USD"), ("B1", "Latencia de inclusion p95", "s"), ("B2", "Tiempo a finalidad", "s"),
    ("B2b", "Tiempo a irrevocabilidad en Ethereum", "s"), ("B3", "Margen de capacidad (capacidad / 18 TPS)", "razon"), ("C1", "Concentracion de produccion o consenso (HHI)", "indice"),
    ("C2", "Operadores que concentran mas del 50 %", "conteo"), ("C3", "Continuidad", "%"), ("C4", "Tasa de fallo", "fraccion"),
    ("C5", "Cambios de implementacion en la ventana", "conteo"), ("D1", "Pago sin activo volatil propio", "fraccion"), ("D2", "Transferencias con datos asociables a una orden", "fraccion"),
    ("D3", "Transacciones multi-transferencia", "fraccion"),
]
CASOS = {
    "remesa_usd300": "Remesa de USD 300 (COP 1 200 000, transfronteriza, espera 1 h, irrevocabilidad baja)",
    "tienda_cop15000": "Compra en tienda (COP 15 000, domestica, espera 3 s, irrevocabilidad media)",
    "domestico_cop1200000": "Pago domestico (COP 1 200 000, espera 60 s, irrevocabilidad media)",
    "altovalor_cop80M": "Pago de alto valor (COP 80 000 000, espera 10 min, irrevocabilidad alta)",
}
LIM_PCA = {
    "polygon": ["A3 no computable: el ajuste de la pendiente de congestion no es util (R2 0,003).",
                "B3 es cota inferior: la red no se saturo en la ventana (141,3 TPS en el percentil 99 frente a 18 requeridos).",
                "C3 esta marcada como documental en la linea base: cota al 95 % con 0 incidentes en 356 dias, no un valor medido con una consulta a la red.",
                "C1 y C2 salen de 8 productores de bloques observados en 19 509 bloques; C5 sale de 61 lecturas de la ranura de implementacion del proxy (zeppelin)."],
    "celo": ["A3 no computable: el ajuste no es util (R2 0,046).",
             "B3 es cota inferior: 36,0 TPS en el percentil 99 frente a 18 requeridos, sin saturacion.",
             "C1 = 1 y C2 = 1 reflejan un productor unico de direccion de sistema, que no identifica a una organizacion; el valor describe la arquitectura, no el reparto entre operadores.",
             "B2b tiene n = 122 confirmaciones en Ethereum (p95 3,52 dias).", "C3 esta marcada como documental en la linea base: cota al 95 % con 1 incidente en 552 dias, no una medicion con una consulta a la red."],
    "arbitrum": ["A3 no computable: la ocupacion es casi constante (rango 0,0000), no hay variacion para ajustar.",
                 "B3 es cota inferior: 115,8 TPS en el percentil 99 frente a 18 requeridos, sin saturacion.",
                 "C1 = 0,994 y C2 = 1 sobre 16 direcciones productoras observadas en 20 000 bloques.",
                 "B2b tiene n = 118 confirmaciones en Ethereum (p95 6,45 dias); el tamano de muestra de D2 y D3 es el menor de las tres (2 266 transacciones).",
                 "C3 esta marcada como documental en la linea base: cota al 95 % con 0 incidentes en 271 dias, no una medicion con una consulta a la red."],
}
TRANSVERSALES = [
    ("Ventanas distintas entre grupos", "Polygon, Celo y Arbitrum vienen de la medicion de la tesis (ventana de 90 dias, octubre de 2026, `backend/modelo/perfiles.json`). Tempo, Aptos y Canton vienen de una muestra reducida de verificacion (Tempo: 700 bloques y 220 transacciones; Aptos: 350 bloques; Canton: 8 000 eventos en unos 493 s del 2026-09-07, una ventana dominada por un burst periodico y no representativa del trafico tipico), no de la ventana W_H de 14 dias que fija el plan. Las seis columnas son comparables en definicion de metrica, no en tamano de muestra ni en fecha."),
    ("Un solo proveedor por red", "El plan exige un segundo proveedor independiente por red para el control de concordancia. No se cumplio para ninguna: cada red se consulto con un unico endpoint publico (`resultados/run_manifest.json`). En Canton ademas es un espejo publico de terceros (`api.cantonnodes.com`), porque los Scan de los Super Validadores rechazan el acceso publico (403/RBAC)."),
    ("Sin bootstrap en Tempo, Aptos y Canton", "Los valores de T/A/C no traen intervalo de confianza; en el modelo entran con `sigma = 0`, de modo que la incertidumbre del Monte Carlo para esas redes viene solo de los pesos, no de la medicion."),
    ("A4 solo existe en Polygon, Celo y Arbitrum", "A4 (costo de anclaje) aplica a los rollups que publican en Ethereum. Tempo, Aptos y Canton son redes de capa 1 propia: A4 no aplica y no se imputa."),
    ("Compuerta G2 y Aptos", "El modelo marca a Aptos como inadmisible por G2 (`sin anclaje verificable en Ethereum`) porque su B2 no es computable. Es un efecto de que falta la medicion, no una evidencia de que Aptos no sea apta: sin B2 la red no puede pasar la compuerta."),
    ("Monte Carlo sin semilla en el motor de puntajes", "El Monte Carlo del motor del plan (`score_engine.py`) usa el generador de numeros aleatorios sin semilla, asi que `sensitivity.csv` cambia ligeramente entre ejecuciones; el modelo de la tesis (`modelo.recomendar`) usa semilla 42 y es determinista."),
    ("TRM fija", "Todos los casos usan 4 000 COP/USD, como la tesis; el ticket en USD depende de ese supuesto."),
    ("Quirk de `normaliza()` con log(0)", "En `score_engine.py`, una metrica `mayor es mejor` con valor exactamente 0 (hoy `canton.D3 = 0`) se excluye del promedio del bloque sin contar como cero puntos; mirar `n_D` en `scores.csv` antes de leer el bloque D. No se corrigio porque cambiaria el puntaje de las 18 combinaciones red x escenario."),
    ("Los RPC publicos son inestables", "Los endpoints publicos cambian de proveedor, limitan por IP (Aptos anonimo cobra por tamano de respuesta) y los nodos L1 publicos guardan solo ~10 000 bloques; por eso la recalibracion en vivo de P/C/A usa una ventana de 24 h y no sustituye la linea base de 90 dias."),
]
SIMULACION = [
    "Los 12 perfiles son personas sinteticas: los rangos de los perfiles 4 a 12 son supuestos de diseno, no datos de usuarios reales. Los resultados se leen por perfil, nunca como porcentaje de la poblacion.",
    "El panel continuo (P7) usa 60 a 63 de 74 metricas vivas esperadas; el resto cae a la linea base y el informe marca la procedencia.",
    "Un perfil que llega al tope de 400 usuarios en P1 (Micropago de transporte, y Remesa urgente en vivo) indica que la cuota modal no se estabilizo con el tope fijado.",
    "El umbral de lo que cuenta como cuota relevante de alertas no se fijo: se reportan las cifras, no un veredicto.",
    "Los contrafactuales solo quitan redes, metricas o sigma; no inventan datos.",
    "El panel corrio unos 11,9 dias, por encima del minimo de 3 dias que pide B2 de Tempo (72 h) y por debajo de los 14 dias ideales.",
]


def _csv(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fmt(v):
    if v is None:
        return "n/d"
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1000 or a < 0.001:
        return f"{v:.3g}"
    return f"{v:.4g}"


def _estado(red, mid, entrada, filas):
    if entrada is None or entrada.get("valor") is None:
        if red in TAC:
            razon = next((f["razon_estado"] for f in filas if f["red"] == red and f["metrica_id"] == mid and f["estado"] == "no_computable"), "")
            return "no computable" if razon or mid in ("A4",) else "no aplica" if mid == "A4" else "no computable"
        return "no computable" if mid != "A4" else "no aplica"
    if entrada.get("cota_inferior"):
        return "cota inferior"
    if red in TAC:
        f = next((f for f in filas if f["red"] == red and f["metrica_id"] == ("C1b" if mid == "C1" else mid)), None)
        if f and f["estado"] == "parcialmente_derivada":
            return "parcial"
    return "medida"


def tabla_metricas(base, filas):
    cab = ["metrica", "descripcion", "unidad"] + [NOMBRE[r] for r in REDES]
    out = []
    for mid, desc, unidad in METRICAS:
        celdas = []
        for r in REDES:
            e = base.get(r, {}).get(mid)
            est = _estado(r, mid, e, filas)
            v = None if e is None else e.get("valor")
            celdas.append(_fmt(v) if est in ("medida",) else f"{_fmt(v)} ({est})" if v is not None else est)
        out.append([f"**{mid}**", desc, unidad] + celdas)
    return cab, out


def tabla_md(cab, filas):
    return ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)] + ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]


def cobertura(base, filas):
    out = []
    for r in REDES:
        est = [_estado(r, mid, base.get(r, {}).get(mid), filas) for mid, _, _ in METRICAS]
        out.append([NOMBRE[r], est.count("medida"), est.count("parcial"), est.count("cota inferior"), est.count("no computable"), est.count("no aplica")])
    return out


def correr_modelo(base):
    casos = json.loads((BACKEND / "modelo" / "casos_referencia.json").read_text(encoding="utf-8"))
    out = {}
    for clave, caso in casos.items():
        out[clave] = modelo.recomendar(base, **caso["entrada"], replicas=10000)
    return out


def seccion_modelo(resultados):
    lineas = []
    victorias = {r: 0 for r in REDES}
    for clave, r in resultados.items():
        c = r["caso"]
        lineas += [f"### {CASOS[clave]}", "",
                   f"Ticket USD {c['ticket_usd']:,.2f}. Composicion: " + ", ".join(f"{k} {v:.0%}" for k, v in r["composicion"].items()) + f". Certidumbre {r['certidumbre']}.", ""]
        filas = []
        for b in r["bandas"]:
            for red in b["redes"]:
                p = b["puntajes"][red]
                filas.append([b["banda"], NOMBRE[red], p["mediana"], f"{p['p05']} - {p['p95']}"])
        lineas += tabla_md(["banda", "red", "puntaje mediano", "p05 - p95"], filas)
        if r["bandas"]:
            for red in r["bandas"][0]["redes"]:
                victorias[red] += 1
            if len(r["bandas"][0]["redes"]) > 1:
                lineas += ["", f"La banda 1 reune {', '.join(NOMBRE[x] for x in r['bandas'][0]['redes'])}: estan empatadas, no hay una ganadora unica ({r['bandas'][0].get('no_distinguibles', '')})."]
            det = r.get("determinante")
            if det:
                lineas += ["", f"Metrica que mas separa la banda 1 de la 2: **{det['metrica']}** (contribucion {det['contribucion']})."]
        if r["inadmisibles"]:
            lineas += ["", "Inadmisibles: " + "; ".join(f"{NOMBRE[red]} ({', '.join(f'{g[0]}: {g[1]}' for g in fall)})" for red, fall in r["inadmisibles"].items()) + "."]
        for adv in r["advertencias"]:
            lineas += ["", f"Advertencia del modelo: {adv}."]
        lineas.append("")
    return lineas, victorias


def seccion_tac():
    scores = _csv(RES / "benchmark_final.csv")
    cab = ["red", "escenario", "admisible", "compuertas fallidas", "S_total", "S_A", "S_B", "S_C", "S_D", "historicas", "tiempo real", "no aplica", "computadas", "parciales", "no computables"]
    filas = []
    for f in scores:
        def n(x):
            return f"{float(x):.3f}" if x not in ("", None) else "--"
        filas.append([NOMBRE[f["red"]], f["escenario"], f["admisible"], f["compuertas_fallidas"] or "-", n(f["S_total"]), n(f["S_A"]), n(f["S_B"]), n(f["S_C"]), n(f["S_D"]),
                      f["metricas_historicas"], f["metricas_tiempo_real"], f["metricas_no_aplica"], f["metricas_computadas"], f["metricas_parcialmente_derivadas"], f["metricas_no_computables"]])
    return tabla_md(cab, filas)


def construir_benchmark(base, filas, resultados, ahora):
    t_filas = cobertura(base, filas)
    cab, tm = tabla_metricas(base, filas)
    modelo_md, victorias = seccion_modelo(resultados)
    n_metricas = len([f for f in filas if f["metrica_id"] != "E1"])
    md = ["# Resultados del benchmark: seis redes", "",
          f"Generado el {ahora:%Y-%m-%d} a partir de `resultados/metrics.csv` (Tempo, Aptos, Canton), `backend/modelo/perfiles.json` (Polygon, Celo, Arbitrum) y `backend/modelo/modelo.py` sin modificar. "
          "Todos los datos son historicos (ya producidos por la red); la unica metrica de tiempo real, B2 en Tempo y Aptos, se trata en las limitaciones.", "",
          "## Resumen", "",
          "- **Seis redes** comparadas con el mismo modelo de la tesis: Polygon, Celo y Arbitrum (medicion de 90 dias) frente a Tempo, Aptos y Canton (muestra reducida de verificacion).",
          "- **Cobertura**: " + "; ".join(f"{r[0]} {r[1] + r[2] + r[3]}/16 con valor" for r in t_filas) + ".",
          "- **Recomendacion por caso** (banda 1): " + "; ".join(f"{CASOS[k].split(' (')[0]}: " + " + ".join(NOMBRE[x] for x in r["bandas"][0]["redes"]) for k, r in resultados.items() if r["bandas"]) + ".",
          "- **Lectura**: la recomendacion es la banda 1; si tiene varias redes, estan empatadas. Las limitaciones que condicionan esta lectura estan en [limitaciones.md](limitaciones.md) y no son un apendice.", "",
          "## Cobertura de metricas por red", "", "Metricas del catalogo del modelo (16) segun su estado.", ""]
    md += tabla_md(["red", "medidas", "parciales", "cota inferior", "no computables", "no aplican"], t_filas)
    md += ["", "## Metricas por red", "",
           "Valores tal como entran al modelo (`ServicioPerfiles`, modo `medicion`). Para T/A/C: A2 = p95/mediana, B3 x 48/18, C3 en %, C1 = C1b (HHI de peso de consenso). `n/d` = sin valor; el estado entre parentesis marca valores parciales o cota inferior.", ""]
    md += tabla_md(cab, tm)
    md += ["", "## Recomendaciones del modelo con las seis redes", "",
           "`modelo.recomendar` con 10 000 replicas, semilla 42 y TRM 4 000, sobre los cuatro casos de referencia de la tesis y las seis redes.", ""] + modelo_md
    md += ["## Benchmark de Tempo, Aptos y Canton con el motor del plan", "",
           "Puntajes del motor `score_engine.py` (pesos y agregacion heredados del estudio de referencia) para los escenarios E1, E2 y E3 del plan. Este motor solo puntua las tres redes del plan; la comparacion de las seis redes es la de la seccion anterior. Un `--` es una red inadmisible por compuerta.", ""]
    md += seccion_tac()
    md += ["", f"El catalogo de `metrics.csv` tiene {n_metricas} filas (16 metricas x 3 redes y E1, con C1 y C1b). Detalle: `resultados/metrics.csv`, `gates.csv`, `scores.csv`, `sensitivity.csv`, `discrimination.csv`, `benchmark_final.csv`.", ""]
    return "\n".join(md), t_filas, victorias


def construir_limitaciones(base, filas, ahora):
    md = ["# Limitaciones", "",
          f"Generado el {ahora:%Y-%m-%d}. Aplican a los resultados de [benchmark.md](benchmark.md) y [pruebas.md](pruebas.md). Un `no_computable` con su razon es un resultado valido; un valor parcial se publica con su advertencia, nunca como un numero limpio.", "",
          "## Estados", "",
          "- **medida**: el valor sale de una consulta reproducible al registro publico de la red.",
          "- **parcial** (`parcialmente_derivada`): hay valor, con un supuesto o una advertencia que no se pudo verificar.",
          "- **cota inferior**: la red no se saturo en la ventana; el valor es un minimo de lo que sostiene.",
          "- **no computable**: no se puede derivar de una consulta reproducible; no se completa con documentacion.",
          "- **no aplica**: la metrica no tiene sentido para esa arquitectura.", "",
          "## Limitaciones que afectan a todas las redes", ""]
    for t, d in TRANSVERSALES:
        md += [f"- **{t}.** {d}"]
    md += ["", "## Por red", ""]
    for r in REDES:
        md += [f"### {NOMBRE[r]}", ""]
        if r in TAC:
            mias = [f for f in filas if f["red"] == r and f["estado"] != "computada"]
            for f in mias:
                v = f"= {_fmt(float(f['valor']))} " if f["valor"] not in ("", None) else ""
                md += [f"- **{f['metrica_id']}** ({f['estado']}) {v}: {f['razon_estado']}"]
            sin = [f for f in filas if f["red"] == r and f["estado"] == "computada" and f["razon_estado"] and not f["razon_estado"].startswith("muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap") and f["metrica_id"] != "E1"]
            for f in sin:
                md += [f"- **{f['metrica_id']}** (medida, con nota): {f['razon_estado']}"]
        else:
            md += [f"- {x}" for x in LIM_PCA[r]]
            md += ["- B3, D2 y D3 provienen solo de la linea base: la metrica en vivo no las reemplaza porque necesita ventanas largas."]
        md.append("")
    md += ["## Por metrica", ""]
    cab = ["metrica"] + [NOMBRE[r] for r in REDES]
    filas_m = []
    for mid, _, _ in METRICAS:
        filas_m.append([f"**{mid}**"] + [_estado(r, mid, base.get(r, {}).get(mid), filas) for r in REDES])
    md += tabla_md(cab, filas_m)
    md += ["", "## Que falta para cerrar los huecos", "",
           "- **aptos.B2**: sondeo en vivo de la finalidad durante 72 h en al menos dos fullnodes (`backend/benchmark/poll_finality.py`); el tiempo de bloque de Aptos (~20 ms) es menor que el viaje HTTP a la API publica, asi que un sondeo HTTP simple no basta.",
           "- **aptos.D2**: fijar por escrito la definicion operativa de referencia apta (A-5) y recolectar transferencias de pago reales; la muestra actual esta dominada por un protocolo de derivados.",
           "- **canton.C1**: no es un hueco de datos; Canton no tiene bloques y C1b es la metrica de concentracion primaria.",
           "- **canton.B3**: usar el techo agregado del sincronizador en lugar de la asignacion gratuita por miembro (`baseRateTrafficLimits`); hasta entonces es una lectura conservadora que no debe citarse como que Canton no puede sostener 48 TPS.",
           "- **Ventana W_H completa**: aumentar `N_BLOCKS_TEMPO`, `N_BLOCKS_APTOS` y `MAX_PAGES` y volver a correr `python backend/benchmark/main.py --collect`.",
           "- **Segundo proveedor por red** para el control de concordancia.",
           "- **Precio de APT**: el oraculo Pyth esta congelado desde 2026-08-26 en 0,55654017 USD/APT y se aplica fijo a toda la muestra (`aptos.A1`, `aptos.A2`); no hay otra fuente verificable.", "",
           "## Banco de usuarios simulados", ""]
    md += [f"- {x}" for x in SIMULACION]
    return "\n".join(md) + "\n"


def generar(res=RES):
    ahora = datetime.now(timezone.utc)
    filas = _csv(res / "metrics.csv")
    base = construir_linea_base(BACKEND / "modelo" / "perfiles.json", res / "metrics.csv")
    resultados = correr_modelo(base)
    bench_md, t_filas, victorias = construir_benchmark(base, filas, resultados, ahora)
    (res / "benchmark.md").write_text(bench_md, encoding="utf-8")
    cuerpo = md_a_html(bench_md).replace("<h2>Resumen</h2>", "<h2>Resumen</h2>" + kpis([("6", "redes comparadas"), ("16", "metricas por red"), (str(len(resultados)), "casos de referencia"),
                                                                                         (str(sum(r[1] + r[2] + r[3] for r in t_filas)), "valores disponibles de 96")]), 1)
    (res / "benchmark.html").write_text(pagina("Resultados del benchmark", cuerpo.replace("limitaciones.md", "limitaciones.md")), encoding="utf-8")
    (res / "limitaciones.md").write_text(construir_limitaciones(base, filas, ahora), encoding="utf-8")
    return [res / "benchmark.md", res / "benchmark.html", res / "limitaciones.md"]


if __name__ == "__main__":
    for ruta in generar():
        print(f"escrito {ruta}")
