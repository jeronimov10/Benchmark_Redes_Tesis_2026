"""Procesador de Aptos: bloques REST con transacciones a muestras (productor, costo APT->USD, patrocinio por fee payer, eventos de Fungible Asset)
y decodificacion BCS exacta de ExecutionConfig para el limite de gas de bloque."""

EVENTOS_FA = ("0x1::fungible_asset::Deposit", "0x1::fungible_asset::Withdraw")
OCTAS_POR_APT = 1e8


class LectorBcs:
    def __init__(self, datos):
        self.datos = datos
        self.pos = 0

    def u8(self):
        v = self.datos[self.pos]
        self.pos += 1
        return v

    def u32(self):
        v = int.from_bytes(self.datos[self.pos:self.pos + 4], "little")
        self.pos += 4
        return v

    def u64(self):
        v = int.from_bytes(self.datos[self.pos:self.pos + 8], "little")
        self.pos += 8
        return v

    def booleano(self):
        return bool(self.u8())

    def opcion_u64(self):
        return self.u64() if self.u8() != 0 else None


def decodificar_execution_config(hexa):
    datos = bytes.fromhex(hexa[2:] if hexa.startswith("0x") else hexa)
    r = LectorBcs(datos)

    def barajador():
        v = r.u8()
        if v == 0:
            return {"type": "NoShuffling"}
        if v in (1, 2):
            return {"type": v, "param": r.u32()}
        if v == 3:
            return {"type": "DeprecatedFairness"}
        if v in (4, 5):
            return {"type": v, "sender": r.u64(), "platform": r.u64(), "user": r.u64()}
        raise ValueError(f"TransactionShufflerType: variante {v} no reconocida")

    def limite_gas():
        v = r.u8()
        if v == 0:
            return {"type": "NoLimit", "effective_block_gas_limit": None}
        if v == 1:
            return {"type": "Limit", "effective_block_gas_limit": r.u64()}
        if v == 2:
            eff = r.u64()
            r.u64()
            r.u64()
            r.u32()
            r.booleano()
            r.booleano()
            r.opcion_u64()
            r.booleano()
            r.booleano()
            return {"type": "ComplexLimitV1", "effective_block_gas_limit": eff}
        raise ValueError(f"BlockGasLimitType: variante {v} no reconocida")

    variante = r.u8()
    out = {"variante": variante, "shuffler": barajador()}
    if variante == 0:
        out["block_gas_limit_type"] = {"type": "NoLimit", "effective_block_gas_limit": None}
    elif variante in (1, 2):
        out["block_gas_limit_type"] = {"type": "Option<u64>", "effective_block_gas_limit": r.opcion_u64()}
        if variante == 2:
            r.u8()
    elif variante in (4, 5, 6, 7):
        out["block_gas_limit_type"] = limite_gas()
        if variante >= 5:
            r.booleano()
        r.u8()
        if variante >= 6:
            r.u64()
        if variante >= 7:
            r.u8()
    else:
        raise ValueError(f"OnChainExecutionConfig: variante {variante} no reconocida")
    if r.pos != len(datos):
        raise ValueError(f"ExecutionConfig: se consumieron {r.pos} de {len(datos)} bytes; layout no coincide")
    return out


def productor_bloque(b):
    for tx in b.get("transactions", []):
        if tx.get("type") == "block_metadata_transaction":
            return tx.get("proposer")
    return None


def es_patrocinada(tx):
    sig = tx.get("signature") or {}
    return sig.get("type") == "fee_payer_signature" or "fee_payer" in sig


def procesar_bloque(b, limite_gas, precio_apt_usd, store_a_activo):
    usuario = [t for t in b.get("transactions", []) if t.get("type") == "user_transaction"]
    gas_bloque = sum(int(t["gas_used"]) for t in usuario if t.get("gas_used") is not None)
    ts = int(b["block_timestamp"]) / 1e6
    ocup = gas_bloque / limite_gas if limite_gas else None
    bloque = {"numero": int(b["block_height"]), "ts": ts, "productor": productor_bloque(b),
              "gas_usado": float(gas_bloque), "gas_limite": float(limite_gas) if limite_gas else None,
              "n_tx": len(usuario), "fuente": "aptos_rest"}
    txs = []
    for t in usuario:
        gu, gp = t.get("gas_used"), t.get("gas_unit_price")
        fee = None
        if gu is not None and gp is not None and precio_apt_usd:
            fee = int(gu) * int(gp) / OCTAS_POR_APT * precio_apt_usd
        eventos = [e for e in t.get("events", []) if e.get("type") in EVENTOS_FA]
        activos = {store_a_activo.get(e.get("data", {}).get("store")) for e in eventos}
        resueltos = bool(eventos) and None not in activos
        txs.append({
            "hash": t["hash"], "bloque": bloque["numero"], "ts": ts, "fee_usd": fee, "precio_usado": precio_apt_usd,
            "ocupacion": ocup, "gas_usado": float(gu) if gu is not None else None,
            "estado_ok": bool(t.get("success", True)),
            "patrocinada": es_patrocinada(t), "memo": None,
            "multi_transfer": (len(eventos) > 1) if eventos else None,
            "multi_activo": (len(activos) > 1) if resueltos else None,
            "tiene_transfer": bool(eventos),
        })
    return bloque, txs


def stores_de_bloque(b):
    out = set()
    for t in b.get("transactions", []):
        if t.get("type") != "user_transaction":
            continue
        for e in t.get("events", []):
            if e.get("type") in EVENTOS_FA:
                s = e.get("data", {}).get("store")
                if s:
                    out.add(s)
    return out
