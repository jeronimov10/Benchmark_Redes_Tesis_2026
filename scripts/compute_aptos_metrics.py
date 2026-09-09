import json
import math
import statistics as st
from collections import Counter

RAW = "resultados/raw/aptos"


def load(name):
    with open(f"{RAW}/{name}") as f:
        return json.load(f)


def herfindahl(counter_or_weights):
    if isinstance(counter_or_weights, dict):
        vals = list(counter_or_weights.values())
    else:
        vals = list(counter_or_weights)
    total = sum(vals)
    if total == 0:
        return None
    return sum((v / total) ** 2 for v in vals)


def min_operators_over_50(weights_desc):
    total = sum(weights_desc)
    if total == 0:
        return None
    cum = 0
    for i, w in enumerate(weights_desc, start=1):
        cum += w
        if cum / total > 0.5:
            return i
    return len(weights_desc)


def main():
    blocks = load("blocks_sample.json")
    vs = load("validator_set.json")

    results = {"n_blocks": len(blocks)}

    # --- B1: latencia de inclusion (delta entre timestamps de bloque, microsegundos) ---
    ts = sorted(int(b["block_timestamp"]) for b in blocks)
    deltas_s = [(b - a) / 1e6 for a, b in zip(ts, ts[1:])]
    deltas_sorted = sorted(deltas_s)
    if deltas_sorted:
        p95_idx = min(len(deltas_sorted) - 1, math.ceil(0.95 * len(deltas_sorted)) - 1)
        results["B1_cadencia_mediana_s"] = st.median(deltas_sorted)
        results["B1_cadencia_p95_s"] = deltas_sorted[p95_idx]
        results["B1_n"] = len(deltas_sorted)

    # --- C3: continuidad, huecos > 10x cadencia mediana ---
    if deltas_sorted:
        med = st.median(deltas_sorted)
        umbral = 10 * med
        tiempo_total = ts[-1] - ts[0]
        tiempo_en_huecos = sum(d for d in deltas_s if d * 1e6 > umbral * 1e6) if med else 0
        # recompute directly in seconds
        tiempo_en_huecos = sum(d for d in deltas_s if d > umbral)
        frac_continuidad = 1 - (tiempo_en_huecos / (tiempo_total / 1e6)) if tiempo_total else None
        results["C3_fraccion_continuidad"] = frac_continuidad
        results["C3_n"] = len(deltas_s)

    # --- C1: Herfindahl produccion de bloques ---
    proposers = Counter()
    for b in blocks:
        for tx in b.get("transactions", []):
            if tx.get("type") == "block_metadata_transaction":
                proposers[tx["proposer"]] += 1
    results["C1_herfindahl_produccion"] = herfindahl(proposers)
    results["C1_n_proposers_distintos"] = len(proposers)
    results["C1_n_bloques_con_metadata"] = sum(proposers.values())

    # --- C1b: Herfindahl peso de consenso (voting_power) ---
    weights = [int(v["voting_power"]) for v in vs["data"]["active_validators"]]
    weights_desc = sorted(weights, reverse=True)
    results["C1b_herfindahl_peso_consenso"] = herfindahl(weights)
    results["C1b_n_validadores"] = len(weights)
    results["C2_operadores_sobre_50pct_por_peso"] = min_operators_over_50(weights_desc)
    proposer_weights_desc = sorted(proposers.values(), reverse=True)
    results["C2_operadores_sobre_50pct_por_produccion"] = min_operators_over_50(proposer_weights_desc)

    # --- C4: tasa de fallo sobre user_transactions ---
    total_tx = 0
    fails = 0
    sponsored = 0
    for b in blocks:
        for tx in b.get("transactions", []):
            if tx.get("type") == "user_transaction":
                total_tx += 1
                if not tx.get("success", True):
                    fails += 1
                sig = tx.get("signature") or {}
                if sig.get("type") == "fee_payer_signature" or "fee_payer" in sig:
                    sponsored += 1
    results["C4_tasa_fallo"] = fails / total_tx if total_tx else None
    results["C4_n"] = total_tx
    results["D1_fraccion_fee_payer_distinto"] = sponsored / total_tx if total_tx else None
    results["D1_n"] = total_tx

    print(json.dumps(results, indent=2, default=str))
    with open(f"{RAW}/../aptos_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
