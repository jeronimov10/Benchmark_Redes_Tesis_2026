"""Colector de Tempo (JSON-RPC): bloques y recibos TIP-20, validadores activos (precompilado ValidatorConfigV2), calendario de forks
(tempo_forkSchedule) y sondeo continuo del bloque finalizado para medir tau_F - tau_1 (B2) en tiempo real."""

import time

from ...utils.keccak import selector
from ..processors.evm import bloque_a_muestra, hx, ocupacion
from ..processors.tempo import tx_tempo
from .base import Colector, ErrorFuente

VALIDATOR_CONFIG_V2 = "0xCCCCCCCC00000000000000000000000000000001"
SEL_VALIDADORES = selector("getActiveValidators()")
SEL_DECIMALES = selector("decimals()")


class ColectorTempo(Colector):
    red = "tempo"

    def __init__(self, settings, cliente, repos):
        super().__init__(settings, cliente, repos)
        self.url = settings.rpc_tempo
        self._fee_tokens = {}
        self._ultimo_finalizado = None

    async def _token_verificado(self, token):
        if token in self._fee_tokens:
            return self._fee_tokens[token]
        try:
            dec = hx(await self.http.rpc(self.url, "eth_call", [{"to": token, "data": SEL_DECIMALES}, "latest"]))
            self._fee_tokens[token] = 0 < dec <= 18
        except ErrorFuente:
            self._fee_tokens[token] = False
        return self._fee_tokens[token]

    async def ciclo_bloques(self):
        cap = self.settings.max_bloques_por_ciclo
        cabeza = hx(await self.http.rpc(self.url, "eth_blockNumber"))
        ultimo = self.repos["muestras"].ultimo_bloque(self.red)
        if ultimo is None:
            inicio = cabeza - min(cap, 10) + 1
        elif cabeza - ultimo > cap:
            inicio = cabeza - cap + 1
        else:
            inicio = ultimo + 1
        if inicio > cabeza:
            return {"bloques": 0, "txs": 0, "muestras": []}
        crudos = [b for b in await self.http.rpc_lote(
            self.url, [("eth_getBlockByNumber", [hex(n), True]) for n in range(inicio, cabeza + 1)], tamano=25) if b]
        muestras = []
        for b in crudos:
            m = bloque_a_muestra(b)
            m["productor"] = ((b.get("consensusContext") or {}).get("proposer") or "").lower() or None
            muestras.append(m)
        self.repos["muestras"].guardar_bloques(self.red, muestras)
        txs_crudas = [(b, t) for b in crudos for t in (b.get("transactions") or [])]
        filas = []
        if txs_crudas:
            recibos = await self.http.rpc_lote(
                self.url, [("eth_getTransactionReceipt", [t["hash"]]) for _, t in txs_crudas], tamano=25)
            info = {hx(b["number"]): (bloque_a_muestra(b)["ts"], ocupacion(b)) for b in crudos}
            for (b, t), rc in zip(txs_crudas, recibos):
                if rc is None:
                    continue
                ft = rc.get("feeToken")
                tokens = {ft: await self._token_verificado(ft)} if ft else {}
                verificados = {k for k, v in tokens.items() if v}
                ts, ocup = info[hx(b["number"])]
                filas.append(tx_tempo(rc, ts, ocup, verificados))
            self.repos["muestras"].guardar_txs(self.red, filas)
        return {"bloques": len(muestras), "txs": len(filas), "muestras": muestras}

    async def ciclo_estado(self):
        crudo = await self.http.rpc(self.url, "eth_call", [{"to": VALIDATOR_CONFIG_V2, "data": SEL_VALIDADORES}, "latest"])
        datos = crudo[2:]
        n = int(datos[64:128], 16)
        if n <= 0:
            raise ErrorFuente("getActiveValidators devolvio cero validadores")
        self.repos["estado"].guardar(self.red, "validadores", {"n": n, "precompilado": VALIDATOR_CONFIG_V2})
        fork = await self.http.rpc(self.url, "tempo_forkSchedule")
        if not isinstance(fork, dict) or "schedule" not in fork:
            raise ErrorFuente("tempo_forkSchedule sin campo schedule")
        self.repos["estado"].guardar(self.red, "fork_schedule", fork)
        return {"validadores": n, "fork_activo": fork.get("active")}

    async def ciclo_finalidad(self):
        t_obs = time.time()
        b = await self.http.rpc(self.url, "eth_getBlockByNumber", ["finalized", False])
        numero = hx(b["number"])
        if self._ultimo_finalizado is None:
            self._ultimo_finalizado = numero
            return {"transiciones": 0}
        if numero == self._ultimo_finalizado:
            return {"transiciones": 0}
        self._ultimo_finalizado = numero
        tau_1 = bloque_a_muestra(b)["ts"]
        if t_obs < tau_1:
            return {"transiciones": 0}
        self.repos["muestras"].guardar_finalidad(self.red, [{"bloque": numero, "tau_1": tau_1, "tau_f": t_obs, "delta_s": t_obs - tau_1}])
        return {"transiciones": 1}
