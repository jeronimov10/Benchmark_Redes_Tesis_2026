import json
import math
import statistics as st
from collections import Counter, defaultdict

RAW = "resultados/raw/tempo"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# event TransferWithMemo(address indexed from, address indexed to, uint256 amount,
# bytes32 indexed memo) -- interfaz ITIP20 confirmada leyendo el codigo fuente publico
# (github.com/tempoxyz/tempo, crates/contracts/src/precompiles/tip20.rs). El topic0
# es keccak256("TransferWithMemo(address,address,uint256,bytes32)"), calculado aqui,
# no copiado de documentacion. D2 se mide sobre logs ya descargados (historico).
MEMO_TOPIC = "0x57bc7354aa85aed339e000bccffabbc529466af35f0772c8f8ee1145927de7f0"


def load(name):
    with open(f"{RAW}/{name}") as f:
        return json.load(f)


def herfindahl(counter):
    total = sum(counter.values())
    if total == 0:
        return None
    return sum((c / total) ** 2 for c in counter.values())


def main():
    blocks = load("blocks_sample.json")
    receipts = load("receipts_sample.json")
    fee_meta = load("fee_token_meta.json")

    results = {}
    n_blocks = len(blocks)
    results["n_blocks"] = n_blocks

    # --- B1: latencia de inclusion (proxy = delta entre timestamps de bloques consecutivos) ---
    ts = sorted(int(b["timestamp"], 16) + int(b.get("timestampMillisPart", "0x0"), 16) / 1000.0 for b in blocks)
    deltas = [b - a for a, b in zip(ts, ts[1:])]
    deltas.sort()
    if deltas:
        p95_idx = min(len(deltas) - 1, math.ceil(0.95 * len(deltas)) - 1)
        results["B1_cadencia_mediana_s"] = st.median(deltas)
        results["B1_cadencia_p95_s"] = deltas[p95_idx]
        results["B1_n"] = len(deltas)

    # --- C3: continuidad, 1 - fraccion de tiempo en huecos > 10x cadencia mediana ---
    # Reconstruible con datos historicos (los mismos bloques ya descargados para B1):
    # no requiere sondeo en vivo, a diferencia de B2.
    if deltas:
        med_c3 = st.median(deltas)
        umbral_c3 = 10 * med_c3
        total_span = ts[-1] - ts[0]
        gap_time = sum(d for d in deltas if d > umbral_c3)
        results["C3_fraccion_continuidad"] = (1 - gap_time / total_span) if total_span else None
        results["C3_n"] = len(deltas)
        results["C3_umbral_s"] = umbral_c3

    # --- C1: Herfindahl sobre produccion de bloques (proposer real, no 'miner') ---
    proposers = Counter()
    for b in blocks:
        cc = b.get("consensusContext") or {}
        p = cc.get("proposer")
        if p:
            proposers[p] += 1
    results["C1_herfindahl_produccion"] = herfindahl(proposers)
    results["C1_n_proposers_distintos"] = len(proposers)
    results["C1_n_bloques"] = sum(proposers.values())

    # --- occupancy por bloque (para A3) ---
    occ_by_number = {}
    for b in blocks:
        num = int(b["number"], 16)
        gas_used = int(b["gasUsed"], 16)
        gas_limit = int(b["gasLimit"], 16)
        occ_by_number[num] = gas_used / gas_limit if gas_limit else 0.0

    # --- receipts: costo, exito, patrocinio, transfers ---
    costs_usd = []
    fails = 0
    sponsored = 0
    n_receipts = 0
    tx_transfer_tokens = defaultdict(set)  # tx_hash -> set(token_addr)
    tx_transfer_count = Counter()
    token_transfer_count = Counter()
    tx_con_memo = set()
    occ_cost_pairs = []

    for r in receipts:
        if r is None:
            continue
        n_receipts += 1
        status = r.get("status")
        if status not in ("0x1",):
            fails += 1
        gas_used = int(r["gasUsed"], 16)
        gas_price = int(r["effectiveGasPrice"], 16)
        fee_token = r.get("feeToken")
        fee_payer = r.get("feePayer")
        raw_cost = gas_used * gas_price
        # Supuesto EVM estandar: gasPrice/effectiveGasPrice esta siempre en escala
        # fija de 18 decimales ("wei"), independiente de los decimales propios
        # del feeToken (aqui 6). Se documenta como supuesto en limitaciones.md:
        # no se pudo confirmar contra un TIP publicado, se infirio por orden de
        # magnitud plausible (fee ~0.00003 USD, coherente con una cadena de pagos
        # de bajisimo costo) y por convencion universal EVM.
        if fee_token in fee_meta:
            cost_usd = raw_cost / 1e18
            costs_usd.append(cost_usd)
            block_num = int(r["blockNumber"], 16)
            if block_num in occ_by_number and cost_usd > 0:
                occ_cost_pairs.append((occ_by_number[block_num], cost_usd))
        if fee_payer:
            sponsored += 1
        h = r["transactionHash"]
        for log in r.get("logs", []):
            if log["topics"] and log["topics"][0].lower() == TRANSFER_TOPIC:
                tx_transfer_tokens[h].add(log["address"])
                tx_transfer_count[h] += 1
                token_transfer_count[log["address"]] += 1
            if log["topics"] and log["topics"][0].lower() == MEMO_TOPIC:
                tx_con_memo.add(h)

    results["n_receipts"] = n_receipts
    results["C4_tasa_fallo"] = fails / n_receipts if n_receipts else None
    results["C4_n"] = n_receipts
    results["D1_fraccion_feePayer_distinto"] = sponsored / n_receipts if n_receipts else None
    results["D1_n"] = n_receipts

    if costs_usd:
        costs_sorted = sorted(costs_usd)
        p95_idx = min(len(costs_sorted) - 1, math.ceil(0.95 * len(costs_sorted)) - 1)
        results["A1_costo_mediano_usd"] = st.median(costs_sorted)
        results["A2_costo_p95_usd"] = costs_sorted[p95_idx]
        results["A_n"] = len(costs_sorted)
        for ticket, label in [(3.8, "comercio_barrio"), (40, "p2p_promedio"), (300, "remesa")]:
            results[f"A1_fraccion_{label}"] = st.median(costs_sorted) / ticket

    # --- A3: regresion ln(costo) ~ ocupacion ---
    if len(occ_cost_pairs) >= 5:
        xs = [p[0] for p in occ_cost_pairs]
        ys = [math.log(p[1]) for p in occ_cost_pairs]
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        var = sum((x - mean_x) ** 2 for x in xs)
        beta = cov / var if var else None
        results["A3_beta_ocupacion_global"] = beta
        results["A3_n"] = n
    else:
        results["A3_beta_ocupacion_global"] = None
        results["A3_n"] = len(occ_cost_pairs)

    # --- D3: multi-transferencia / multi-activo ---
    multi_transfer = sum(1 for c in tx_transfer_count.values() if c > 1)
    multi_asset = sum(1 for toks in tx_transfer_tokens.values() if len(toks) > 1)
    n_tx_with_transfer = len(tx_transfer_count)
    results["D3_n_tx_con_transferencia"] = n_tx_with_transfer
    results["D3_fraccion_multi_transferencia"] = (
        multi_transfer / n_tx_with_transfer if n_tx_with_transfer else None
    )
    results["D3_fraccion_multi_activo"] = multi_asset / n_tx_with_transfer if n_tx_with_transfer else None

    # --- D2: memo de 32 bytes via evento TransferWithMemo (ver MEMO_TOPIC arriba) ---
    tx_con_memo_en_muestra = tx_con_memo & set(tx_transfer_count.keys())
    results["D2_fraccion_con_memo"] = (
        len(tx_con_memo_en_muestra) / n_tx_with_transfer if n_tx_with_transfer else None
    )
    results["D2_n"] = n_tx_with_transfer

    # --- inventario de activos (T-5, informativo) ---
    results["inventario_tokens_por_conteo_transferencias"] = dict(token_transfer_count.most_common())

    # --- C5: actualizaciones de red (TIPs) activadas dentro de la ventana muestreada.
    # Fuente admisible: RPC en vivo tempo_forkSchedule (extension tempo_*, confirmada
    # leyendo crates/node/src/rpc/fork_schedule.rs), NO el changelog/TIPs de GitHub
    # -- eso si violaria la regla de oro (documentacion, no consulta al registro).
    # activationTime es un timestamp unix real que el nodo expone para su propio
    # fork schedule, comparable directamente contra la ventana de bloques ya
    # descargada (ts_min/ts_max de esta misma muestra).
    try:
        fork_sched = load("fork_schedule.json")
        forks = fork_sched["result"]["schedule"]
        ts_min, ts_max = ts[0], ts[-1]
        en_ventana = [
            f for f in forks
            if f["name"] != "T0" and ts_min <= f["activationTime"] <= ts_max
        ]
        results["C5_actualizaciones_en_ventana"] = len(en_ventana)
        results["C5_detalle"] = [f["name"] for f in en_ventana]
        results["C5_ventana_ts"] = [ts_min, ts_max]
        results["C5_fork_activo_actual"] = fork_sched["result"]["active"]
    except (FileNotFoundError, KeyError):
        pass

    # --- C1b: validadores activos via ValidatorConfigV2 (T-2 resuelto) ---
    try:
        vc = load("validator_config.json")
        n_val = vc.get("n_activos")
        if n_val:
            results["C1b_herfindahl_peso_consenso"] = 1 / n_val
            results["C1b_n_validadores_activos"] = n_val
            results["C1b_direccion_precompilado"] = vc.get("validator_config_v2_address")
    except FileNotFoundError:
        pass

    print(json.dumps(results, indent=2, default=str))
    with open(f"{RAW}/../tempo_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
