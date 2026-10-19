# -*- coding: utf-8 -*-
"""Genera docs/benchmark-medible-tempo-aptos-canton.pdf, con la misma
estructura de 12 secciones (+referencias) que docs/benchmark-medible-
polygon-celo-arbitrum.pdf de Dilan, pero para Tempo/Aptos/Canton, y con
resultados reales medidos (Sec.11-13), no solo especificacion.
"""
import csv
import json
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, ListFlowable, ListItem,
)
from reportlab.pdfgen import canvas as canvas_mod

RES = "resultados"
OUT = "docs/benchmark-medible-tempo-aptos-canton.pdf"

NAVY = colors.HexColor("#1B2A45")
NAVY_LIGHT = colors.HexColor("#EEF1F6")
GREEN_BOX = colors.HexColor("#EAF3EA")
GREEN_BORDER = colors.HexColor("#6B9B6F")
AMBER_BOX = colors.HexColor("#FDF3DC")
AMBER_BORDER = colors.HexColor("#C9973A")
GREY_TEXT = colors.HexColor("#444444")
ROW_ALT = colors.HexColor("#F5F6F8")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleMain", fontName="Helvetica-Bold", fontSize=18, leading=22,
                           alignment=TA_CENTER, spaceAfter=6, textColor=NAVY))
styles.add(ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=12, leading=15,
                           alignment=TA_CENTER, textColor=GREY_TEXT, spaceAfter=4))
styles.add(ParagraphStyle("SectionH", fontName="Helvetica-Bold", fontSize=13.5, leading=16,
                           spaceBefore=16, spaceAfter=8, textColor=NAVY))
styles.add(ParagraphStyle("SubH", fontName="Helvetica-Bold", fontSize=11, leading=14,
                           spaceBefore=10, spaceAfter=5, textColor=NAVY))
styles.add(ParagraphStyle("Body", fontName="Times-Roman", fontSize=9.6, leading=13.2,
                           alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle("BodyBold", parent=styles["Body"], fontName="Times-Bold"))
styles.add(ParagraphStyle("Small", fontName="Times-Roman", fontSize=8, leading=10.5,
                           textColor=GREY_TEXT))
styles.add(ParagraphStyle("Cell", fontName="Times-Roman", fontSize=8.3, leading=10.6))
styles.add(ParagraphStyle("CellHead", fontName="Helvetica-Bold", fontSize=8.3, leading=10.6,
                           textColor=colors.white))
styles.add(ParagraphStyle("Mono", fontName="Courier", fontSize=8, leading=10.5))


def P(text, style="Body"):
    return Paragraph(text, styles[style])


def C(text):
    return Paragraph(text, styles["Cell"])


def H(text):
    return Paragraph(text, styles["CellHead"])


def dark_table(header, rows, col_widths=None, note=None):
    data = [[H(h) for h in header]] + [[C(str(c)) for c in r] for r in rows]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B9C2CF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    t.setStyle(TableStyle(style))
    out = [t]
    if note:
        out += [Spacer(1, 3), P(note, "Small")]
    return out


def callout(text, kind="info"):
    box_color = GREEN_BOX if kind == "info" else AMBER_BOX
    border = GREEN_BORDER if kind == "info" else AMBER_BORDER
    t = Table([[P(text, "Body")]], colWidths=[16.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), box_color),
        ("BOX", (0, 0), (-1, -1), 0.75, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def bullets(items):
    return ListFlowable(
        [ListItem(P(it, "Body"), leftIndent=6) for it in items],
        bulletType="bullet", start="•", leftIndent=14,
    )


# ---------------------------------------------------------------------------
# carga de datos reales
# ---------------------------------------------------------------------------
def load_csv(name):
    try:
        return list(csv.DictReader(open(f"{RES}/{name}", encoding="utf-8")))
    except FileNotFoundError:
        return []


metrics_rows = load_csv("metrics.csv")
gates_rows = load_csv("gates.csv")
scores_rows = load_csv("scores.csv")
disc_rows = load_csv("discrimination.csv")
try:
    manifest = json.load(open(f"{RES}/run_manifest.json"))
except FileNotFoundError:
    manifest = {}

ESTADO_LABEL = {
    "computada": "computada",
    "parcialmente_derivada": "parcial",
    "no_computable": "no computable",
    "degenerada": "degenerada",
}


def fmt_val(v):
    if v in (None, ""):
        return "—"
    try:
        f = float(v)
        if abs(f) >= 1000 or (abs(f) < 0.001 and f != 0):
            return f"{f:.4g}"
        return f"{f:.4f}".rstrip("0").rstrip(".")
    except ValueError:
        return v


def metrics_table_for(red):
    rows = [r for r in metrics_rows if r["red"] == red]
    rows.sort(key=lambda r: r["metrica_id"])
    out = []
    for r in rows:
        out.append([
            r["metrica_id"],
            r["activo"] if r["activo"] not in ("n/a", "") else "—",
            fmt_val(r["valor"]),
            r["unidad"],
            r["n"] or "—",
            ESTADO_LABEL.get(r["estado"], r["estado"]),
        ])
    return out


# ---------------------------------------------------------------------------
# construccion del documento
# ---------------------------------------------------------------------------
story = []

# ---- portada ----
story.append(Spacer(1, 4 * cm))
story.append(P("Benchmark medible de redes de pagos en Colombia", "TitleMain"))
story.append(P("Tempo &middot; Aptos &middot; Canton Network", "Subtitle"))
story.append(Spacer(1, 6))
story.append(P("Dieciseis metricas derivadas del registro publico de cada red", "Subtitle"))
story.append(Spacer(1, 40))
story.append(P(f"Version 1.0 &mdash; {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", "Subtitle"))
story.append(P("Adaptacion del benchmark medible de redes EVM (Polygon PoS / Celo / Arbitrum One)", "Subtitle"))
story.append(PageBreak())

# ============================= 1 =============================
story.append(P("1&nbsp;&nbsp;Punto de partida: que decide el benchmark", "SectionH"))
story.append(P(
    "Antes de definir que se mide conviene fijar para que sirve la medicion, porque de eso depende "
    "todo lo demas.", "Body"))
story.append(callout(
    "Para cada escenario transaccional relevante en Colombia, &iquest;que red es admisible como destino "
    "de liquidacion, como se ordenan las admisibles entre si, y que operaciones de pago se usan "
    "efectivamente en cada una?", "info"))
story.append(P(
    "De esa pregunta salen tres salidas: el conjunto admisible por escenario, el orden de preferencia "
    "con su analisis de sensibilidad, y el perfil operativo de cada red. Este documento reproduce la "
    "estructura del benchmark original sobre Polygon PoS, Celo y Arbitrum One &mdash;tres redes EVM ancladas "
    "en Ethereum&mdash; pero aplicada a tres redes que <b>no comparten esa arquitectura entre si</b>: "
    "Tempo (L1 EVM permisionada de pagos), Aptos (L1 Move de proposito general) y Canton Network "
    "(una plataforma de registros distribuidos sin cadena de bloques global). Esa diferencia obliga a "
    "una serie de enmiendas metodologicas explicitas, documentadas seccion por seccion.", "Body"))

story.append(P("2&nbsp;&nbsp;La restriccion que ordena el diseno", "SectionH"))
story.append(P("2.1&nbsp;&nbsp;Solo se mide lo que el registro publico muestra", "SubH"))
story.append(P(
    "Se hereda sin relajar la regla del benchmark original: <b>ninguna metrica se puntua si su valor "
    "no puede derivarse de datos del propio registro de la red mediante consultas reproducibles</b>. "
    "Nada se toma de documentacion oficial, agregadores comerciales ni declaraciones de los equipos.", "Body"))
story.append(P(
    "La unica enmienda de fondo es terminologica pero no cosmetica: el original dice <i>datos en "
    "cadena</i>; Canton no tiene cadena de bloques en el sentido de Tempo o Aptos. La regla se "
    "reformula sin aflojarla:", "Body"))
story.append(callout(
    "Una metrica es admisible si su valor puede obtenerse consultando el registro que la propia red "
    "publica para terceros, mediante una consulta que un tercero puede reejecutar y cuyo resultado no "
    "depende de ser contraparte de las transacciones observadas.", "info"))
story.append(P("2.2&nbsp;&nbsp;Fuentes admisibles por red", "SubH"))
story.extend(dark_table(
    ["Red", "Registro admisible", "Registro NO admisible"],
    [
        ["Tempo", "JSON-RPC de nodo Tempo (eth_*), estado de precompilados", "Explorador web, documentacion"],
        ["Aptos", "Fullnode REST API /v1/*, Indexer GraphQL, recursos Move de 0x1", "Dashboards, agregadores"],
        ["Canton", "Scan API de Super Validadores (/v2/updates, /v0/events, /v0/state/acs)", "Ledger API de un participante propio"],
    ],
    col_widths=[2.3 * cm, 7.2 * cm, 7 * cm],
))
story.append(Spacer(1, 6))
story.append(callout(
    "<b>Hallazgo de esta ejecucion, no anticipado por el diseno:</b> los Scan de Super Validador "
    "individuales de Canton (sync.global, digitalasset.com, cumberland.io, fivenorth.io) "
    "<b>rechazan el acceso publico directo</b> (403 Forbidden / RBAC access denied). El acceso de "
    "terceros ocurre en la practica a traves de espejos operados por proveedores independientes "
    "(<i>api.cantonnodes.com</i>, <i>ccscan.xyz</i>), de forma analoga a como Infura o Alchemy median "
    "el acceso publico a Ethereum. Esto se documenta como limitacion estructural, no se disimula.",
    "warn"))

story.append(PageBreak())

# ============================= 3 =============================
story.append(P("3&nbsp;&nbsp;Las tres redes evaluadas", "SectionH"))
story.append(P("3.1&nbsp;&nbsp;Criterios de inclusion", "SubH"))
story.append(P(
    "A diferencia del benchmark original, donde las tres redes comparten compatibilidad EVM y ancla "
    "verificable en Ethereum, aqui el criterio es el opuesto: se eligieron deliberadamente tres "
    "<b>arquitecturas de registro distintas</b> para poner a prueba si el instrumento de medicion "
    "sobrevive al cambio de arquitectura.", "Body"))
story.append(bullets([
    "<b>Historia operativa suficiente.</b> Tempo mainnet arranco el 16 de enero de 2026 (confirmado "
    "por la marca de tiempo real del bloque 1, corrigiendo el 18 de marzo que figuraba como supuesto "
    "antes de verificarlo en vivo); Aptos mainnet opera desde octubre de 2022; el Global Synchronizer "
    "de Canton, desde junio de 2024 (confirmado por el evento DsoBootstrap mas antiguo recuperable).",
    "<b>Registro publico consultable por terceros</b>, con distinto grado de friccion segun la red "
    "(ver 2.2).",
    "<b>Ninguna aloja una stablecoin del peso colombiano</b>, a diferencia de Polygon (COPW) y Celo "
    "(COPM) en el benchmark original. El activo de pago se elige por red segun lo que efectivamente "
    "circula.",
]))
story.append(P("3.2&nbsp;&nbsp;Perfil de cada red", "SubH"))
story.extend(dark_table(
    ["Atributo", "Tempo", "Aptos", "Canton"],
    [
        ["Arquitectura", "L1 EVM permisionada; BFT propio (Simplex/Commonware)",
         "L1 de proposito general; VM Move; AptosBFT",
         "Sin cadena global; sub-ledgers sincronizados por un Global Synchronizer"],
        ["Finalidad", "Deterministica, sub-segundo (mediana medida 0.63s, n=53)",
         "Deterministica, sub-segundo (no medible con sondeo HTTP simple, ver 11)",
         "Verdict del mediador; mediana medida 0.63-1.06s"],
        ["Produccion", "Proponente por VRF; 15 validadores activos confirmados",
         "Proponente ponderado por stake; 84 validadores activos",
         "No hay bloques; sequencers de cada SV ordenan su synchronizer"],
        ["Activo de comision", "TIP-20 en USD; sin token nativo de gas", "APT (nativo)",
         "Trafico tarifado en USD, liquidado en Canton Coin"],
        ["Gobernanza", "TIPs, activados por hardfork", "AIPs + publicacion de modulos Move",
         "CIPs + votos de gobernanza del DSO"],
    ],
    col_widths=[2.6 * cm, 4.8 * cm, 4.6 * cm, 4.6 * cm],
    note="Ninguno de estos datos entra al puntaje: todo lo puntuado se mide, conforme a 2.1.",
))

story.append(PageBreak())

# ============================= 4 =============================
story.append(P("4&nbsp;&nbsp;La materia prima: que expone cada registro", "SectionH"))
story.extend(dark_table(
    ["Necesidad", "Tempo", "Aptos", "Canton"],
    [
        ["Cadencia / timestamp", "eth_getBlockByNumber.timestamp", "block_timestamp (us)", "record_time del update"],
        ["Productor / orden", "consensusContext.proposer (cabecera)", "block_metadata_transaction.proposer",
         "No existe; solo sequencers via /v0/dso-sequencers"],
        ["Peso de consenso", "ValidatorConfigV2.getActiveValidators() (sin campo de peso -> igualitario)",
         "0x1::stake::ValidatorSet.voting_power", "sv_node_states en /v0/dso"],
        ["Costo de tx", "gasUsed x effectiveGasPrice, feeToken en el recibo",
         "gas_used x gas_unit_price (octas) + oraculo", "traffic_summary.total_traffic_cost x trafficPrice (USD/MB)"],
        ["Exito / fallo", "status del recibo", "success / vm_status", "verdict_result (ACCEPTED/REJECTED)"],
        ["Irreversibilidad", "Sondeo en vivo del tag 'finalized'", "Sondeo en vivo de altura comprometida",
         "finalization_time del verdict (reconstruible historicamente)"],
    ],
    col_widths=[3 * cm, 5.2 * cm, 4.5 * cm, 4.5 * cm],
))
story.append(Spacer(1, 6))
story.append(P(
    "Las tres redes exponen conteo, tiempo y resultado de todas sus transacciones. Solo dos exponen "
    "monto y contrapartes de todas: en Canton eso depende del activo (Canton Coin es visible al DSO; "
    "USDCx bajo el estandar de token, no). Esta asimetria se convierte en la compuerta G2' y en "
    "la metrica E1 (secciones 8 y 9).", "Body"))

# ============================= 5 =============================
story.append(P("5&nbsp;&nbsp;De la irreversibilidad ancorada a la irreversibilidad observable", "SectionH"))
story.append(P(
    "El benchmark original define tau<sub>A</sub> como el instante en que el bloque queda "
    "comprometido en un contrato de Ethereum. Ninguna de las tres redes de este estudio publica ese "
    "compromiso: aplicar tau<sub>A</sub> literalmente declararia a las tres inadmisibles en todos "
    "los escenarios, lo cual seria un error de portabilidad, no un resultado.", "Body"))
story.append(callout(
    "<b>Instante de irreversibilidad observable tau<sub>F</sub>.</b> Primer momento en que un "
    "tercero, consultando unicamente el registro publico de la red, puede verificar que la "
    "transferencia ya no puede revertirse. Se mide tau<sub>F</sub> - tau<sub>1</sub>, donde "
    "tau<sub>1</sub> es la marca de tiempo del bloque o update que la contiene.", "info"))
story.append(P(
    "En Tempo y Aptos, tau<sub>F</sub> no es reconstruible desde el historico: solo se puede medir "
    "sondeando en vivo. En Canton si es reconstruible, porque el verdict del mediador trae su propio "
    "finalization_time.", "Body"))
story.append(callout(
    "<b>Resultado obtenido (n bajo, sondeo de 30s, no las 72h que exige la ventana completa):</b> "
    "tau<sub>F</sub> - tau<sub>1</sub> en Tempo tiene mediana 0.63s (n=53). En Aptos, un "
    "sondeo HTTP secuencial simple no pudo resolverlo: el tiempo de bloque de Aptos (~20ms) es mas "
    "rapido que el round-trip hacia la API publica, y los deltas medidos salieron con signo mezclado "
    "(ruido, no senal). Esto confirma la advertencia del plan: el eje de irreversibilidad, sub-segundo "
    "en las redes que si se pudieron medir, deja de discriminar entre ellas tal como discriminaba "
    "entre Polygon/Celo/Arbitrum en el benchmark original.", "warn"))

story.append(PageBreak())

# ============================= 6 =============================
story.append(P("6&nbsp;&nbsp;Del mercado colombiano a los umbrales", "SectionH"))
story.append(P(
    "Heredado sin cambios del benchmark original. Fuente: documento tecnico del Banco de la Republica "
    "sobre Bre-B, febrero de 2026.", "Body"))
story.extend(dark_table(
    ["Hecho del mercado", "Valor", "Umbral que fija"],
    [
        ["Tiempo maximo de transferencia inmediata", "20 s", "Umbral inaceptable de B1 y compuerta G1"],
        ["Ticket promedio observado", "COP 159.456", "Denominador de A1"],
        ["Maximo diario observado (31-ene-2026)", "5,2 millones de operaciones", "Requisito de capacidad (ec. 1)"],
        ["Operaciones desde billeteras de bajo monto", "50%", "Justifica el peso de D1"],
        ["Estandar de mensajeria nacional", "ISO 20022", "Justifica D2"],
        ["Remesas recibidas en 2025", "USD 13.098 millones", "Dimensiona el escenario E1"],
        ["Meta internacional de costo de remesas", "&lt; 3%", "Umbral de A1 en remesas"],
    ],
    col_widths=[6.5 * cm, 4.5 * cm, 5.2 * cm],
))
story.append(Spacer(1, 6))
story.append(P(
    "Requisito de capacidad: TPS<sub>req</sub>(rho) = rho &middot; phi &middot; N<sub>max</sub> / "
    "86.400. Con phi=8: <b>48 TPS</b> para rho=10% del volumen nacional (referencia usada en B3/G4).",
    "Body"))

story.append(P("7&nbsp;&nbsp;Escenarios", "SectionH"))
story.extend(dark_table(
    ["Atributo", "E1 &mdash; Remesas", "E2 &mdash; Comercio domestico", "E3 &mdash; Alto valor"],
    [
        ["Ticket de referencia", "USD 200&ndash;500", "COP 15.000 a 159.456", "&gt; COP 100 millones"],
        ["Restriccion dominante", "Costo", "Latencia de inclusion", "Irreversibilidad y concentracion"],
        ["Tolerancia a latencia", "Alta: horas", "Baja: segundos", "Media: minutos"],
        ["Compuertas aplicables", "G2', G3", "G1, G2', G3, G4", "G2', G3, G4"],
    ],
    col_widths=[3.2 * cm, 4.3 * cm, 4.3 * cm, 4.4 * cm],
))

story.append(PageBreak())

# ============================= 8 =============================
story.append(P("8&nbsp;&nbsp;Catalogo de metricas", "SectionH"))
story.append(P(
    "Dieciseis metricas en cuatro bloques (catorce heredadas del original, menos A4 &mdash;el costo de "
    "anclaje amortizado, sin sentido sin ancla&mdash;, mas C1b y la metrica transversal E1).", "Body"))

story.append(P("8.1&nbsp;&nbsp;Bloque A &mdash; Costo", "SubH"))
story.extend(dark_table(
    ["ID", "Metrica", "t", "w"],
    [
        ["A1", "Costo mediano por transferencia, fraccion del ticket", "0,1%", "1,0%"],
        ["A2", "Dispersion del costo (p95/mediana)", "1,5", "10"],
        ["A3", "Elasticidad del costo a la ocupacion (pendiente log-lineal)", "0,2", "2,0"],
    ], col_widths=[1.3 * cm, 10.5 * cm, 2 * cm, 2 * cm]))

story.append(P("8.2&nbsp;&nbsp;Bloque B &mdash; Tiempo y caudal", "SubH"))
story.extend(dark_table(
    ["ID", "Metrica", "t", "w"],
    [
        ["B1", "Latencia de inclusion, p95", "5 s", "20 s"],
        ["B2", "tau<sub>F</sub> - tau<sub>1</sub>, mediana", "60 s", "604.800 s"],
        ["B3", "Margen de capacidad H_cfg (sobre 48 TPS)", "5", "1"],
    ], col_widths=[1.3 * cm, 10.5 * cm, 2 * cm, 2 * cm]))

story.append(P("8.3&nbsp;&nbsp;Bloque C &mdash; Concentracion y continuidad", "SubH"))
story.extend(dark_table(
    ["ID", "Metrica", "t", "w"],
    [
        ["C1b", "Herfindahl sobre peso de consenso (primaria)", "0,10", "1,00"],
        ["C1", "Herfindahl sobre produccion de bloques (secundaria)", "0,10", "1,00"],
        ["C2", "N&uacute;mero de operadores que concentran &gt;50%", "15", "1"],
        ["C3", "Disponibilidad (numero de nueves)", "99,999%", "99,9%"],
        ["C4", "Tasa de fallo", "0,1%", "5,0%"],
        ["C5", "Cambios de implementacion en la ruta de pago", "0", "5"],
    ], col_widths=[1.3 * cm, 10.5 * cm, 2 * cm, 2 * cm]))

story.append(P("8.4&nbsp;&nbsp;Bloque D &mdash; Primitivas observadas en uso", "SubH"))
story.extend(dark_table(
    ["ID", "Metrica", "t", "w"],
    [
        ["D1", "Independencia del token nativo / patrocinio", "50%", "1%"],
        ["D2", "Referencia de conciliacion", "20%", "0,1%"],
        ["D3", "Agregacion y atomicidad", "10%", "0,1%"],
    ], col_widths=[1.3 * cm, 10.5 * cm, 2 * cm, 2 * cm]))

story.append(P("8.5&nbsp;&nbsp;Metrica transversal", "SubH"))
story.append(P(
    "<b>E1</b> &mdash; Proporcion de transferencias del activo de pago cuyo monto, contrapartes y "
    "resultado son verificables por un tercero no contraparte. No se puntua directamente: opera como "
    "compuerta G2'. Es la diferencia arquitectonica mas importante entre Canton y las otras dos.",
    "Body"))

story.append(PageBreak())

# ============================= 9 =============================
story.append(P("9&nbsp;&nbsp;De mediciones a puntajes", "SectionH"))
story.append(P("9.1&nbsp;&nbsp;Normalizacion (heredada sin cambios)", "SubH"))
story.append(P(
    "menor es mejor: s<sub>i</sub> = clip[(ln w - ln x)/(ln w - ln t), 0, 1] &nbsp;&nbsp; "
    "mayor es mejor: s<sub>i</sub> = clip[(ln x - ln w)/(ln t - ln w), 0, 1]", "Body"))
story.append(P(
    "Para C3 se transforma primero al numero de nueves. Para C5 (t=0, logaritmo indefinido) se usa "
    "clip lineal como excepcion declarada, no prevista explicitamente en el original.", "Body"))
story.append(P("9.2&nbsp;&nbsp;Pesos entre bloques (heredados, A redistribuido tras eliminar A4)", "SubH"))
story.extend(dark_table(
    ["Bloque", "E1 Remesas", "E2 Comercio", "E3 Alto valor"],
    [
        ["A Costo", "0,45", "0,35", "0,10"],
        ["B Tiempo y caudal", "0,15", "0,35", "0,30"],
        ["C Concentracion", "0,15", "0,15", "0,40"],
        ["D Primitivas", "0,25", "0,15", "0,20"],
    ], col_widths=[4.5 * cm, 4 * cm, 4 * cm, 4 * cm]))
story.append(Spacer(1, 6))
story.append(P(
    "Agregacion: media aritmetica ponderada dentro de cada bloque; media geometrica ponderada entre "
    "bloques con piso epsilon=0,05. <b>Cuando un bloque tiene metricas no computables, el peso se "
    "renormaliza sobre las metricas si disponibles dentro de ese bloque</b> &mdash;una necesidad "
    "practica de esta ejecucion parcial, no prevista en el documento original, y declarada explicitamente "
    "en cada fila de sensitivity.csv donde ocurre.", "Body"))

# ============================= 10 =============================
story.append(P("10&nbsp;&nbsp;Compuertas", "SectionH"))
story.extend(dark_table(
    ["ID", "Condicion medida", "Escenarios"],
    [
        ["G1", "B1 no superior a 20 s", "E2"],
        ["G2'", "E1 (observabilidad) = 1 y tau<sub>F</sub> computable", "Todos"],
        ["G3", "D2 mayor que cero", "Todos"],
        ["G4", "B3 (H_cfg) no inferior a 1", "E2, E3"],
    ], col_widths=[1.6 * cm, 10.5 * cm, 3.7 * cm]))
story.append(Spacer(1, 6))
story.append(P(
    "G2' sustituye a la G2 original (“existe evento de anclaje observable en Ethereum”). "
    "Es la compuerta que produce el hallazgo mas fuerte de este estudio: Canton pasa G2' con "
    "Canton Coin y falla con USDCx (ver 11 y 13).", "Body"))

story.append(PageBreak())

# ============================= 11 =============================
story.append(P("11&nbsp;&nbsp;El sistema de recoleccion", "SectionH"))
story.extend(dark_table(
    ["#", "Modulo", "Metricas que alimenta"],
    [
        ["1", "Lector de bloques / updates", "B1, B3, C1, C1b, C3, A3"],
        ["2", "Indexador de transferencias", "A1, A2, C4, E1"],
        ["3", "Observador de finalidad (sondeo en vivo)", "B2"],
        ["4", "Clasificador de primitivas", "D1, D2, D3"],
        ["5", "Detector de mutabilidad", "C5"],
        ["6", "Lector de estado de consenso", "C1b, C2"],
        ["7", "Contador de actividad total (verdicts)", "C4, B3, E1"],
        ["8", "Motor de calculo", "Todas"],
    ], col_widths=[0.8 * cm, 6.5 * cm, 8.5 * cm]))
story.append(Spacer(1, 8))
story.append(P(
    "A diferencia del benchmark original, los modulos 1&ndash;7 <b>no son compartidos entre redes</b>: "
    "cada una tiene su propio colector (<font face=\"Courier\">scripts/collect_tempo.py</font>, "
    "<font face=\"Courier\">collect_aptos.py</font>, <font face=\"Courier\">collect_canton.py</font>) y "
    "su propio calculador. El motor de puntajes "
    "(<font face=\"Courier\">scripts/score_engine.py</font>) si es comun a las tres, igual que en el "
    "original. Todo el pipeline se ejecuta con un unico punto de entrada:", "Body"))
story.append(Paragraph("python main.py &nbsp;&nbsp;[--collect]", styles["Mono"]))
story.append(P(
    "que corre los colectores (si se pide <font face=\"Courier\">--collect</font>), los calculadores, "
    "el ensamblador de entregables y el motor de puntajes, e imprime el reporte diferenciado que se "
    "reproduce en la seccion 13.", "Body"))

n_collect = manifest.get("redes", {})
story.append(P("11.1&nbsp;&nbsp;Alcance real de esta corrida", "SubH"))
story.extend(dark_table(
    ["Red", "Fuente", "Cobertura"],
    [
        ["Tempo", n_collect.get("tempo", {}).get("endpoint", "-"),
         f"{n_collect.get('tempo', {}).get('n_bloques', '-')} bloques, "
         f"{n_collect.get('tempo', {}).get('n_transacciones', '-')} tx"],
        ["Aptos", n_collect.get("aptos", {}).get("endpoint", "-"),
         f"{n_collect.get('aptos', {}).get('n_bloques', '-')} bloques"],
        ["Canton", "api.cantonnodes.com (espejo publico de terceros)",
         f"{n_collect.get('canton', {}).get('n_eventos', '-')} eventos/verdicts"],
    ], col_widths=[2 * cm, 8 * cm, 6.5 * cm],
    note="Muestra de verificacion/implementacion, NO la ventana W_H de 14 dias que exige el plan completo."))

story.append(PageBreak())

# ============================= 12 =============================
story.append(P("12&nbsp;&nbsp;Limitaciones", "SectionH"))
story.append(bullets([
    "<b>La continuidad institucional no se evalua</b>, igual que en el benchmark original (2.2).",
    "<b>tau<sub>F</sub> mide tiempo, no fuerza de garantia.</b> Sub-segundo en Tempo y Aptos "
    "(cuando es medible), reconstruible historicamente en Canton via el verdict del mediador &mdash;"
    "arquitecturas de finalidad distintas producen numeros que no son directamente equiparables en "
    "robustez, solo en tiempo.",
    "<b>El acceso de terceros a Canton pasa por espejos de proveedores</b>, no por los Scan de SV "
    "directamente &mdash;los 4 probados rechazan acceso publico (2.2).",
    "<b>El precio APT/USD no tiene oraculo vivo verificado en esta pasada.</b> Pyth dejo de dar soporte "
    "a Aptos el 26-ago-2026; Chainlink Data Feeds es un candidato real (opera en Aptos) pero su "
    "direccion de mainnet no se confirmo en vivo en esta ejecucion.",
    "<b>El limite de gas por bloque de Aptos no existe como concepto</b> (a diferencia de EVM): la "
    "capacidad se rige por un techo por transaccion (GasScheduleV2) mas multiplicadores por escalon de "
    "stake (TxnLimitsConfig) &mdash;falta el modelo de agregacion a throughput comparable con las otras "
    "dos redes.",
    "<b>El sondeo de finalidad en Aptos con HTTP simple no resuelve B2</b>: el tiempo de bloque "
    "(~20ms) es mas rapido que el round-trip hacia la API publica.",
    "<b>USDCx no se encontro en 10.400 eventos reales de Canton</b> (dos ventanas distintas), pese a "
    "estar confirmado vivo por fuentes externas (Circle, Canton Network) &mdash;evidencia de actividad "
    "muy escasa o enteramente privada, no de ausencia del activo.",
    "<b>Los resultados son de una muestra reducida</b> (minutos de datos), no la ventana W_H de 14 dias "
    "ni la W_L de 72 horas que exige el plan completo. Cada valor en la seccion 13 declara su n.",
]))

story.append(PageBreak())

# ============================= 13: RESULTADOS REALES =============================
story.append(P("13&nbsp;&nbsp;Resultados obtenidos (ejecucion real, no especificacion)", "SectionH"))
story.append(P(
    "Esta seccion no tiene equivalente en el benchmark original tal como se recibio: el documento de "
    "referencia especifica el instrumento pero no muestra una sola cifra medida. Aqui se presentan los "
    "valores realmente obtenidos, con su estado y tamano muestral, generados por "
    "<font face=\"Courier\">python main.py</font> y persistidos en "
    "<font face=\"Courier\">resultados/metrics.csv</font>.", "Body"))

for red, nombre in [("tempo", "Tempo"), ("aptos", "Aptos"), ("canton", "Canton")]:
    story.append(P(f"13.{['tempo','aptos','canton'].index(red)+1}&nbsp;&nbsp;{nombre}", "SubH"))
    rows = metrics_table_for(red)
    story.extend(dark_table(
        ["ID", "Activo", "Valor", "Unidad", "n", "Estado"],
        rows,
        col_widths=[1.3 * cm, 4.7 * cm, 3 * cm, 2.6 * cm, 1.4 * cm, 2.7 * cm],
    ))
    story.append(Spacer(1, 10))

story.append(PageBreak())
story.append(P("13.4&nbsp;&nbsp;Compuertas", "SubH"))
gate_rows_fmt = []
seen = set()
for g in gates_rows:
    key = (g["red"], g["escenario"], g["compuerta"], g.get("activo", ""))
    if key in seen:
        continue
    seen.add(key)
    gate_rows_fmt.append([g["red"], g["escenario"], g["compuerta"],
                           g.get("activo", "") if g.get("activo") not in ("n/a", "") else "—",
                           g["resultado"]])
story.extend(dark_table(["Red", "Escenario", "Compuerta", "Activo", "Resultado"], gate_rows_fmt,
                         col_widths=[2.2 * cm, 2 * cm, 2.2 * cm, 5.5 * cm, 3.5 * cm]))
story.append(Spacer(1, 6))
story.append(callout(
    "<b>El hallazgo mas fuerte de este estudio</b> esta en esta tabla: Canton pasa G2' con "
    "Canton Coin (Amulet) y falla G2' con USDCx bajo el mismo synchronizer. Es exactamente la "
    "conclusion que D7 del plan anticipaba como la mas relevante posible: <i>Canton es admisible con "
    "su activo nativo e inadmisible con el activo que un pagador colombiano realmente usaria.</i>",
    "info"))

story.append(Spacer(1, 12))
story.append(P("13.5&nbsp;&nbsp;Puntajes por escenario", "SubH"))
score_rows_fmt = [[s["red"], s["escenario"], fmt_val(s["S_A"]), fmt_val(s["S_B"]), fmt_val(s["S_C"]),
                   fmt_val(s["S_D"]), fmt_val(s["S_total"]), s["admisible"]] for s in scores_rows]
story.extend(dark_table(
    ["Red", "Esc.", "S_A", "S_B", "S_C", "S_D", "S total", "Admisible"],
    score_rows_fmt,
    col_widths=[2 * cm, 1.3 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2 * cm, 2.5 * cm],
    note="S_total es la media geometrica ponderada solo sobre los bloques con al menos una metrica "
         "computable; los pesos se renormalizan sobre los bloques disponibles (ver 9.2). Con la "
         "cobertura parcial actual estos puntajes son ilustrativos del mecanismo, no un ranking final.",
))

story.append(Spacer(1, 12))
story.append(P("13.6&nbsp;&nbsp;&iquest;Cuales metricas discriminaron entre las tres redes?", "SubH"))
disc_fmt = [[d["metrica_id"], d["valores_por_red"][:70], d["discrimino"]] for d in disc_rows]
story.extend(dark_table(["Metrica", "Valores por red", "&iquest;Discrimino?"], disc_fmt,
                         col_widths=[1.8 * cm, 12 * cm, 3 * cm]))
story.append(Spacer(1, 6))
story.append(P(
    "Tal como exige la seccion 10.3 del benchmark original: reportar cuantas metricas distinguen "
    "efectivamente entre las redes es un resultado del instrumento en si mismo, no solo de las redes "
    "evaluadas.", "Body"))

story.append(PageBreak())
story.append(P("Referencias", "SectionH"))
story.append(P("<b>Redes evaluadas</b>", "BodyBold"))
story.append(bullets([
    "Tempo. Documentacion oficial: docs.tempo.xyz. Codigo fuente: github.com/tempoxyz/tempo "
    "(usado para confirmar VALIDATOR_CONFIG_V2_ADDRESS, crates/contracts/src/precompiles/mod.rs).",
    "Aptos Labs. aptos.dev (Indexer, REST API, recursos 0x1). Chainlink. docs.chain.link/data-feeds/aptos.",
    "Canton Network / Digital Asset. docs.canton.network, docs.sync.global (Synchronizer Traffic Fees, "
    "CIP-0042, CIP-0084). Canton Nodes (api.cantonnodes.com) y Blueprint (ccscan.xyz), espejos publicos "
    "de la Scan API.",
    "Circle. circle.com/blog &mdash; USDCx on Canton via xReserve (CIP-56).",
]))
story.append(P("<b>Mercado colombiano</b>", "BodyBold"))
story.append(bullets([
    "Banco de la Republica. Bre-B: Sistema de Pagos Inmediatos Interoperado de Colombia. Documento "
    "tecnico, febrero de 2026. Fuente de todos los umbrales de la seccion 6.",
    "Migracion Colombia, con base en estadisticas del Banco de la Republica. Remesas recibidas en 2025.",
]))
story.append(P("<b>Documento base</b>", "BodyBold"))
story.append(P(
    "Benchmark medible de redes EVM para pagos en Colombia: Polygon PoS &middot; Celo &middot; Arbitrum "
    "One. Documento de referencia sobre el que se construyo esta adaptacion (Sec.1&ndash;10, "
    "estructura y formulas heredadas salvo donde se declara explicitamente lo contrario).", "Body"))
story.append(Spacer(1, 20))
story.append(P(
    "Nota sobre el uso de las fuentes. Ninguna cifra de la seccion 13 proviene de una referencia: todo "
    "lo puntuado se mide, conforme a la regla de 2.1. Las referencias indican al sistema de recoleccion "
    "que contratos/recursos observar, no proveen valores.", "Small"))


# ---------------------------------------------------------------------------
def _header_footer(c: canvas_mod.Canvas, doc):
    c.saveState()
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GREY_TEXT)
    c.drawString(2 * cm, 1.2 * cm, "Benchmark medible de redes de pagos en Colombia — Tempo / Aptos / Canton")
    c.drawRightString(19 * cm, 1.2 * cm, f"{doc.page}")
    c.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=LETTER,
                         leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                         title="Benchmark medible de redes de pagos en Colombia -- Tempo, Aptos, Canton")
doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
print(f"PDF generado: {OUT}")
