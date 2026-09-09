import json
import csv
from datetime import datetime, timezone

RES = "resultados"

with open(f"{RES}/raw/tempo_metrics.json") as f:
    T = json.load(f)
with open(f"{RES}/raw/aptos_metrics.json") as f:
    A = json.load(f)
with open(f"{RES}/raw/canton_metrics.json") as f:
    C = json.load(f)


def calcula_H_cfg_tempo():
    """B3 real de Tempo: gasLimit de bloque / gasUsed mediano de recibo /
    cadencia mediana de bloque, sobre el requisito de 48 TPS del Anexo."""
    try:
        blocks = json.load(open(f"{RES}/raw/tempo/blocks_sample.json"))
        receipts = json.load(open(f"{RES}/raw/tempo/receipts_sample.json"))
    except FileNotFoundError:
        return None
    gas_limits = [int(b["gasLimit"], 16) for b in blocks if b.get("gasLimit")]
    gas_useds = sorted(int(r["gasUsed"], 16) for r in receipts if r and r.get("gasUsed"))
    ts = sorted(int(b["timestamp"], 16) + int(b.get("timestampMillisPart", "0x0"), 16) / 1000.0 for b in blocks)
    deltas = sorted(b - a for a, b in zip(ts, ts[1:]))
    if not (gas_limits and gas_useds and deltas):
        return None
    gas_limit = sum(gas_limits) / len(gas_limits)
    gas_mediana = gas_useds[len(gas_useds) // 2]
    cadencia = deltas[len(deltas) // 2]
    tps_cfg = (gas_limit / gas_mediana) / cadencia
    return dict(tps_cfg=tps_cfg, h_cfg=tps_cfg / 48.0, gas_limit=gas_limit,
                gas_mediana=gas_mediana, cadencia=cadencia, n=len(gas_useds))


H_CFG_TEMPO = calcula_H_cfg_tempo()

rows = []


def row(red, activo, metrica_id, escenario, valor, unidad, n, estado, razon="", consulta=""):
    rows.append(
        dict(
            red=red, activo=activo, metrica_id=metrica_id, escenario=escenario,
            valor=valor, unidad=unidad, n=n, ic_bajo="", ic_alto="",
            estado=estado, razon_estado=razon, consulta_ref=consulta,
        )
    )


NOTA_MUESTRA = "muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap"

# ---------------- TEMPO ----------------
row("tempo", "TIP-20 (feeToken observado)", "A1", "global", T["A1_costo_mediano_usd"], "USD", T["A_n"],
    "parcialmente_derivada", NOTA_MUESTRA + "; supuesto 18 decimales de precio de gas no confirmado contra TIP publicado", "collect_tempo.py+compute_tempo_metrics.py")
row("tempo", "TIP-20 (feeToken observado)", "A2", "global", T["A2_costo_p95_usd"], "USD", T["A_n"],
    "parcialmente_derivada", NOTA_MUESTRA, "idem")
row("tempo", "TIP-20 (feeToken observado)", "A3", "global", T["A3_beta_ocupacion_global"], "indice", T["A3_n"],
    "parcialmente_derivada", NOTA_MUESTRA + "; n muy pequeno para una regresion confiable, sin R2", "idem")
row("tempo", "n/a", "B1", "global", T["B1_cadencia_p95_s"], "segundos", T["B1_n"],
    "computada", NOTA_MUESTRA, "collect_tempo.py")
row("tempo", "n/a", "B2", "global", 0.6302020549774170, "segundos", 53,
    "parcialmente_derivada", "Mecanismo de sondeo en vivo (scripts/poll_finality.py) verificado y corrido 30s como demostracion (no las 72h de W_L que exige el plan). p95=0.81s. Confirma la advertencia del plan: tau_F es sub-segundo en Tempo, no discrimina frente al umbral t=60s/w=604800s -- el eje de irreversibilidad no separa a esta red en esta muestra.", "scripts/poll_finality.py (30s, n=53)")
row("tempo", "n/a", "B3", "global", H_CFG_TEMPO["h_cfg"] if H_CFG_TEMPO else None, "razon (H_cfg/48TPS)",
    H_CFG_TEMPO["n"] if H_CFG_TEMPO else 0,
    "parcialmente_derivada" if H_CFG_TEMPO else "no_computable",
    (f"H_cfg = (gasLimit={H_CFG_TEMPO['gas_limit']:.0f} / gasUsed_mediana={H_CFG_TEMPO['gas_mediana']}) / cadencia_mediana={H_CFG_TEMPO['cadencia']:.3f}s, sobre 48 TPS de referencia. No separa carril de pagos de ocupacion global (T-4 sigue abierto) -- es capacidad agregada del bloque completo, un limite superior optimista." if H_CFG_TEMPO
     else "T-4 abierto: no se pudo separar el carril de pagos de la ocupacion global"),
    "build_deliverables.py:calcula_H_cfg_tempo")
row("tempo", "n/a", "C1", "global", T["C1_herfindahl_produccion"], "indice", T["C1_n_bloques"],
    "computada", NOTA_MUESTRA, "collect_tempo.py")
row("tempo", "n/a", "C1b", "global", T["C1b_herfindahl_peso_consenso"], "indice", T["C1b_n_validadores_activos"],
    "computada", "T-2 RESUELTO: direccion 0xCCCCCCCC...01 (ValidatorConfigV2) hallada en codigo fuente (github.com/tempoxyz/tempo, crates/contracts/src/precompiles/mod.rs) y verificada con eth_call en vivo. El ABI no expone campo de peso/stake por validador -> consenso es de peso igualitario (1/N), no ponderado como en Aptos", "collect_tempo.py + eth_call getActiveValidators()")
row("tempo", "n/a", "C2", "global", T["C1b_n_validadores_activos"] // 2 + 1, "conteo", T["C1b_n_validadores_activos"],
    "computada", "sobre C1b (peso real, ahora resuelta): con pesos iguales entre 15 validadores activos, el umbral del 50% se cruza en el validador numero 8", "idem")
row("tempo", "n/a", "C3", "global", None, "porcentaje", 0,
    "no_computable", "no ejecutado en esta pasada", "-")
row("tempo", "n/a", "C4", "global", T["C4_tasa_fallo"], "fraccion", T["C4_n"],
    "computada", NOTA_MUESTRA, "collect_tempo.py")
row("tempo", "n/a", "C5", "global", None, "conteo", 0,
    "no_computable", "requiere fijar W_H primero", "-")
row("tempo", "n/a", "D1", "global", T["D1_fraccion_feePayer_distinto"], "fraccion", T["D1_n"],
    "computada", "OJO: 100% en la muestra; posible artefacto de la abstraccion de cuentas nativa de Tempo (feePayer podria estar siempre poblado por diseno, no solo cuando un tercero patrocina) -- ver docs/matriz_requerimientos.md", "collect_tempo.py")
row("tempo", "n/a", "D2", "global", None, "fraccion", 0,
    "no_computable", "no se decodifico el calldata en busca de memo en esta pasada", "-")
row("tempo", "n/a", "D3", "global", T["D3_fraccion_multi_transferencia"], "fraccion", T["D3_n_tx_con_transferencia"],
    "parcialmente_derivada", "probablemente sobreestimada: incluye Transfer logs del reparto de comision (TipFeeManager), no solo pagos multi-instrumento genuinos", "collect_tempo.py")
row("tempo", "TIP-20 nativo", "E1", "global", 1, "fraccion", None,
    "computada", "degenerada por diseno: todo Transfer de un TIP-20 es publico via logs", "-")

# ---------------- APTOS ----------------
row("aptos", "APT (gas)", "A1", "global", None, "fraccion", 0,
    "no_computable", "Pyth (unico oraculo APT/USD hallado) dejo de soportar Aptos el 2026-08-26; sin oraculo vivo no hay conversion octas->USD auditable en este momento", "-")
row("aptos", "APT (gas)", "A2", "global", None, "fraccion", 0,
    "no_computable", "misma razon que A1", "-")
row("aptos", "n/a", "B2", "global", None, "segundos", 3,
    "no_computable", "Se intento un sondeo corto (30s, scripts/poll_finality.py) y produjo 17 alturas nuevas pero solo 3 con delta valido, con signos mezclados (-0.09s, +0.03s, -0.56s). Hallazgo metodologico real: el tiempo de bloque de Aptos (~20ms) es mas rapido que el round-trip HTTP hacia la API publica, asi que un sondeo secuencial simple no puede resolver B2 aqui -- se necesitaria un nodo de baja latencia o streaming, no polling HTTP estandar.", "scripts/poll_finality.py (30s, n=3 invalido)")
row("aptos", "n/a", "A3", "global", None, "indice", None,
    "no_computable", "NO es la elasticidad todavia -- 20.000.000 (txn.maximum_number_of_gas_units, de 0x1::gas_schedule::GasScheduleV2) es un techo de capacidad por transaccion, no la pendiente ln(costo)~ocupacion que pide A3. El dato de capacidad ya no esta bloqueado (ver B3), pero A3 en si requiere costo real por tx (bloqueado por el oraculo, ver A1/A2) regresado contra alguna nocion de ocupacion -- sigue sin poder calcularse hasta resolver A1/A2.", "GET /v1/accounts/0x1/resource/0x1::gas_schedule::GasScheduleV2")
row("aptos", "n/a", "B1", "global", A["B1_cadencia_p95_s"], "segundos", A["B1_n"],
    "computada", NOTA_MUESTRA, "collect_aptos.py")
row("aptos", "n/a", "B3", "global", None, "razon", 0,
    "no_computable", "ya no bloqueado por falta de dato (ver A3), sino por falta de modelo: falta combinar GasScheduleV2 + TxnLimitsConfig + tiempo de bloque en un H_cfg comparable a los 48 TPS de referencia", "-")
row("aptos", "n/a", "C1", "global", A["C1_herfindahl_produccion"], "indice", A["C1_n_bloques_con_metadata"],
    "computada", NOTA_MUESTRA, "collect_aptos.py")
row("aptos", "n/a", "C1b", "global", A["C1b_herfindahl_peso_consenso"], "indice", A["C1b_n_validadores"],
    "computada", "peso de consenso completo (84 validadores activos), no es muestra temporal", "collect_aptos.py")
row("aptos", "n/a", "C2", "global", A["C2_operadores_sobre_50pct_por_peso"], "conteo", A["C1b_n_validadores"],
    "computada", "sobre C1b (peso), que es la metrica primaria segun el plan (D3)", "collect_aptos.py")
row("aptos", "n/a", "C3", "global", A["C3_fraccion_continuidad"], "porcentaje", A["C3_n"],
    "computada", NOTA_MUESTRA, "collect_aptos.py")
row("aptos", "n/a", "C4", "global", A["C4_tasa_fallo"], "fraccion", A["C4_n"],
    "computada", NOTA_MUESTRA, "collect_aptos.py")
row("aptos", "n/a", "C5", "global", None, "conteo", 0,
    "no_computable", "requiere fijar W_H primero", "-")
row("aptos", "n/a", "D1", "global", A["D1_fraccion_fee_payer_distinto"], "fraccion", A["D1_n"],
    "computada", NOTA_MUESTRA + "; medicion limpia (fee_payer_signature explicito), sin la ambiguedad observada en Tempo", "collect_aptos.py")
row("aptos", "n/a", "D2", "global", None, "fraccion", 0,
    "no_computable", "depende de fijar primero la definicion operativa de A-5, como exige el propio plan", "-")
row("aptos", "n/a", "D3", "global", None, "fraccion", 0,
    "no_computable", "no ejecutado en esta pasada", "-")
row("aptos", "Fungible Asset (generico)", "E1", "global", 1, "fraccion", None,
    "computada", "degenerada por diseno: eventos de Fungible Asset son publicos", "-")

# ---------------- CANTON ----------------
row("canton", "Canton Coin (Amulet)", "A1", "global", C["A1_costo_usd_mediana_confirmado"], "USD", C["A_n"],
    "parcialmente_derivada", "Unidad CONFIRMADA via docs.sync.global (Synchronizer Traffic Fees, CIP-0042/CIP-0084): trafficPrice=60 USD/MB, total_traffic_cost en bytes. Coincide con el objetivo de diseno de CIP-0042 (~1 USD por transferencia estandar de CC). Sigue parcial porque la ventana (~189s) cae en un burst periodico de ValidatorLicense_ReportActive, no en trafico de pagos tipico.", "collect_canton.py + docs.sync.global/deployment/traffic.html")
row("canton", "Canton Coin (Amulet)", "A2", "global", C["A2_costo_usd_p95_confirmado"], "USD", C["A_n"],
    "parcialmente_derivada", "misma confirmacion de unidad que A1; misma limitacion de ventana no representativa", "idem")
row("canton", "Canton Coin (Amulet)", "A3", "global", None, "indice", 0,
    "no_computable", "no ejecutado: requiere bucketizar traffic_summary por intervalo, pendiente", "-")
row("canton", "n/a", "B1", "global", C["B1_B2_latencia_confirmacion_p95_s"], "segundos", C["B1_B2_n"],
    "computada", C["nota_B1_B2"] + " " + NOTA_MUESTRA + "; ventana de solo ~189s dominada por un burst, no representativa de latencia tipica", "collect_canton.py")
row("canton", "n/a", "B2", "global", C["B1_B2_latencia_confirmacion_p95_s"], "segundos", C["B1_B2_n"],
    "computada", C["nota_B1_B2"], "collect_canton.py")
row("canton", "n/a", "B3", "global", None, "razon", 0,
    "no_computable", "limites de trafico del sincronizador no extraidos todavia de /v0/dso", "-")
row("canton", "n/a", "C1", "global", None, "indice", 0,
    "no_computable", "degenerada por diseno: Canton no tiene bloques", "degenerada")
row("canton", "n/a", "C1b", "global", None, "indice", 0,
    "no_computable", "pesos de SV estan en /v0/dso (dso_rules/sv_node_states) pero no se extrajeron en esta pasada", "-")
row("canton", "n/a", "C2", "global", None, "conteo", 0,
    "no_computable", "depende de C1b", "-")
row("canton", "n/a", "C3", "global", None, "porcentaje", 0,
    "no_computable", "requiere identificar primero el latido del DSO (C-5), no ejecutado", "-")
row("canton", "n/a", "C4", "global", C["C4_tasa_fallo"], "fraccion", C["C4_n"],
    "computada", NOTA_MUESTRA + "; ventana de ~189s dominada por un burst de reportes de validador", "collect_canton.py")
row("canton", "n/a", "C5", "global", None, "conteo", 0,
    "no_computable", "requiere fijar W_H primero", "-")
row("canton", "n/a", "D1", "global", None, "fraccion", 0,
    "no_computable", "requiere decidir primero como declarar el sujeto (el operador compra trafico, no el usuario), no ejecutado", "-")
row("canton", "n/a", "D2", "global", None, "fraccion", 0,
    "no_computable", "no ejecutado; depende de si el activo es visible al DSO", "-")
row("canton", "n/a", "D3", "global", None, "fraccion", 0,
    "no_computable", "no ejecutado en esta pasada", "-")
row("canton", "Canton Coin (Amulet)", "E1", "global", 1, "fraccion", None,
    "computada", "verdicts y traffic son publicos via el espejo api.cantonnodes.com", "collect_canton.py")
row("canton", "USDCx (Circle xReserve, CIP-56)", "E1", "global", 0, "fraccion", 10400,
    "parcialmente_derivada", "USDCx esta confirmado vivo en mainnet por fuente externa (canton.network/blog, circle.com/blog, CIP-56), pero la busqueda propia de template_id tipo Holding/Token en 10.400 eventos reales sobre DOS ventanas distintas (una de burst de medianoche, otra de 8 min en horario habil) no encontro ninguno -- todos los templates visibles son nativos de Amulet/Splice. Esto es evidencia mas fuerte que antes de que, si USDCx circula, su actividad visible es muy escasa frente a la nativa, o bien nunca deja `update` visible (solo verdict) -- consistente con D7 del plan: si es privada, E1=0 para ese activo es precisamente el resultado esperado, no una falla de busqueda.", "collect_canton.py + compute_canton_metrics.py (busqueda de template_families, n=10.400 eventos)")

with open(f"{RES}/metrics.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"metrics.csv escrito con {len(rows)} filas")

# ---------------- limitaciones.md ----------------
no_comp = [r for r in rows if r["estado"] in ("no_computable",)]
parcial = [r for r in rows if r["estado"] == "parcialmente_derivada"]

with open(f"{RES}/limitaciones.md", "w", encoding="utf-8") as f:
    f.write("# Limitaciones — generado desde metrics.csv\n\n")
    f.write(f"Fecha: {datetime.now(timezone.utc).isoformat()}\n\n")
    f.write("Esta es una pasada de verificacion/implementacion con muestras reducidas, no la ")
    f.write("recoleccion completa de 14 dias (W_H) que especifica el plan. Cada entrada abajo ")
    f.write("es una metrica que NO se completo con un valor pleno, junto con la razon exacta.\n\n")
    f.write("## No computable\n\n")
    for r in no_comp:
        f.write(f"- **{r['red']}.{r['metrica_id']}**: {r['razon_estado']}\n")
    f.write("\n## Parcialmente derivada (valor obtenido, con supuesto o advertencia sin verificar)\n\n")
    for r in parcial:
        f.write(f"- **{r['red']}.{r['metrica_id']}** = {r['valor']}: {r['razon_estado']}\n")

print(f"limitaciones.md escrito: {len(no_comp)} no_computable, {len(parcial)} parcialmente_derivada")

# ---------------- run_manifest.json ----------------
manifest = {
    "fecha_ejecucion": datetime.now(timezone.utc).isoformat(),
    "tipo_de_corrida": "verificacion/implementacion con muestra reducida, NO la ventana W_H de 14 dias del plan",
    "redes": {
        "tempo": {
            "endpoint": "https://rpc.tempo.xyz",
            "proveedores_independientes": 1,
            "rango": "ver resultados/raw/tempo/blocks_sample.json (150 bloques mas recientes al momento de la corrida)",
            "n_bloques": T["n_blocks"],
            "n_transacciones": T.get("n_receipts"),
        },
        "aptos": {
            "endpoint": "https://api.mainnet.aptoslabs.com/v1",
            "proveedores_independientes": 1,
            "rango": "ver resultados/raw/aptos/blocks_sample.json (60 bloques mas recientes al momento de la corrida)",
            "n_bloques": A["n_blocks"],
        },
        "canton": {
            "endpoint": "https://api.cantonnodes.com (espejo publico de terceros; los Scan de SV directos -sync.global, digitalasset.com, cumberland.io, fivenorth.io- rechazaron acceso publico con 403/RBAC)",
            "proveedores_independientes": 1,
            "rango": f"{C.get('ventana_inicio')} a {C.get('ventana_fin')} ({C.get('ventana_cubierta_s')} s) -- ventana dominada por un burst periodico, no representativa del trafico tipico",
            "n_eventos": C["n_eventos"],
        },
    },
    "limitaciones_estructurales": [
        "Tempo: no se localizo la direccion del precompilado ValidatorConfig (T-2) -> C1b no computable en Tempo",
        "Aptos: oraculo Pyth (APT/USD) descontinuado el 2026-08-26 -> A1/A2 no computables sin oraculo vivo",
        "Aptos: limite de gas de bloque ahora es un blob BCS opaco (ExecutionConfig) -> A3/B3 no computables sin decodificacion BCS",
        "Canton: los Scan de Super Validador individuales bloquean acceso publico directo (403/RBAC); solo se pudo verificar un espejo de tercero (api.cantonnodes.com) -> no se cumplio el control de concordancia entre dos SV independientes (C-7)",
    ],
    "segundo_proveedor_por_red": "NO CUMPLIDO en esta pasada para ninguna red -- solo se uso un proveedor por red",
    "codigo": {
        "collect_tempo.py": "resultados/raw/tempo",
        "collect_aptos.py": "resultados/raw/aptos",
        "collect_canton.py": "resultados/raw/canton",
        "compute_tempo_metrics.py": "resultados/tempo_metrics.json",
        "compute_aptos_metrics.py": "resultados/aptos_metrics.json",
        "compute_canton_metrics.py": "resultados/canton_metrics.json",
    },
}
with open(f"{RES}/run_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2, default=str)

print("run_manifest.json escrito")
