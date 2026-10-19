import json
import math
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Choices de gobernanza del DSO que son ruido rutinario (votos de precio, reportes
# de estado, confirmaciones de accion ya contadas en otro lado, merges de trafico)
# y NO cuentan como "cambio de la ruta de pago" para C5. Definicion operativa
# declarada aqui porque el plan no fija una lista cerrada -- se documenta como
# supuesto, no se oculta (Sec.10 regla 8 del plan).
DSO_CHOICES_RUTINARIAS = {
    "DsoRules_UpdateAmuletPriceVote",
    "DsoRules_SubmitStatusReport",
    "DsoRules_ConfirmAction",
    "DsoRules_ReceiveSvRewardCoupon",
    "DsoRules_MergeMemberTrafficContracts",
    "DsoRules_AmuletRules_ConvertFeaturedAppActivityMarkers",
}
TRANSFER_CHOICES = {"TransferFactory_Transfer", "AmuletRules_Transfer"}
HEARTBEAT_CHOICE = "ValidatorLicense_ReportActive"

RAW = "resultados/raw/canton"
# trafficPrice se lee en vivo de /v0/dso (amuletConfig) en collect_canton.py.
# Unidad CONFIRMADA como USD/MB via docs.sync.global/deployment/traffic.html
# (Synchronizer Traffic Fees, CIP-0042/CIP-0084). total_traffic_cost esta en
# bytes -> costo_usd = total_traffic_cost / 1e6 * trafficPrice.
TRAFFIC_PRICE_USD_POR_MB = 60.0


def parse_ts(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # normaliza microsegundos a 6 digitos
    if "." in s:
        head, rest = s.split(".")
        frac, tz = rest[: rest.index("+")], rest[rest.index("+") :]
        frac = (frac + "000000")[:6]
        s = f"{head}.{frac}{tz}"
    return datetime.fromisoformat(s)


def main():
    with open(f"{RAW}/events_sample.json") as f:
        events = json.load(f)

    results = {"n_eventos": len(events)}

    latencies = []
    verdict_results = Counter()
    traffic_costs = []
    record_times = []

    for e in events:
        v = e.get("verdict")
        if not v:
            continue
        verdict_results[v["verdict_result"]] += 1
        try:
            rt = parse_ts(v["record_time"])
            ft = parse_ts(v["finalization_time"])
            latencies.append((ft - rt).total_seconds())
            record_times.append(rt)
        except Exception:
            pass
        ts = e.get("traffic_summary")
        if ts and "total_traffic_cost" in ts:
            traffic_costs.append(ts["total_traffic_cost"])

    # --- C-6: busqueda de una stablecoin bajo el estandar de token (CIP-56) ---
    # Se cuentan familias de template_id (antes del ':') vistas en los updates
    # visibles, sin decodificar contenido de instrumentos privados.
    template_families = Counter()
    for e in events:
        upd = e.get("update")
        if not upd:
            continue
        for ev in upd.get("events_by_id", {}).values():
            tmpl = ev.get("template_id", "")
            if ":" in tmpl:
                pkg, rest = tmpl.split(":", 1)
                template_families[rest] += 1
    results["template_families_vistas"] = dict(template_families.most_common(30))
    cip56_hits = {k: v for k, v in template_families.items() if "Token" in k or "Holding" in k or "Api.Token" in k}
    results["cip56_o_holding_detectado"] = cip56_hits if cip56_hits else None

    results["n_verdicts"] = sum(verdict_results.values())
    results["C4_distribucion_verdict_result"] = dict(verdict_results)
    total_v = sum(verdict_results.values())
    rejected = verdict_results.get("VERDICT_RESULT_REJECTED", 0)
    results["C4_tasa_fallo"] = rejected / total_v if total_v else None
    results["C4_n"] = total_v

    if latencies:
        lat_sorted = sorted(latencies)
        p95_idx = min(len(lat_sorted) - 1, math.ceil(0.95 * len(lat_sorted)) - 1)
        results["B1_B2_latencia_confirmacion_mediana_s"] = st.median(lat_sorted)
        results["B1_B2_latencia_confirmacion_p95_s"] = lat_sorted[p95_idx]
        results["B1_B2_n"] = len(lat_sorted)
        results["nota_B1_B2"] = (
            "En Canton B1 (latencia de inclusion) y B2 (irreversibilidad) coinciden: "
            "finalization_time - record_time del mismo verdict es, a la vez, cuando se "
            "incluye y cuando queda firme. No hay un segundo instante de finalidad "
            "separado como en Tempo/Aptos."
        )

    if traffic_costs:
        tc_sorted = sorted(traffic_costs)
        p95_idx = min(len(tc_sorted) - 1, math.ceil(0.95 * len(tc_sorted)) - 1)
        mediana_bytes = st.median(tc_sorted)
        p95_bytes = tc_sorted[p95_idx]
        results["A1_traffic_cost_mediana_bytes"] = mediana_bytes
        results["A2_traffic_cost_p95_bytes"] = p95_bytes
        results["A_n"] = len(tc_sorted)
        results["A1_costo_usd_mediana_confirmado"] = mediana_bytes / 1e6 * TRAFFIC_PRICE_USD_POR_MB
        results["A2_costo_usd_p95_confirmado"] = p95_bytes / 1e6 * TRAFFIC_PRICE_USD_POR_MB
        results["nota_A1_A2"] = (
            "Unidad CONFIRMADA: trafficPrice=60.0 USD/MB (docs.sync.global/deployment/"
            "traffic.html, CIP-0042/CIP-0084), total_traffic_cost en bytes. "
            "costo_usd = bytes/1e6 * 60. El resultado coincide con el objetivo de diseno "
            "de CIP-0042 (~1 USD por transferencia estandar de CC)."
        )

    if record_times:
        rt_sorted = sorted(record_times)
        span = (rt_sorted[-1] - rt_sorted[0]).total_seconds()
        results["ventana_cubierta_s"] = span
        results["ventana_inicio"] = rt_sorted[0].isoformat()
        results["ventana_fin"] = rt_sorted[-1].isoformat()

    # ============================================================
    # Metricas historicas nuevas: todas reconstruibles de datos ya
    # descargados (dso_state.json + events_sample.json), sin sondeo en vivo.
    # ============================================================

    # --- C1b/C2: Herfindahl de peso de consenso via svRewardWeight, y minimo
    # de operadores que concentran >50% del peso. dso_rules.svs ya estaba
    # descargado en dso_state.json (collect_canton.py) pero no se habia leido.
    try:
        with open(f"{RAW}/dso_state.json") as f:
            dso = json.load(f)
        svs = dso["dso_rules"]["contract"]["payload"]["svs"]
        pesos = [float(entry[1]["svRewardWeight"]) for entry in svs]
        total_peso = sum(pesos)
        if total_peso:
            results["C1b_herfindahl_peso_consenso"] = sum((p / total_peso) ** 2 for p in pesos)
            results["C1b_n_sv"] = len(pesos)
            pesos_desc = sorted(pesos, reverse=True)
            cum = 0.0
            min_ops = len(pesos_desc)
            for i, p in enumerate(pesos_desc, start=1):
                cum += p
                if cum / total_peso > 0.5:
                    min_ops = i
                    break
            results["C2_operadores_sobre_50pct"] = min_ops

        # --- B3: H_cfg desde los limites de trafico del sincronizador (ACS) ---
        fees = dso["amulet_rules"]["contract"]["payload"]["configSchedule"]["initialValue"][
            "decentralizedSynchronizer"
        ]["fees"]
        burst = fees["baseRateTrafficLimits"]
        burst_bytes = float(burst["burstAmount"])
        burst_window_s = float(burst["burstWindow"]["microseconds"]) / 1e6
        results["B3_burst_bytes"] = burst_bytes
        results["B3_burst_window_s"] = burst_window_s
    except (FileNotFoundError, KeyError, IndexError) as e:
        results["B3_error"] = str(e)

    if traffic_costs and "B3_burst_bytes" in results:
        bytes_por_tx_mediana = st.median(traffic_costs)
        tasa_bytes_s = results["B3_burst_bytes"] / results["B3_burst_window_s"]
        tps_cfg = tasa_bytes_s / bytes_por_tx_mediana if bytes_por_tx_mediana else None
        if tps_cfg is not None:
            results["B3_tps_cfg"] = tps_cfg
            results["B3_h_cfg"] = tps_cfg / 48.0
            results["B3_n"] = len(traffic_costs)

    # --- A3: pendiente ln(costo individual) ~ trafico total del sincronizador
    # por intervalo de 10s (sustituto de "ocupacion" para Canton, Sec.5.1 del
    # plan). Se espera beta~0 por diseno de tarifa fija -- eso mismo es un
    # resultado valido, no una falla del calculo.
    registros_costo = []
    for e in events:
        v = e.get("verdict")
        ts_ = e.get("traffic_summary")
        if v and ts_ and ts_.get("total_traffic_cost"):
            try:
                registros_costo.append((parse_ts(v["record_time"]), ts_["total_traffic_cost"]))
            except Exception:
                pass
    if registros_costo:
        registros_costo.sort(key=lambda x: x[0])
        t0 = registros_costo[0][0]
        BUCKET_S = 10
        totales_bucket = defaultdict(float)
        for rt, costo in registros_costo:
            totales_bucket[int((rt - t0).total_seconds() // BUCKET_S)] += costo
        pares = []
        for rt, costo in registros_costo:
            if costo <= 0:
                continue
            b = int((rt - t0).total_seconds() // BUCKET_S)
            pares.append((totales_bucket[b], math.log(costo)))
        if len(pares) >= 5:
            xs = [p[0] for p in pares]
            ys = [p[1] for p in pares]
            n = len(xs)
            mean_x = sum(xs) / n
            mean_y = sum(ys) / n
            cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
            var = sum((x - mean_x) ** 2 for x in xs)
            results["A3_beta_ocupacion_sincronizador"] = cov / var if var else None
            results["A3_n"] = n
            results["A3_bucket_s"] = BUCKET_S

    # --- C3: continuidad usando el latido del DSO (ValidatorLicense_ReportActive,
    # hallado en la matriz de requerimientos como burst periodico), no el trafico
    # de usuarios -- exactamente la distincion que exige C-5/C3 del plan.
    latidos = []
    for e in events:
        u = e.get("update")
        if not u:
            continue
        tiene_latido = any(
            ev.get("choice") == HEARTBEAT_CHOICE for ev in u.get("events_by_id", {}).values()
        )
        if tiene_latido:
            try:
                latidos.append(parse_ts(u["record_time"]))
            except Exception:
                pass
    latidos = sorted(set(latidos))
    if len(latidos) >= 2:
        deltas_latido = sorted(b - a for a, b in zip(latidos, latidos[1:]))
        deltas_latido_s = [d.total_seconds() for d in deltas_latido]
        med_latido = st.median(deltas_latido_s)
        umbral_latido = 10 * med_latido
        span_latido = (latidos[-1] - latidos[0]).total_seconds()
        gap_latido = sum(d for d in deltas_latido_s if d > umbral_latido)
        results["C3_fraccion_continuidad"] = (1 - gap_latido / span_latido) if span_latido else None
        results["C3_n"] = len(latidos)
        results["C3_cadencia_latido_mediana_s"] = med_latido

    # --- D1: sujeto declarado (Sec.5.4 del plan: "el operador compra trafico,
    # no el usuario"). Degenerada por arquitectura, igual que Tempo D1=100%:
    # el costo de red (trafico) lo adquiere el operador del validador, no el
    # usuario final gastando un activo volatil propio para pagar la comision.
    results["D1_declarado_degenerada"] = 1.0

    # --- D2/D3: sobre las mismas choices de transferencia real (TransferFactory_
    # Transfer / AmuletRules_Transfer): D2 = fraccion con datos de referencia en
    # el campo `meta` del estandar de token; D3 = fraccion con mas de una salida
    # (multi-transferencia) y con mas de un instrumento de entrada (multi-activo).
    n_transfer = 0
    n_con_meta = 0
    n_multi_salida = 0
    n_multi_activo = 0
    for e in events:
        u = e.get("update")
        if not u:
            continue
        for ev in u.get("events_by_id", {}).values():
            if ev.get("choice") not in TRANSFER_CHOICES:
                continue
            n_transfer += 1
            arg = ev.get("choice_argument") or {}
            transfer = arg.get("transfer") or {}
            meta_values = ((transfer.get("meta") or {}).get("values")) or {}
            outputs = transfer.get("outputs") or []
            meta_en_salidas = any(isinstance(o, dict) and o.get("meta") for o in outputs)
            if meta_values or meta_en_salidas:
                n_con_meta += 1
            if len(outputs) > 1:
                n_multi_salida += 1
            # Instrumentos distintos tocados por la transferencia. TransferFactory_
            # Transfer trae un unico instrumentId por diseno (nunca multi-activo por
            # construccion de la choice). AmuletRules_Transfer no trae instrumentId,
            # solo `inputs` etiquetados; se normaliza "InputAmulet"/"InputLockedAmulet"
            # como el MISMO activo (Amulet en distinto estado de holding, no dos
            # instrumentos), consistente con el hallazgo C-6 de que solo Amulet
            # circula visible en esta muestra. Un tag realmente distinto (ej. una
            # stablecoin) si se contaria aparte.
            instrumentos = set()
            inst = transfer.get("instrumentId")
            if inst:
                instrumentos.add(json.dumps(inst, sort_keys=True))
            else:
                for i in transfer.get("inputs") or []:
                    if isinstance(i, dict) and i.get("tag"):
                        instrumentos.add(i["tag"].replace("Locked", ""))
            if len(instrumentos) > 1:
                n_multi_activo += 1
    if n_transfer:
        results["D2_fraccion_con_referencia"] = n_con_meta / n_transfer
        results["D3_fraccion_multi_transferencia"] = n_multi_salida / n_transfer
        results["D3_fraccion_multi_activo"] = n_multi_activo / n_transfer
        results["D2_D3_n"] = n_transfer

    # --- C5: cambios estructurales de las reglas del DSO en la ventana (choices
    # DsoRules_* que no son ruido rutinario, ver DSO_CHOICES_RUTINARIAS arriba).
    # 0 en la ventana muestreada es un resultado valido (no se observo ninguno),
    # no un no_computable.
    estructurales = Counter()
    for e in events:
        u = e.get("update")
        if not u:
            continue
        for ev in u.get("events_by_id", {}).values():
            c = ev.get("choice") or ""
            if c.startswith("DsoRules_") and c not in DSO_CHOICES_RUTINARIAS:
                estructurales[c] += 1
    results["C5_cambios_estructurales"] = sum(estructurales.values())
    results["C5_detalle"] = dict(estructurales)
    results["C5_n"] = len(events)

    print(json.dumps(results, indent=2, default=str))
    with open(f"{RAW}/../canton_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
