"""Procesador de Tempo: recibos TIP-20 a muestras (costo en USD por feeToken, patrocinio por feePayer, memo, multi-transferencia/activo)."""

from collections import Counter

from .evm import TOPIC_TRANSFER, TOPIC_TRANSFER_CON_MEMO, hx, ocupacion

ESCALA_FEE_TEMPO = 10 ** 18


def tx_tempo(recibo, bloque_ts, bloque_ocup, fee_tokens):
    h = recibo["transactionHash"]
    gas = hx(recibo.get("gasUsed"))
    precio = hx(recibo.get("effectiveGasPrice"))
    fee_usd = None
    if recibo.get("feeToken") in fee_tokens:
        fee_usd = gas * precio / ESCALA_FEE_TEMPO
    por_token = Counter()
    n_transfer = 0
    memo = False
    for lg in recibo.get("logs", []):
        t = lg.get("topics") or []
        if not t:
            continue
        if t[0].lower() == TOPIC_TRANSFER:
            n_transfer += 1
            por_token[lg["address"].lower()] += 1
        if t[0].lower() == TOPIC_TRANSFER_CON_MEMO:
            memo = True
    return {
        "hash": h, "bloque": hx(recibo.get("blockNumber")), "ts": bloque_ts, "fee_usd": fee_usd,
        "precio_usado": 1.0 if fee_usd is not None else None, "ocupacion": bloque_ocup,
        "gas_usado": float(gas), "estado_ok": recibo.get("status") == "0x1",
        "patrocinada": bool(recibo.get("feePayer")),
        "memo": memo if n_transfer else None,
        "multi_transfer": (n_transfer > 1) if n_transfer else None,
        "multi_activo": (len(por_token) > 1) if n_transfer else None,
        "tiene_transfer": n_transfer > 0,
    }


__all__ = ["tx_tempo", "ocupacion"]
