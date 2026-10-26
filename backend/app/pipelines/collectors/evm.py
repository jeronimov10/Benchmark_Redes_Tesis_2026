"""Colector EVM para Polygon, Celo y Arbitrum: lee bloques completos, localiza pagos en USDC (eventos Transfer del contrato verificado
y llamadas directas al contrato), obtiene sus recibos y los normaliza. Verifica el contrato de USDC (symbol, decimals, codigo) y lee la
ranura de implementacion del proxy para C5."""

import asyncio

from ...utils.keccak import keccak256_hex, selector
from ..processors.evm import (TOPIC_TRANSFER, bloque_a_muestra, candidatas_pago, hx, ocupacion,
                              tx_de_pago_evm)
from .base import Colector, ErrorFuente
from .precios import ServicioPrecios

ACTIVO_NATIVO = {"polygon": "POL", "celo": "CELO", "arbitrum": "ETH"}
SEL_SIMBOLO = selector("symbol()")
SEL_DECIMALES = selector("decimals()")
RANURAS_PROXY = {
    "zeppelinos": "0x" + keccak256_hex("org.zeppelinos.proxy.implementation"),
    "eip1967": "0x" + format(int(keccak256_hex("eip1967.proxy.implementation"), 16) - 1, "064x"),
}


def _texto_abi(hexa):
    b = bytes.fromhex(hexa[2:])
    if len(b) == 32:
        return b.rstrip(b"\x00").decode(errors="replace")
    n = int.from_bytes(b[32:64], "big")
    return b[64:64 + n].decode(errors="replace")


class ColectorEVM(Colector):
    def __init__(self, red, settings, cliente, repos, precios):
        super().__init__(settings, cliente, repos)
        self.red = red
        self.url = settings.rpc(red)
        self.token = settings.usdc(red).lower()
        self.precios: ServicioPrecios = precios
        self.token_ok = False

    async def verificar(self):
        simbolo = _texto_abi(await self.http.rpc(self.url, "eth_call", [{"to": self.token, "data": SEL_SIMBOLO}, "latest"]))
        decimales = hx(await self.http.rpc(self.url, "eth_call", [{"to": self.token, "data": SEL_DECIMALES}, "latest"]))
        codigo = await self.http.rpc(self.url, "eth_getCode", [self.token, "latest"])
        if simbolo != "USDC" or decimales != 6 or codigo in (None, "0x"):
            raise ErrorFuente(f"el contrato {self.token} en {self.red} no se verifica como USDC (symbol={simbolo}, decimals={decimales})")
        self.token_ok = True
        self.repos["estado"].guardar(self.red, "usdc_verificado", {"direccion": self.token, "symbol": simbolo, "decimals": decimales})
        return {"usdc": self.token}

    async def ciclo_estado(self):
        if not self.token_ok:
            await self.verificar()
        impl = None
        for nombre, ranura in RANURAS_PROXY.items():
            v = await self.http.rpc(self.url, "eth_getStorageAt", [self.token, ranura, "latest"])
            if v and int(v, 16) != 0:
                impl = {"impl": "0x" + v[-40:], "ranura": nombre}
                break
        if impl is None:
            raise ErrorFuente("ninguna ranura de implementacion de proxy devolvio una direccion para USDC")
        self.repos["estado"].guardar(self.red, "proxy_impl", impl)
        return impl

    async def ciclo_bloques(self):
        if not self.token_ok:
            await self.verificar()
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
            return {"bloques": 0, "pagos": 0}
        llamadas = [("eth_getBlockByNumber", [hex(n), True]) for n in range(inicio, cabeza + 1)]
        crudos = [b for b in await self.http.rpc_lote(self.url, llamadas, tamano=10) if b]
        muestras = [bloque_a_muestra(b) for b in crudos]
        pagos = await self._pagos(crudos, inicio, cabeza)
        self.repos["muestras"].guardar_bloques(self.red, muestras)
        return {"bloques": len(muestras), "pagos": pagos}

    async def _logs(self, inicio, fin):
        filtro = {"address": self.token, "topics": [TOPIC_TRANSFER], "fromBlock": hex(inicio), "toBlock": hex(fin)}
        for intento in range(4):
            try:
                return await self.http.rpc(self.url, "eth_getLogs", [filtro])
            except ErrorFuente as exc:
                if "range" not in str(exc) or intento == 3:
                    raise
                await asyncio.sleep(1.5 * (intento + 1))

    async def _pagos(self, bloques, inicio, fin):
        logs = await self._logs(inicio, fin)
        con_transfer = {lg["transactionHash"].lower() for lg in logs or []}
        info_bloque = {hx(b["number"]): (bloque_a_muestra(b)["ts"], ocupacion(b)) for b in bloques}
        candidatas = []
        for b in bloques:
            for tx in candidatas_pago(b.get("transactions") or [], self.token, con_transfer):
                tx["blockNumber"] = b["number"]
                candidatas.append(tx)
        if not candidatas:
            return 0
        recibos = await self.http.rpc_lote(self.url, [("eth_getTransactionReceipt", [t["hash"]]) for t in candidatas], tamano=25)
        precio = None
        try:
            precio = (await self.precios.precio(ACTIVO_NATIVO[self.red]))["usd"]
            self.repos["salud"].ok(self.red, "precio")
        except Exception as exc:
            self.repos["salud"].fallo(self.red, "precio", exc)
        filas = []
        for tx, rc in zip(candidatas, recibos):
            if rc is None:
                continue
            ts, ocup = info_bloque[hx(tx["blockNumber"])]
            filas.append(tx_de_pago_evm(tx, rc, ts, ocup, self.token, precio))
        self.repos["muestras"].guardar_txs(self.red, filas)
        return len(filas)
