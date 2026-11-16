"""Publica los resultados del banco de usuarios simulados como resultados/pruebas.md y resultados/pruebas.html a partir de los archivos de resultados/pruebas/datos/ (informe.md, serie_vivo.csv, manifiesto.json); no vuelve a correr el modelo."""

import csv
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from app.utils.md_html import kpis, md_a_html, pagina

RAIZ = Path(__file__).resolve().parents[2] / "resultados"
DATOS = RAIZ / "pruebas" / "datos"

def _leer_csv(nombre):
    with open(DATOS / nombre, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fecha(texto):
    return datetime.fromisoformat(texto)


def _tabla(cabecera, filas):
    return ["| " + " | ".join(cabecera) + " |", "|" + "---|" * len(cabecera)] + ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]


def resumen_p7(serie):
    por_ciclo = defaultdict(lambda: {"cambios": 0, "distintos": 0, "usuarios": 0, "vivas": 0, "esperadas": 0, "valido": True, "ts": None, "causa": Counter()})
    por_perfil = defaultdict(lambda: {"cambios": 0, "usuarios": 0, "distintos": 0})
    for f in serie:
        c = por_ciclo[int(f["ciclo"])]
        c["cambios"] += int(f["cambios"])
        c["distintos"] += int(f["distintos_de_base"])
        c["usuarios"] += int(f["usuarios"])
        c["vivas"] = int(f["metricas_vivas"])
        c["esperadas"] = int(f["metricas_esperadas"])
        c["valido"] = f["valido"] == "True"
        c["ts"] = f["ts"]
        if f["causa_probable"]:
            c["causa"][f["causa_probable"]] += 1
        p = por_perfil[int(f["perfil"])]
        p["cambios"] += int(f["cambios"])
        p["usuarios"] += int(f["usuarios"])
        p["distintos"] += int(f["distintos_de_base"])
    ids = sorted(por_ciclo)
    t0, t1 = _fecha(por_ciclo[ids[0]]["ts"]), _fecha(por_ciclo[ids[-1]]["ts"])
    causas = Counter()
    for c in por_ciclo.values():
        causas.update(c["causa"])
    return {"ciclos": len(ids), "validos": sum(1 for c in por_ciclo.values() if c["valido"]), "inicio": t0, "fin": t1, "dias": (t1 - t0).total_seconds() / 86400,
            "con_cambios": sum(1 for c in por_ciclo.values() if c["cambios"]), "cambios_total": sum(c["cambios"] for c in por_ciclo.values()),
            "cambios_media": mean(c["cambios"] for c in por_ciclo.values()), "cambios_max": max(c["cambios"] for c in por_ciclo.values()),
            "distintos_mediana": median(c["distintos"] for c in por_ciclo.values()), "usuarios_ciclo": por_ciclo[ids[0]]["usuarios"],
            "vivas_min": min(c["vivas"] for c in por_ciclo.values()), "vivas_max": max(c["vivas"] for c in por_ciclo.values()), "esperadas": por_ciclo[ids[0]]["esperadas"],
            "causas": causas.most_common(10), "por_perfil": por_perfil, "ciclos_serie": [(i, por_ciclo[i]["cambios"], por_ciclo[i]["distintos"]) for i in ids]}


def grafico_serie(puntos, indice, titulo, ancho=900, alto=200):
    xs = [p[0] for p in puntos]
    ys = [p[indice] for p in puntos]
    if not ys:
        return ""
    ymax = max(ys) or 1
    x0, x1 = min(xs), max(xs)
    pts = " ".join(f"{40 + (x - x0) / max(x1 - x0, 1) * (ancho - 50):.1f},{alto - 25 - y / ymax * (alto - 45):.1f}" for x, y in zip(xs, ys))
    return (f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="{html.escape(titulo)}"><text x="40" y="14" fill="currentColor" font-size="12">{html.escape(titulo)}</text>'
            f'<line x1="40" y1="{alto - 25}" x2="{ancho - 10}" y2="{alto - 25}" stroke="currentColor" opacity=".3"/>'
            f'<text x="4" y="30" fill="currentColor" font-size="11">{ymax}</text><text x="4" y="{alto - 25}" fill="currentColor" font-size="11">0</text>'
            f'<text x="40" y="{alto - 8}" fill="currentColor" font-size="11">ciclo {x0}</text><text x="{ancho - 70}" y="{alto - 8}" fill="currentColor" font-size="11">ciclo {x1}</text>'
            f'<polyline points="{pts}" fill="none" stroke="var(--acc)" stroke-width="1.2"/></svg>')


def construir_md(manifiesto, informe, r):
    cfg = manifiesto["config"]
    nombres = {int(f["perfil"]): f["nombre"] for f in _leer_csv("personas.csv")}
    lineas = ["# Resultados de las pruebas del banco de usuarios simulados", "",
              "Banco de usuarios simulados (`backend/simulacion/`): 12 perfiles que evaluan, con `modelo.recomendar` sin modificar, si la red recomendada cumple su necesidad. "
              "Cada resultado se lee por perfil, nunca como porcentaje de la poblacion; los rangos de los perfiles 4 a 12 son supuestos de diseno. Un mal ajuste es evidencia para discutir, no un defecto demostrado.", "",
              "## Resumen", "",
              f"- **Lote P1-P6** (corrida `{manifiesto['corrida']}`): pruebas {', '.join(cfg['pruebas'])}, fuente `{cfg['fuente']}` (linea base y vivo), semilla {cfg['semilla']}, {cfg['replicas']} replicas, tope de {cfg['tope']} usuarios por perfil, "
              f"panel de {cfg['panel_por_perfil']} por perfil, convergencia en {cfg['niveles_replicas']} replicas, TRM {manifiesto['trm']:.0f} COP/USD.",
              f"- **Panel continuo P7**: {r['ciclos']} ciclos de 15 min ({r['validos']} validos) entre {r['inicio']:%Y-%m-%d %H:%M} y {r['fin']:%Y-%m-%d %H:%M} UTC, es decir {r['dias']:.1f} dias.",
              f"- Cada ciclo evalua {r['usuarios_ciclo']} usuarios (10 por perfil) con {r['vivas_min']}-{r['vivas_max']} de {r['esperadas']} metricas vivas esperadas.",
              f"- Commit del codigo evaluado: `{manifiesto['commit'][:12]}`; version de perfil base `{manifiesto['version_perfil']['base']}`.", "",
              "## P7 en cifras", "",
              f"- Ciclos con al menos un cambio de banda 1 respecto al ciclo anterior: {r['con_cambios']} de {r['ciclos']} ({r['con_cambios'] / r['ciclos']:.0%}).",
              f"- Cambios de banda 1 entre ciclos consecutivos: {r['cambios_total']} en total; media {r['cambios_media']:.2f} por ciclo, maximo {r['cambios_max']}.",
              f"- Usuarios con banda 1 distinta de la de la linea base: mediana {r['distintos_mediana']:.0f} de {r['usuarios_ciclo']} por ciclo.",
              "- Causa probable (atribucion indicativa, metrica que mas cambia): " + ", ".join(f"`{c}` ({n})" for c, n in r["causas"]) + ".", "",
              "### P7 por perfil", ""]
    filas = []
    for pid in sorted(r["por_perfil"]):
        p = r["por_perfil"][pid]
        filas.append((pid, nombres.get(pid, ""), p["cambios"], f"{p['cambios'] / r['ciclos']:.3f}", f"{p['distintos'] / p['usuarios']:.2f}"))
    lineas += _tabla(["perfil", "nombre", "cambios de banda 1", "cambios por ciclo", "cuota distinta de la base"], filas)
    cuerpo = re.sub(r"^# .*\n", "", informe, count=1)
    cuerpo = re.sub(r"^(#+) ", lambda m: "#" + m.group(1) + " ", cuerpo, flags=re.M)
    cuerpo = re.sub(r"## P7\. Panel continuo.*", "", cuerpo, flags=re.S).rstrip()
    lineas += ["", "---", "", "# Detalle por prueba", "", cuerpo, ""]
    lineas += ["## Archivos de datos", "",
               "Todo lo anterior sale de `resultados/pruebas/datos/`: `informe.md`, `personas.csv`, `contrafactuales.csv`, `sensibilidad.csv`, `convergencia.csv`, `serie_vivo.csv` (una fila por ciclo y perfil), `manifiesto.json`, `resultados.json`.", ""]
    return "\n".join(lineas)


def kpis_pruebas(r, cfg):
    return kpis([(f"{r['ciclos']}", "ciclos del panel continuo"), (f"{r['dias']:.1f} d", "duracion del panel"), (f"{r['ciclos'] * r['usuarios_ciclo']:,}".replace(",", " "), "evaluaciones del panel"),
                 ("7 840", "evaluaciones del lote P1-P6"), (f"{cfg['replicas']:,}".replace(",", " "), "replicas Monte Carlo"), (f"{r['con_cambios'] / r['ciclos']:.0%}", "ciclos con cambio de banda 1")])


def construir_html(md, r, cfg):
    cuerpo = md_a_html(md)
    cuerpo = cuerpo.replace("<h2>Resumen</h2>", "<h2>Resumen</h2>" + kpis_pruebas(r, cfg), 1)
    graficos = grafico_serie(r["ciclos_serie"], 1, "Cambios de banda 1 por ciclo (P7, 120 usuarios)") + grafico_serie(r["ciclos_serie"], 2, "Usuarios con banda 1 distinta de la linea base por ciclo")
    cuerpo = cuerpo.replace("<h3>P7 por perfil</h3>", graficos + "<h3>P7 por perfil</h3>", 1)
    return pagina("Resultados de las pruebas", cuerpo)


def publicar(raiz=RAIZ):
    manifiesto = json.loads((DATOS / "manifiesto.json").read_text(encoding="utf-8"))
    informe = (DATOS / "informe.md").read_text(encoding="utf-8")
    r = resumen_p7(_leer_csv("serie_vivo.csv"))
    md = construir_md(manifiesto, informe, r)
    (raiz / "pruebas.md").write_text(md, encoding="utf-8")
    (raiz / "pruebas.html").write_text(construir_html(md, r, manifiesto["config"]), encoding="utf-8")
    return raiz / "pruebas.md", raiz / "pruebas.html"
