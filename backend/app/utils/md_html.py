"""Conversion de Markdown simple (titulos, tablas, listas, parrafos) a una pagina HTML autocontenida con tema claro/oscuro, usada por los informes de resultados/."""

import html
import re

CSS = """
:root{--bg:#fff;--fg:#1c2430;--mut:#5c6877;--line:#dfe4ea;--acc:#1f5fbf;--card:#f6f8fb;--warn:#a15c00}
@media (prefers-color-scheme:dark){:root{--bg:#10151c;--fg:#e4e9f0;--mut:#9aa6b5;--line:#27313d;--acc:#6ea8ff;--card:#171e27;--warn:#f0b050}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.8rem}h2{margin-top:2.2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}
h3{margin-top:1.6rem}table{border-collapse:collapse;width:100%;margin:.8rem 0;font-size:.85rem;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}th{background:var(--card)}
li.alerta{color:var(--warn)}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:1rem 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}.kpi b{display:block;font-size:1.4rem;color:var(--acc)}
.kpi span{color:var(--mut);font-size:.8rem}svg{max-width:100%;height:auto}.mut{color:var(--mut)}code{background:var(--card);padding:1px 4px;border-radius:4px}
"""


def inline(texto):
    t = html.escape(texto)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)


def md_a_html(md):
    salida, i, lineas = [], 0, md.split("\n")
    en_lista = False
    while i < len(lineas):
        ln = lineas[i]
        if ln.startswith("|"):
            if en_lista:
                salida.append("</ul>")
                en_lista = False
            bloque = []
            while i < len(lineas) and lineas[i].startswith("|"):
                bloque.append(lineas[i])
                i += 1
            celdas = [[c.strip() for c in b.strip().strip("|").split("|")] for b in bloque if not re.fullmatch(r"\|[-| ]+\|", b)]
            salida.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in celdas[0]) + "</tr></thead><tbody>")
            for fila in celdas[1:]:
                salida.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in fila) + "</tr>")
            salida.append("</tbody></table>")
            continue
        m = re.match(r"^(#{1,4}) (.*)", ln)
        if m:
            if en_lista:
                salida.append("</ul>")
                en_lista = False
            n = len(m.group(1))
            salida.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif ln.startswith("- "):
            if not en_lista:
                salida.append("<ul>")
                en_lista = True
            clase = ' class="alerta"' if ln.startswith("- ALERTA") else ""
            salida.append(f"<li{clase}>{inline(ln[2:])}</li>")
        elif ln.strip() == "---":
            salida.append("<hr>")
        elif ln.strip():
            if en_lista:
                salida.append("</ul>")
                en_lista = False
            salida.append(f"<p>{inline(ln)}</p>")
        i += 1
    if en_lista:
        salida.append("</ul>")
    return "\n".join(salida)


def kpis(datos):
    return '<div class="kpis">' + "".join(f'<div class="kpi"><b>{v}</b><span>{t}</span></div>' for v, t in datos) + "</div>"


def pagina(titulo, cuerpo):
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body><main>{cuerpo}</main></body></html>")
