"""Procesador de Canton: eventos de Scan API a muestras (veredictos con costo de trafico y latencia, transferencias con meta/salidas,
latidos de ValidatorLicense_ReportActive, cambios estructurales del DSO) y pesos de Super Validators desde el estado del DSO."""

from datetime import datetime, timezone

CHOICES_DSO_RUTINARIAS = {
    "DsoRules_UpdateAmuletPriceVote", "DsoRules_SubmitStatusReport", "DsoRules_ConfirmAction",
    "DsoRules_ReceiveSvRewardCoupon", "DsoRules_MergeMemberTrafficContracts",
    "DsoRules_AmuletRules_ConvertFeaturedAppActivityMarkers",
}
CHOICES_TRANSFERENCIA = {"TransferFactory_Transfer", "AmuletRules_Transfer"}
CHOICE_LATIDO = "ValidatorLicense_ReportActive"
BYTES_POR_MB = 1e6


def parse_ts(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "." in s:
        cabeza, resto = s.split(".")
        cortes = [i for i in (resto.find("+"), resto.find("-")) if i >= 0]
        fin = min(cortes) if cortes else len(resto)
        frac, tz = resto[:fin], resto[fin:]
        s = f"{cabeza}.{(frac + '000000')[:6]}{tz}"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def epoch(s):
    return parse_ts(s).timestamp()


def micros(s):
    d = parse_ts(s)
    return int(d.timestamp()) * 1_000_000 + d.microsecond


def _fees(dso):
    return dso["amulet_rules"]["contract"]["payload"]["configSchedule"]["initialValue"]["decentralizedSynchronizer"]["fees"]


def precio_trafico_usd_por_mb(dso):
    return float(_fees(dso)["extraTrafficPrice"])


def trafico_base(dso):
    b = _fees(dso)["baseRateTrafficLimits"]
    return float(b["burstAmount"]), float(b["burstWindow"]["microseconds"]) / 1e6


def pesos_super_validators(dso):
    svs = dso["dso_rules"]["contract"]["payload"]["svs"]
    return [float(entry[1]["svRewardWeight"]) for entry in svs]


def procesar_evento(e, precio_mb):
    v = e.get("verdict")
    u = e.get("update")
    finalidad = latido = None
    txs = []
    estructurales = 0
    if v:
        rt, ft = epoch(v["record_time"]), epoch(v["finalization_time"])
        coste = (e.get("traffic_summary") or {}).get("total_traffic_cost")
        txs.append({
            "hash": "v:" + v["update_id"], "bloque": None, "ts": rt,
            "fee_usd": coste / BYTES_POR_MB * precio_mb if coste is not None else None,
            "precio_usado": precio_mb, "ocupacion": None,
            "gas_usado": float(coste) if coste is not None else None,
            "estado_ok": v.get("verdict_result") != "VERDICT_RESULT_REJECTED",
            "patrocinada": None, "memo": None, "multi_transfer": None, "multi_activo": None, "tiene_transfer": None,
        })
        finalidad = {"bloque": micros(v["record_time"]), "tau_1": rt, "tau_f": ft, "delta_s": ft - rt}
    if u:
        rt = epoch(u["record_time"])
        for idx, ev in enumerate((u.get("events_by_id") or {}).values()):
            choice = ev.get("choice") or ""
            if choice == CHOICE_LATIDO:
                latido = {"numero": micros(u["record_time"]), "ts": rt, "productor": None,
                          "gas_usado": None, "gas_limite": None, "n_tx": 0, "fuente": "latido"}
            if choice.startswith("DsoRules_") and choice not in CHOICES_DSO_RUTINARIAS:
                estructurales += 1
            if choice in CHOICES_TRANSFERENCIA:
                arg = ev.get("choice_argument") or {}
                tr = arg.get("transfer") or {}
                meta = ((tr.get("meta") or {}).get("values")) or {}
                salidas = tr.get("outputs") or []
                con_meta = bool(meta) or any(isinstance(o, dict) and o.get("meta") for o in salidas)
                instrumentos = set()
                inst = tr.get("instrumentId")
                if inst:
                    instrumentos.add(str(sorted(inst.items())) if isinstance(inst, dict) else str(inst))
                else:
                    for i in tr.get("inputs") or []:
                        if isinstance(i, dict) and i.get("tag"):
                            instrumentos.add(i["tag"].replace("Locked", ""))
                txs.append({
                    "hash": f"u:{u['update_id']}:{idx}", "bloque": None, "ts": rt,
                    "fee_usd": None, "precio_usado": None, "ocupacion": None, "gas_usado": None, "estado_ok": None,
                    "patrocinada": None, "memo": con_meta, "multi_transfer": len(salidas) > 1,
                    "multi_activo": len(instrumentos) > 1, "tiene_transfer": True,
                })
    return {"txs": txs, "finalidad": finalidad, "latido": latido, "estructurales": estructurales}
