"""Procesador EVM: transforma bloques, transacciones y recibos JSON-RPC (Polygon, Celo, Arbitrum, Tempo) en muestras normalizadas
en segundos, USD y fracciones. Funciones puras, sin red ni base de datos."""

from ...utils.keccak import selector, topic

TOPIC_TRANSFER = topic("Transfer(address,address,uint256)")
TOPIC_TRANSFER_CON_MEMO = topic("TransferWithMemo(address,address,uint256,bytes32)")
SELECTORES_AUTORIZACION = {
    selector("transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)"),
    selector("receiveWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)"),
}
TIPO_DELEGACION_7702 = "0x4"
ENTRYPOINTS_4337 = {
    "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789",
    "0x0000000071727de22e5e9d8baf0edac6f37da032",
}
DECIMALES_NATIVO = 10 ** 18


def hx(valor, defecto=0):
    if valor is None:
        return defecto
    return int(valor, 16) if isinstance(valor, str) else int(valor)


def ts_bloque(b):
    return hx(b.get("timestamp")) + hx(b.get("timestampMillisPart")) / 1000.0


def bloque_a_muestra(b, productor=None, fuente="eth_getBlockByNumber"):
    txs = b.get("transactions") or []
    gas_limite = hx(b.get("gasLimit"))
    gas_usado = hx(b.get("gasUsed"))
    if productor is None:
        productor = (b.get("miner") or "").lower() or None
    return {"numero": hx(b["number"]), "ts": ts_bloque(b), "productor": productor,
            "gas_usado": float(gas_usado), "gas_limite": float(gas_limite),
            "n_tx": len(txs), "fuente": fuente}


def productor_tempo(b):
    cc = b.get("consensusContext") or {}
    p = cc.get("proposer")
    return p.lower() if p else None


def ocupacion(b):
    gl = hx(b.get("gasLimit"))
    return hx(b.get("gasUsed")) / gl if gl else None


def logs_transfer(recibo, token=None):
    out = []
    for lg in recibo.get("logs", []):
        t = lg.get("topics") or []
        if t and t[0].lower() == TOPIC_TRANSFER and (token is None or lg.get("address", "").lower() == token):
            out.append(lg)
    return out


def es_patrocinada_evm(tx, recibo=None):
    if (tx.get("type") or "").lower() == TIPO_DELEGACION_7702:
        return True
    if (tx.get("to") or "").lower() in ENTRYPOINTS_4337:
        return True
    if tx.get("feeCurrency"):
        return True
    entrada = (tx.get("input") or tx.get("data") or "")[:10].lower()
    return entrada in SELECTORES_AUTORIZACION


def fee_nativo(recibo):
    gas = hx(recibo.get("gasUsed"))
    precio = hx(recibo.get("effectiveGasPrice"))
    l1 = hx(recibo.get("l1Fee"))
    return gas * precio + l1


def tx_de_pago_evm(tx, recibo, bloque_ts, bloque_ocup, token_pago, precio_nativo_usd):
    transfers = logs_transfer(recibo, token_pago)
    exitosa = recibo.get("status") == "0x1"
    fee_usd = None
    if precio_nativo_usd and not tx.get("feeCurrency"):
        fee_usd = fee_nativo(recibo) / DECIMALES_NATIVO * precio_nativo_usd
    return {
        "hash": tx["hash"], "bloque": hx(tx.get("blockNumber") or recibo.get("blockNumber")), "ts": bloque_ts,
        "fee_usd": fee_usd, "precio_usado": precio_nativo_usd, "ocupacion": bloque_ocup,
        "gas_usado": float(hx(recibo.get("gasUsed"))), "estado_ok": exitosa,
        "patrocinada": es_patrocinada_evm(tx, recibo),
        "memo": None, "multi_transfer": None, "multi_activo": None,
        "tiene_transfer": bool(transfers) and exitosa,
    }


def candidatas_pago(txs, token_pago, hashes_con_transfer):
    sel = []
    for tx in txs:
        if (tx.get("to") or "").lower() == token_pago or tx["hash"].lower() in hashes_con_transfer:
            sel.append(tx)
    return sel
