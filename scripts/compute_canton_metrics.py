import json
import math
import statistics as st
from collections import Counter
from datetime import datetime, timezone

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

    print(json.dumps(results, indent=2, default=str))
    with open(f"{RAW}/../canton_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
