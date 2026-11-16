"""Calcula las metricas de Aptos desde los datos crudos de resultados/raw/aptos."""

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


class BcsReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def u8(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u32(self):
        v = int.from_bytes(self.data[self.pos:self.pos + 4], "little")
        self.pos += 4
        return v

    def u64(self):
        v = int.from_bytes(self.data[self.pos:self.pos + 8], "little")
        self.pos += 8
        return v

    def boolean(self):
        return bool(self.u8())

    def option_u64(self):
        return self.u64() if self.u8() != 0 else None


def decode_execution_config(hex_blob):
    data = bytes.fromhex(hex_blob[2:] if hex_blob.startswith("0x") else hex_blob)
    r = BcsReader(data)

    def shuffler():
        v = r.u8()
        if v == 0:
            return {"type": "NoShuffling"}
        if v in (1, 2):
            return {"type": v, "param": r.u32()}
        if v == 3:
            return {"type": "DeprecatedFairness"}
        if v in (4, 5):
            return {
                "type": v,
                "sender_spread_factor": r.u64(),
                "platform_use_case_spread_factor": r.u64(),
                "user_use_case_spread_factor": r.u64(),
            }
        raise ValueError(f"TransactionShufflerType: variante {v} no reconocida")

    def block_gas_limit_type():
        v = r.u8()
        if v == 0:
            return {"type": "NoLimit", "effective_block_gas_limit": None}
        if v == 1:
            return {"type": "Limit", "effective_block_gas_limit": r.u64()}
        if v == 2:
            eff = r.u64()
            exec_mult = r.u64()
            io_mult = r.u64()
            conflict_window = r.u32()
            granular = r.boolean()
            module_conflict = r.boolean()
            output_limit = r.option_u64()
            include_size = r.boolean()
            add_outcome = r.boolean()
            return {
                "type": "ComplexLimitV1",
                "effective_block_gas_limit": eff,
                "execution_gas_effective_multiplier": exec_mult,
                "io_gas_effective_multiplier": io_mult,
                "conflict_penalty_window": conflict_window,
                "use_granular_resource_group_conflicts": granular,
                "use_module_publishing_block_conflict": module_conflict,
                "block_output_limit": output_limit,
                "include_user_txn_size_in_block_output": include_size,
                "add_block_limit_outcome_onchain": add_outcome,
            }
        raise ValueError(f"BlockGasLimitType: variante {v} no reconocida")

    variant = r.u8()
    out = {"onchain_execution_config_variant": variant}

    out["transaction_shuffler_type"] = shuffler()
    if variant in (0,):
        out["block_gas_limit_type"] = {"type": "NoLimit", "effective_block_gas_limit": None}
        return out
    if variant in (1, 2):
        out["block_gas_limit_type"] = {"type": "Option<u64>", "effective_block_gas_limit": r.option_u64()}
        if variant == 2:
            out["transaction_deduper_type"] = r.u8()
        return out
    if variant in (4, 5, 6, 7):
        out["block_gas_limit_type"] = block_gas_limit_type()
        if variant >= 5:
            out["enable_per_block_gas_limit"] = r.boolean()
        out["transaction_deduper_type"] = r.u8()
        if variant >= 6:
            out["gas_price_to_burn"] = r.u64()
        if variant >= 7:
            out["persisted_auxiliary_info_version"] = r.u8()
        return out
    raise ValueError(f"OnChainExecutionConfig: variante {variant} no reconocida (Missing=3 no deberia aparecer on-chain)")


def main():
    blocks = load("blocks_sample.json")
    vs = load("validator_set.json")

    results = {"n_blocks": len(blocks)}

    ts = sorted(int(b["block_timestamp"]) for b in blocks)
    deltas_s = [(b - a) / 1e6 for a, b in zip(ts, ts[1:])]
    deltas_sorted = sorted(deltas_s)
    if deltas_sorted:
        p95_idx = min(len(deltas_sorted) - 1, math.ceil(0.95 * len(deltas_sorted)) - 1)
        results["B1_cadencia_mediana_s"] = st.median(deltas_sorted)
        results["B1_cadencia_p95_s"] = deltas_sorted[p95_idx]
        results["B1_n"] = len(deltas_sorted)

    if deltas_sorted:
        med = st.median(deltas_sorted)
        umbral = 10 * med
        tiempo_total = ts[-1] - ts[0]
        tiempo_en_huecos = sum(d for d in deltas_s if d * 1e6 > umbral * 1e6) if med else 0
        tiempo_en_huecos = sum(d for d in deltas_s if d > umbral)
        frac_continuidad = 1 - (tiempo_en_huecos / (tiempo_total / 1e6)) if tiempo_total else None
        results["C3_fraccion_continuidad"] = frac_continuidad
        results["C3_n"] = len(deltas_s)

    proposers = Counter()
    for b in blocks:
        for tx in b.get("transactions", []):
            if tx.get("type") == "block_metadata_transaction":
                proposers[tx["proposer"]] += 1
    results["C1_herfindahl_produccion"] = herfindahl(proposers)
    results["C1_n_proposers_distintos"] = len(proposers)
    results["C1_n_bloques_con_metadata"] = sum(proposers.values())

    weights = [int(v["voting_power"]) for v in vs["data"]["active_validators"]]
    weights_desc = sorted(weights, reverse=True)
    results["C1b_herfindahl_peso_consenso"] = herfindahl(weights)
    results["C1b_n_validadores"] = len(weights)
    results["C2_operadores_sobre_50pct_por_peso"] = min_operators_over_50(weights_desc)
    proposer_weights_desc = sorted(proposers.values(), reverse=True)
    results["C2_operadores_sobre_50pct_por_produccion"] = min_operators_over_50(proposer_weights_desc)

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

    try:
        pyth = load("pyth_apt_usd_price.json")
        pf = pyth["price_info"]["price_feed"]["price"]
        expo = pf["expo"]
        precio_usd = int(pf["price"]["magnitude"]) / (10 ** int(expo["magnitude"]))
        if pf["price"]["negative"]:
            precio_usd = -precio_usd
        results["A1A2_precio_apt_usd_congelado"] = precio_usd
        results["A1A2_precio_timestamp_unix"] = int(pf["timestamp"])

        costos_usd = []
        for b in blocks:
            for tx in b.get("transactions", []):
                if tx.get("type") != "user_transaction":
                    continue
                gu = tx.get("gas_used")
                gp = tx.get("gas_unit_price")
                if gu is None or gp is None:
                    continue
                costo_apt = int(gu) * int(gp) / 1e8
                costos_usd.append(costo_apt * precio_usd)
        if costos_usd:
            costos_sorted = sorted(costos_usd)
            p95_idx = min(len(costos_sorted) - 1, math.ceil(0.95 * len(costos_sorted)) - 1)
            results["A1_costo_mediano_usd"] = st.median(costos_sorted)
            results["A2_costo_p95_usd"] = costos_sorted[p95_idx]
            results["A_n"] = len(costos_sorted)
    except FileNotFoundError:
        pass

    try:
        exec_cfg_raw = load("execution_config.json")
        decoded = decode_execution_config(exec_cfg_raw["data"]["config"])
        results["execution_config_decodificado"] = decoded
        block_gas_limit = decoded["block_gas_limit_type"].get("effective_block_gas_limit")
        results["B3_block_gas_limit"] = block_gas_limit

        if block_gas_limit and "A1_costo_mediano_usd" in results:
            gas_used_por_tx = []
            occ_cost_pairs = []
            gas_por_bloque = {}
            for b in blocks:
                total_gas_bloque = 0
                for tx in b.get("transactions", []):
                    if tx.get("type") == "user_transaction" and tx.get("gas_used"):
                        total_gas_bloque += int(tx["gas_used"])
                gas_por_bloque[b["block_height"]] = total_gas_bloque

            for b in blocks:
                h = b["block_height"]
                occ = gas_por_bloque.get(h, 0) / block_gas_limit
                for tx in b.get("transactions", []):
                    if tx.get("type") != "user_transaction":
                        continue
                    gu, gp = tx.get("gas_used"), tx.get("gas_unit_price")
                    if gu is None or gp is None:
                        continue
                    gas_used_por_tx.append(int(gu))
                    costo_usd = int(gu) * int(gp) / 1e8 * results["A1A2_precio_apt_usd_congelado"]
                    if costo_usd > 0:
                        occ_cost_pairs.append((occ, costo_usd))

            if gas_used_por_tx:
                gas_mediana = sorted(gas_used_por_tx)[len(gas_used_por_tx) // 2]
                cadencia_mediana = results.get("B1_cadencia_mediana_s")
                if cadencia_mediana:
                    tps_cfg = (block_gas_limit / gas_mediana) / cadencia_mediana
                    results["B3_tps_cfg"] = tps_cfg
                    results["B3_h_cfg"] = tps_cfg / 48.0
                    results["B3_gas_mediana_tx"] = gas_mediana
                    results["B3_n"] = len(gas_used_por_tx)

            if len(occ_cost_pairs) >= 5:
                xs = [p[0] for p in occ_cost_pairs]
                ys = [math.log(p[1]) for p in occ_cost_pairs]
                n = len(xs)
                mean_x = sum(xs) / n
                mean_y = sum(ys) / n
                cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
                var = sum((x - mean_x) ** 2 for x in xs)
                results["A3_beta_ocupacion_global"] = cov / var if var else None
                results["A3_n"] = n
    except (FileNotFoundError, KeyError, ValueError) as e:
        results["execution_config_error"] = str(e)

    PUBLISH_FUNCS = {
        "0x1::code::publish_package_txn",
        "0x1::code::publish_package",
        "0x1::code::freeze_code_object",
    }
    publicaciones = 0
    for b in blocks:
        for tx in b.get("transactions", []):
            if tx.get("type") != "user_transaction":
                continue
            pl = tx.get("payload") or {}
            fn = pl.get("function")
            if fn in PUBLISH_FUNCS or pl.get("type") == "module_bundle_payload":
                publicaciones += 1
    results["C5_publicaciones_modulo"] = publicaciones
    results["C5_n"] = total_tx

    try:
        store_to_asset = load("fa_store_to_asset.json")
        n_tx_fa = 0
        multi_transfer = 0
        multi_asset = 0
        for b in blocks:
            for tx in b.get("transactions", []):
                if tx.get("type") != "user_transaction":
                    continue
                fa_events = [
                    e for e in tx.get("events", [])
                    if e.get("type") in ("0x1::fungible_asset::Deposit", "0x1::fungible_asset::Withdraw")
                ]
                if not fa_events:
                    continue
                n_tx_fa += 1
                if len(fa_events) > 1:
                    multi_transfer += 1
                assets = {store_to_asset.get(e.get("data", {}).get("store")) for e in fa_events}
                assets.discard(None)
                if len(assets) > 1:
                    multi_asset += 1
        if n_tx_fa:
            results["D3_fraccion_multi_transferencia"] = multi_transfer / n_tx_fa
            results["D3_fraccion_multi_activo"] = multi_asset / n_tx_fa
            results["D3_n_tx_con_transferencia"] = n_tx_fa
    except FileNotFoundError:
        pass

    print(json.dumps(results, indent=2, default=str))
    with open(f"{RAW}/../aptos_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
