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


def row(red, activo, metrica_id, escenario, valor, unidad, n, estado, razon="", consulta="", modo="historico"):
    """modo describe COMO se obtuvo el dato, en el vocabulario del propio plan
    (Sec.7.1): 'historico' = consulta reproducible sobre bloques/eventos/estado
    ya producidos (ventana W_H, aunque la consulta se haya hecho hace un
    instante contra un nodo en vivo); 'tiempo_real' = requiere sondeo continuo
    mientras ocurre (ventana W_L, ej. B2 en Tempo/Aptos); 'no_aplica' = metrica
    degenerada por diseno o transversal, sin ventana temporal de por medio."""
    rows.append(
        dict(
            red=red, activo=activo, metrica_id=metrica_id, escenario=escenario,
            valor=valor, unidad=unidad, n=n, ic_bajo="", ic_alto="",
            estado=estado, razon_estado=razon, consulta_ref=consulta, modo_dato=modo,
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
    "parcialmente_derivada", "Mecanismo de sondeo en vivo (scripts/poll_finality.py) verificado y corrido 30s como demostracion (no las 72h de W_L que exige el plan). p95=0.81s. Confirma la advertencia del plan: tau_F es sub-segundo en Tempo, no discrimina frente al umbral t=60s/w=604800s -- el eje de irreversibilidad no separa a esta red en esta muestra.", "scripts/poll_finality.py (30s, n=53)",
    modo="tiempo_real")
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
row("tempo", "n/a", "C3", "global", T.get("C3_fraccion_continuidad"), "porcentaje", T.get("C3_n", 0),
    "computada" if T.get("C3_fraccion_continuidad") is not None else "no_computable",
    "Reconstruido con datos historicos, no requiere sondeo en vivo (a diferencia de B2): huecos > 10x la cadencia mediana sobre los mismos bloques ya descargados. " + NOTA_MUESTRA,
    "compute_tempo_metrics.py (sobre blocks_sample.json)")
row("tempo", "n/a", "C4", "global", T["C4_tasa_fallo"], "fraccion", T["C4_n"],
    "computada", NOTA_MUESTRA, "collect_tempo.py")
row("tempo", "n/a", "C5", "global", T.get("C5_actualizaciones_en_ventana"), "conteo", 1,
    "computada" if T.get("C5_actualizaciones_en_ventana") is not None else "no_computable",
    (f"RESUELTO en esta pasada: se encontro una extension RPC admisible del propio nodo, tempo_forkSchedule "
     f"(confirmada leyendo crates/node/src/rpc/fork_schedule.rs en el codigo fuente publico), que expone el "
     f"schedule completo de TIPs con su activationTime real -- fuente del registro, no el changelog/TIPs de "
     f"GitHub (eso si violaria la regla de oro). En la ventana muestreada ({T.get('C5_ventana_ts')}, ~6.5 min) "
     f"no se activo ningun fork nuevo ({T.get('C5_detalle')}); fork activo actual: {T.get('C5_fork_activo_actual')}. "
     f"0 en una ventana de minutos es el resultado esperado, no una falla -- los forks de Tempo se activan con "
     f"semanas de separacion segun el propio schedule." if T.get("C5_actualizaciones_en_ventana") is not None
     else "no se pudo leer tempo_forkSchedule en esta pasada"),
    "collect_tempo.py (RPC tempo_forkSchedule) + compute_tempo_metrics.py")
row("tempo", "n/a", "D1", "global", T["D1_fraccion_feePayer_distinto"], "fraccion", T["D1_n"],
    "computada", "OJO: 100% en la muestra; posible artefacto de la abstraccion de cuentas nativa de Tempo (feePayer podria estar siempre poblado por diseno, no solo cuando un tercero patrocina) -- ver docs/matriz_requerimientos.md", "collect_tempo.py")
row("tempo", "n/a", "D2", "global", T.get("D2_fraccion_con_memo"), "fraccion", T.get("D2_n", 0),
    "computada" if T.get("D2_fraccion_con_memo") is not None else "no_computable",
    (f"RESUELTO en esta pasada: la interfaz ITIP20 (crates/contracts/src/precompiles/tip20.rs, codigo fuente publico) "
     f"confirma la funcion transferWithMemo(address,uint256,bytes32) y su evento TransferWithMemo(address indexed from, "
     f"address indexed to, uint256 amount, bytes32 indexed memo). D2 se mide via el topic0 de ese evento "
     f"(keccak256 calculado, no copiado) sobre los logs ya descargados de las mismas transacciones usadas para D3 -- "
     f"reconstruible con datos historicos, no requirio nueva consulta a la red." if T.get("D2_fraccion_con_memo") is not None
     else "no se encontro el evento TransferWithMemo en la muestra"),
    "compute_tempo_metrics.py (topic MEMO_TOPIC sobre receipts_sample.json)")
row("tempo", "n/a", "D3", "global", T["D3_fraccion_multi_transferencia"], "fraccion", T["D3_n_tx_con_transferencia"],
    "parcialmente_derivada", "probablemente sobreestimada: incluye Transfer logs del reparto de comision (TipFeeManager), no solo pagos multi-instrumento genuinos", "collect_tempo.py")
row("tempo", "TIP-20 nativo", "E1", "global", 1, "fraccion", None,
    "computada", "degenerada por diseno: todo Transfer de un TIP-20 es publico via logs", "-", modo="no_aplica")

# ---------------- APTOS ----------------
row("aptos", "APT (gas)", "A1", "global", A.get("A1_costo_mediano_usd"), "USD", A.get("A_n", 0),
    "parcialmente_derivada" if A.get("A1_costo_mediano_usd") is not None else "no_computable",
    (f"RESUELTO en esta pasada: el ID de 32 bytes del feed APT/USD de Pyth se obtuvo de la propia API en vivo de Pyth "
     f"(hermes.pyth.network/v2/price_feeds?query=APT), no se adivino -- y se verifico contra el contrato en Aptos "
     f"(POST /v1/tables/{{handle}}/item devuelve el mismo price_identifier que se consulto, autoconsistente). El oraculo sigue "
     f"CONGELADO desde 2026-08-26 (timestamp on-chain confirmado: {A.get('A1A2_precio_timestamp_unix')} unix = 2026-08-26 16:08:48 UTC, "
     f"coincide con la fecha de congelamiento documentada). Precio usado: {A.get('A1A2_precio_apt_usd_congelado')} USD/APT, fijo para "
     f"toda la muestra -- exactamente la desviacion explicita que preve el plan (Sec.4.2 [VERIFICAR A-2]: precio congelado, "
     f"parcialmente_derivada, no computada limpia). costo_usd = gas_used*gas_unit_price/1e8 (octas->APT) * precio congelado." if A.get("A1_costo_mediano_usd") is not None
     else "Pyth dejo de dar soporte a Aptos el 2026-08-26; no se pudo obtener el precio congelado en esta pasada."),
    "collect_aptos.py (tabla Pyth) + compute_aptos_metrics.py")
row("aptos", "APT (gas)", "A2", "global", A.get("A2_costo_p95_usd"), "USD", A.get("A_n", 0),
    "parcialmente_derivada" if A.get("A2_costo_p95_usd") is not None else "no_computable",
    "misma resolucion y misma advertencia de precio congelado que A1", "idem")
row("aptos", "n/a", "B2", "global", None, "segundos", 3,
    "no_computable", "Se intento un sondeo corto (30s, scripts/poll_finality.py) y produjo 17 alturas nuevas pero solo 3 con delta valido, con signos mezclados (-0.09s, +0.03s, -0.56s). Hallazgo metodologico real: el tiempo de bloque de Aptos (~20ms) es mas rapido que el round-trip HTTP hacia la API publica, asi que un sondeo secuencial simple no puede resolver B2 aqui -- se necesitaria un nodo de baja latencia o streaming, no polling HTTP estandar. NO es reconstruible con datos historicos por definicion (D1 del plan): requiere W_L en vivo.", "scripts/poll_finality.py (30s, n=3 invalido)",
    modo="tiempo_real")
row("aptos", "n/a", "A3", "global", A.get("A3_beta_ocupacion_global"), "indice", A.get("A3_n"),
    "parcialmente_derivada" if A.get("A3_beta_ocupacion_global") is not None else "no_computable",
    (f"RESUELTO en esta pasada: el blob BCS de 0x1::execution_config::ExecutionConfig se decodifico contra el layout "
     f"EXACTO de OnChainExecutionConfig (verificado leyendo types/src/on_chain_config/execution_config.rs en "
     f"aptos-labs/aptos-core, codigo fuente publico -- 79 de 79 bytes consumidos sin sobrante, fuerte indicio de que "
     f"el layout es correcto). Variante V7 activa, block_gas_limit_type=ComplexLimitV1, "
     f"effective_block_gas_limit={A.get('B3_block_gas_limit')}. SIMPLIFICACION DECLARADA: la formula real del "
     f"protocolo pondera execution_gas/io_gas por separado y penaliza conflictos en una ventana (ver comentario en "
     f"el propio struct); aqui se usa gas_used total sin ponderar como proxy de ocupacion (los multiplicadores son "
     f"1 y el conflict_penalty_window no se rastrea desde REST), asi que beta es aproximado, no exacto. "
     f"{NOTA_MUESTRA}" if A.get("A3_beta_ocupacion_global") is not None
     else "no se pudo decodificar ExecutionConfig o combinar con costo real"),
    "collect_aptos.py + compute_aptos_metrics.py:decode_execution_config")
row("aptos", "n/a", "B1", "global", A["B1_cadencia_p95_s"], "segundos", A["B1_n"],
    "computada", NOTA_MUESTRA, "collect_aptos.py")
row("aptos", "n/a", "B3", "global", A.get("B3_h_cfg"), "razon (H_cfg/48TPS)", A.get("B3_n", 0),
    "parcialmente_derivada" if A.get("B3_h_cfg") is not None else "no_computable",
    (f"RESUELTO en esta pasada, mismo decode verificado que A3: H_cfg = (block_gas_limit={A.get('B3_block_gas_limit')} "
     f"/ gas_used_mediana={A.get('B3_gas_mediana_tx')}) / cadencia_mediana_bloque, sobre 48 TPS de referencia. "
     f"Es capacidad agregada del bloque completo (no separa por tipo de transaccion), igual limitacion declarada "
     f"que en Tempo B3 -- limite superior optimista, no un carril de pagos aislado." if A.get("B3_h_cfg") is not None
     else "no se pudo decodificar ExecutionConfig en esta pasada"),
    "collect_aptos.py + compute_aptos_metrics.py:decode_execution_config")
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
row("aptos", "n/a", "C5", "global", A.get("C5_publicaciones_modulo"), "conteo", A.get("C5_n", 0),
    "computada", "Reconstruido con datos historicos (mismos bloques ya descargados): cuenta entry functions de publicacion de codigo (0x1::code::publish_package_txn y variantes) entre las transacciones de la muestra. 0 en la ventana muestreada es un resultado valido, no una falla. " + NOTA_MUESTRA,
    "compute_aptos_metrics.py (sobre blocks_sample.json)")
row("aptos", "n/a", "D1", "global", A["D1_fraccion_fee_payer_distinto"], "fraccion", A["D1_n"],
    "computada", NOTA_MUESTRA + "; medicion limpia (fee_payer_signature explicito), sin la ambiguedad observada en Tempo", "collect_aptos.py")
row("aptos", "n/a", "D2", "global", None, "fraccion", 0,
    "no_computable", "depende de fijar primero la definicion operativa de A-5, como exige el propio plan", "-")
row("aptos", "n/a", "D3", "global", A.get("D3_fraccion_multi_transferencia"), "fraccion", A.get("D3_n_tx_con_transferencia", 0),
    "parcialmente_derivada" if A.get("D3_fraccion_multi_transferencia") is not None else "no_computable",
    (f"RESUELTO en esta pasada: se resolvio el `store` de cada evento 0x1::fungible_asset::Deposit/Withdraw a su "
     f"activo real via 0x1::fungible_asset::FungibleStore.metadata (29 stores distintos, 29/29 resueltos, colapsan "
     f"a solo 3 activos reales). multi-transferencia (>1 evento FA por tx) = {A.get('D3_fraccion_multi_transferencia')}; "
     f"multi-activo (>1 activo distinto por tx) = {A.get('D3_fraccion_multi_activo')}. ADVERTENCIA: n={A.get('D3_n_tx_con_transferencia')} "
     f"es MUY pequeno (la muestra de bloques esta dominada por un protocolo de trading de derivados, modulo "
     f"0x50ead22a..., no por transferencias de pago simples), y estos numeros probablemente miden rebalanceo de "
     f"colateral de trading (depositar/retirar garantia en mas de un activo durante una operacion), no pagos "
     f"multi-instrumento genuinos -- mismo tipo de contaminacion que D3 en Tempo (TipFeeManager) y Canton "
     f"(reward coupons), reportada con la misma regla: el dato real con la advertencia, no un numero limpio sin "
     f"verificar la causa." if A.get("D3_fraccion_multi_transferencia") is not None
     else "no se pudo resolver store->activo en esta pasada"),
    "collect_aptos.py (resolucion store->FungibleStore.metadata) + compute_aptos_metrics.py")
row("aptos", "Fungible Asset (generico)", "E1", "global", 1, "fraccion", None,
    "computada", "degenerada por diseno: eventos de Fungible Asset son publicos", "-", modo="no_aplica")

# ---------------- CANTON ----------------
row("canton", "Canton Coin (Amulet)", "A1", "global", C["A1_costo_usd_mediana_confirmado"], "USD", C["A_n"],
    "parcialmente_derivada", "Unidad CONFIRMADA via docs.sync.global (Synchronizer Traffic Fees, CIP-0042/CIP-0084): trafficPrice=60 USD/MB, total_traffic_cost en bytes. Coincide con el objetivo de diseno de CIP-0042 (~1 USD por transferencia estandar de CC). Sigue parcial porque la ventana (~189s) cae en un burst periodico de ValidatorLicense_ReportActive, no en trafico de pagos tipico.", "collect_canton.py + docs.sync.global/deployment/traffic.html")
row("canton", "Canton Coin (Amulet)", "A2", "global", C["A2_costo_usd_p95_confirmado"], "USD", C["A_n"],
    "parcialmente_derivada", "misma confirmacion de unidad que A1; misma limitacion de ventana no representativa", "idem")
row("canton", "Canton Coin (Amulet)", "A3", "global", C.get("A3_beta_ocupacion_sincronizador"), "indice", C.get("A3_n", 0),
    "computada" if C.get("A3_beta_ocupacion_sincronizador") is not None else "no_computable",
    f"Reconstruido con datos historicos ya descargados: regresion ln(costo individual) ~ trafico total del sincronizador en buckets de {C.get('A3_bucket_s','?')}s (sustituto de ocupacion, Sec.5.1 del plan). beta≈0 ({C.get('A3_beta_ocupacion_sincronizador')}) es el resultado ESPERADO por diseno de tarifa fija (trafficPrice constante en USD/MB, no varia con la congestion) -- confirma la prediccion del plan, no es un calculo fallido.",
    "compute_canton_metrics.py (sobre events_sample.json)")
row("canton", "n/a", "B1", "global", C["B1_B2_latencia_confirmacion_p95_s"], "segundos", C["B1_B2_n"],
    "computada", C["nota_B1_B2"] + " " + NOTA_MUESTRA + "; ventana de solo ~189s dominada por un burst, no representativa de latencia tipica", "collect_canton.py")
row("canton", "n/a", "B2", "global", C["B1_B2_latencia_confirmacion_p95_s"], "segundos", C["B1_B2_n"],
    "computada", C["nota_B1_B2"], "collect_canton.py")
row("canton", "n/a", "B3", "global", C.get("B3_h_cfg"), "razon (H_cfg/48TPS)", C.get("B3_n", 0),
    "parcialmente_derivada" if C.get("B3_h_cfg") is not None else "no_computable",
    (f"Reconstruido con datos historicos: baseRateTrafficLimits en dso_rules ya estaba descargado (burstAmount={C.get('B3_burst_bytes')} bytes cada burstWindow={C.get('B3_burst_window_s')}s -> {C.get('B3_burst_bytes',0)/C.get('B3_burst_window_s',1):.2f} bytes/s), dividido por el costo mediano en bytes de una transferencia (A1). ADVERTENCIA METODOLOGICA IMPORTANTE: este campo es la asignacion GRATUITA por MIEMBRO antes de tener que comprar trafico extra (ver choice AmuletRules_BuyMemberTraffic, extraTrafficPrice=60 USD/MB en el mismo estado) -- no es un techo agregado del sincronizador completo. H_cfg={C.get('B3_h_cfg')} probablemente SUBESTIMA drasticamente la capacidad real de Canton, porque el trafico adicional se compra sin un limite aparente en el estado consultado. Se reporta como lectura conservadora de un miembro individual, no como el techo real de la red -- no interpretar como 'Canton no puede sostener 48 TPS'." if C.get("B3_h_cfg") is not None
     else "no se pudo extraer baseRateTrafficLimits de dso_state.json"),
    "compute_canton_metrics.py (sobre dso_state.json)")
row("canton", "n/a", "C1", "global", None, "indice", 0,
    "no_computable", "degenerada por diseno: Canton no tiene bloques", "degenerada", modo="no_aplica")
row("canton", "n/a", "C1b", "global", C.get("C1b_herfindahl_peso_consenso"), "indice", C.get("C1b_n_sv", 0),
    "computada" if C.get("C1b_herfindahl_peso_consenso") is not None else "no_computable",
    "Reconstruido con datos historicos ya descargados: dso_rules.svs (dso_state.json, collect_canton.py) trae svRewardWeight por cada Super Validador; no requirio nueva consulta, solo leerlo. Cobertura completa del conjunto de SV (no es muestra temporal).",
    "compute_canton_metrics.py (sobre dso_state.json)")
row("canton", "n/a", "C2", "global", C.get("C2_operadores_sobre_50pct"), "conteo", C.get("C1b_n_sv", 0),
    "computada" if C.get("C2_operadores_sobre_50pct") is not None else "no_computable",
    "sobre C1b (peso real via svRewardWeight)", "compute_canton_metrics.py (sobre dso_state.json)")
row("canton", "n/a", "C3", "global", C.get("C3_fraccion_continuidad"), "porcentaje", C.get("C3_n", 0),
    "computada" if C.get("C3_fraccion_continuidad") is not None else "no_computable",
    f"Reconstruido con datos historicos: se identifico el latido del DSO independiente del trafico de usuarios (choice ValidatorLicense_ReportActive, cadencia mediana observada {C.get('C3_cadencia_latido_mediana_s')}s), tal como pide C-5/C3 del plan para no confundir ausencia de demanda con caida del sincronizador. Continuidad sobre ese latido, no sobre pagos. " + NOTA_MUESTRA,
    "compute_canton_metrics.py (sobre events_sample.json)")
row("canton", "n/a", "C4", "global", C["C4_tasa_fallo"], "fraccion", C["C4_n"],
    "computada", NOTA_MUESTRA + "; ventana de ~189s dominada por un burst de reportes de validador", "collect_canton.py")
row("canton", "n/a", "C5", "global", C.get("C5_cambios_estructurales"), "conteo", C.get("C5_n", 0),
    "computada",
    f"Definicion operativa declarada (el plan no fija una lista cerrada de que choice cuenta como 'cambio de la ruta de pago'): se cuentan choices DsoRules_* que exceden el ruido rutinario (votos de precio, reportes de estado, confirmaciones y merges de recompensa ya contados por otras metricas); detalle: {json.dumps(C.get('C5_detalle', {}), ensure_ascii=False)}. 0 en la ventana muestreada seria un resultado igualmente valido.",
    "compute_canton_metrics.py (sobre events_sample.json)")
row("canton", "n/a", "D1", "global", C.get("D1_declarado_degenerada"), "fraccion", None,
    "computada",
    "Sujeto declarado segun Sec.5.4 del plan: 'el operador compra trafico, no el usuario'. Degenerada por arquitectura, igual que Tempo D1=100%: el costo de red (trafico del sincronizador) lo adquiere el operador del validador/app provider, no el usuario final gastando un activo volatil propio para pagar la comision de red.",
    "-", modo="no_aplica")
row("canton", "n/a", "D2", "global", C.get("D2_fraccion_con_referencia"), "fraccion", C.get("D2_D3_n", 0),
    "computada" if C.get("D2_fraccion_con_referencia") is not None else "no_computable",
    "Reconstruido con datos historicos: sobre las choices de transferencia real (TransferFactory_Transfer, AmuletRules_Transfer), se mide la fraccion con el campo `meta` del estandar de token no vacio -- exactamente el mecanismo que el plan preve para D2 en activos visibles al DSO.",
    "compute_canton_metrics.py (sobre events_sample.json)")
row("canton", "n/a", "D3", "global", C.get("D3_fraccion_multi_transferencia"), "fraccion", C.get("D2_D3_n", 0),
    "parcialmente_derivada" if C.get("D3_fraccion_multi_transferencia") is not None else "no_computable",
    (f"Reconstruido con datos historicos sobre las mismas choices de transferencia. multi-transferencia (>1 salida) = {C.get('D3_fraccion_multi_transferencia')}. multi-activo (>1 instrumento de entrada, normalizando holdings bloqueados del mismo activo) = {C.get('D3_fraccion_multi_activo')}: este segundo numero esta probablemente CONTAMINADO por la redencion de reward coupons (SvRewardCoupon/AppRewardCoupon/ValidatorRewardCoupon) dentro de la misma choice AmuletRules_Transfer -- mecanica de protocolo/incentivos, no pagos multi-instrumento genuinos por el usuario. Mismo tipo de advertencia que D3 en Tempo con TipFeeManager." if C.get("D3_fraccion_multi_transferencia") is not None
     else "no ejecutado"),
    "compute_canton_metrics.py (sobre events_sample.json)")
row("canton", "Canton Coin (Amulet)", "E1", "global", 1, "fraccion", None,
    "computada", "verdicts y traffic son publicos via el espejo api.cantonnodes.com", "collect_canton.py", modo="no_aplica")
row("canton", "USDCx (Circle xReserve, CIP-56)", "E1", "global", 0, "fraccion", 10400,
    "parcialmente_derivada", "USDCx esta confirmado vivo en mainnet por fuente externa (canton.network/blog, circle.com/blog, CIP-56), pero la busqueda propia de template_id tipo Holding/Token en 10.400 eventos reales sobre DOS ventanas distintas (una de burst de medianoche, otra de 8 min en horario habil) no encontro ninguno -- todos los templates visibles son nativos de Amulet/Splice. Esto es evidencia mas fuerte que antes de que, si USDCx circula, su actividad visible es muy escasa frente a la nativa, o bien nunca deja `update` visible (solo verdict) -- consistente con D7 del plan: si es privada, E1=0 para ese activo es precisamente el resultado esperado, no una falla de busqueda.", "collect_canton.py + compute_canton_metrics.py (busqueda de template_families, n=10.400 eventos)",
    modo="no_aplica")

with open(f"{RES}/metrics.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"metrics.csv escrito con {len(rows)} filas")

# ---------------- limitaciones.md ----------------
no_comp = [r for r in rows if r["estado"] in ("no_computable",)]
parcial = [r for r in rows if r["estado"] == "parcialmente_derivada"]

tiempo_real_rows = [r for r in rows if r["modo_dato"] == "tiempo_real"]
historico_rows = [r for r in rows if r["modo_dato"] == "historico"]

with open(f"{RES}/limitaciones.md", "w", encoding="utf-8") as f:
    f.write("# Limitaciones — generado desde metrics.csv\n\n")
    f.write(f"Fecha: {datetime.now(timezone.utc).isoformat()}\n\n")
    f.write("Esta es una pasada de verificacion/implementacion con muestras reducidas, no la ")
    f.write("recoleccion completa de 14 dias (W_H) que especifica el plan. Cada entrada abajo ")
    f.write("es una metrica que NO se completo con un valor pleno, junto con la razon exacta.\n\n")
    f.write(
        f"**Modo de obtencion de los datos** (columna `modo_dato` de metrics.csv): "
        f"{len(historico_rows)} filas se calculan sobre datos historicos (bloques/eventos/estado ya "
        f"producidos por la red, consultados con una peticion puntual reproducible -- ventana W_H del "
        f"plan); {len(tiempo_real_rows)} filas requieren sondeo en vivo mientras ocurre el evento "
        f"(ventana W_L: solo B2 en Tempo y Aptos); el resto son transversales/degeneradas por diseno "
        f"y no tienen ventana temporal (E1, D1 en Canton, C1 en Canton).\n\n"
    )
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
        "Aptos: oraculo Pyth (APT/USD) descontinuado el 2026-08-26 -> RESUELTO como parcialmente_derivada: el ID del feed se obtuvo de hermes.pyth.network (API en vivo de Pyth) y se verifico contra la tabla on-chain (self-consistente); el precio esta congelado en 0.55654017 USD/APT (timestamp on-chain 2026-08-26T16:08:48Z) y se aplica como fijo a toda la muestra -- desviacion explicita prevista por el plan (Sec.4.2 A-2), no una limitacion abierta",
        "Aptos: limite de gas de bloque -> RESUELTO: ExecutionConfig (variante V7, ComplexLimitV1) decodificado contra el layout exacto de aptos-core (types/src/on_chain_config/execution_config.rs), 79/79 bytes consumidos. A3/B3 parcialmente_derivada con la simplificacion declarada de no ponderar execution/io gas por separado",
        "Aptos: B2 no es reconstruible con datos historicos por definicion del plan (D1) -> requiere sondeo en vivo (W_L) de al menos 72h en dos fullnodes independientes, no ejecutado en esta pasada",
        "Canton: los Scan de Super Validador individuales bloquean acceso publico directo (403/RBAC); solo se pudo verificar un espejo de tercero (api.cantonnodes.com) -> no se cumplio el control de concordancia entre dos SV independientes (C-7)",
        "Canton: B3 (H_cfg) se calcula sobre baseRateTrafficLimits, que es la asignacion GRATUITA por miembro antes de comprar trafico extra, no el techo agregado del sincronizador -> probablemente subestima la capacidad real; se reporta parcialmente_derivada con esa advertencia explicita, no computada",
    ],
    "segundo_proveedor_por_red": "NO CUMPLIDO en esta pasada para ninguna red -- solo se uso un proveedor por red",
    "resumen_modo_dato": {
        "historico_W_H": len(historico_rows),
        "tiempo_real_W_L": len(tiempo_real_rows),
        "no_aplica_transversal_o_degenerada": len(rows) - len(historico_rows) - len(tiempo_real_rows),
        "nota": "historico = consulta reproducible sobre bloques/eventos/estado ya producidos por la red (aunque la peticion se haga en vivo contra un nodo, lo que se mide ya ocurrio); tiempo_real = requiere sondeo continuo mientras el evento ocurre (solo B2 en Tempo y Aptos, via scripts/poll_finality.py); no_aplica = transversal o degenerada por arquitectura, sin ventana temporal.",
    },
    "codigo": {
        "collect_tempo.py": "resultados/raw/tempo",
        "collect_aptos.py": "resultados/raw/aptos",
        "collect_canton.py": "resultados/raw/canton",
        "compute_tempo_metrics.py": "resultados/tempo_metrics.json",
        "compute_aptos_metrics.py": "resultados/aptos_metrics.json",
        "compute_canton_metrics.py": "resultados/canton_metrics.json",
    },
}
with open(f"{RES}/run_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, default=str)

print("run_manifest.json escrito")
