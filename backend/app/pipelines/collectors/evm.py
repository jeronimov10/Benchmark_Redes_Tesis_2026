"""Colector EVM de Polygon, Celo y Arbitrum: lee bloques, localiza pagos en USDC, obtiene sus recibos, lee la implementacion del proxy (C5), rastrea el anclaje en Ethereum (A4, B2, B2b) y rellena ventanas recientes."""

import asyncio
import math

from ...utils.keccak import keccak256_hex, selector
from ..processors.evm import (TOPIC_TRANSFER, bloque_a_muestra, candidatas_pago, hx, ocupacion, ts_bloque,
                              tx_de_pago_evm)
from .anclaje import RastreadorAnclaje
from .base import Colector, ErrorFuente
from .precios import ServicioPrecios

ACTIVO_NATIVO = {"polygon": "POL", "celo": "CELO", "arbitrum": "ETH"}
MARGEN_CABEZA = 5
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
        self.anclaje = RastreadorAnclaje(red, settings, cliente, repos, precios)

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
            return {"bloques": 0, "pagos": 0, "muestras": []}
        n_bloques, pagos, muestras = await self._procesar_rango(inicio, cabeza)
        return {"bloques": n_bloques, "pagos": pagos, "muestras": muestras}

    async def _procesar_rango(self, inicio, fin):
        llamadas = [("eth_getBlockByNumber", [hex(n), True]) for n in range(inicio, fin + 1)]
        crudos = [b for b in await self.http.rpc_lote(self.url, llamadas, tamano=10) if b]
        muestras = [bloque_a_muestra(b) for b in crudos]
        pagos = await self._pagos(crudos, inicio, fin)
        self.repos["muestras"].guardar_bloques(self.red, muestras)
        return len(muestras), pagos, muestras

    async def ciclo_anclaje(self):
        return await self.anclaje.ciclo()

    async def segundos_por_bloque(self):
        referencia = hx(await self.http.rpc(self.url, "eth_blockNumber")) - MARGEN_CABEZA
        recientes = await self.http.rpc_lote(self.url, [("eth_getBlockByNumber", [hex(n), False]) for n in (referencia - 200, referencia)])
        if not all(recientes):
            raise ErrorFuente(f"el nodo de {self.red} no devolvio los bloques de referencia {referencia - 200} y {referencia}")
        return referencia, max((ts_bloque(recientes[1]) - ts_bloque(recientes[0])) / 200, 0.05)

    async def rellenar(self, minutos, progreso=None, cancelado=None):
        if not self.token_ok:
            await self.verificar()
        cabeza, dt = await self.segundos_por_bloque()
        total = min(self.settings.relleno_bloques_max, math.ceil(minutos * 60 / dt))
        inicio = cabeza - total + 1
        existentes = self.repos["muestras"].numeros_entre(self.red, inicio, cabeza)
        trozo = self.settings.relleno_trozo_bloques
        rangos = []
        for a in range(inicio, cabeza + 1, trozo):
            b = min(a + trozo - 1, cabeza)
            if any(n not in existentes for n in range(a, b + 1)):
                rangos.append((a, b))
        sem = asyncio.Semaphore(self.settings.relleno_concurrencia)
        hechos = {"bloques": 0, "pagos": 0, "fallidos": 0, "rangos": 0}
        fallidos = []

        async def uno(a, b, definitivo):
            if cancelado and cancelado():
                return
            async with sem:
                try:
                    nb, np_, _ = await self._procesar_rango(a, b)
                    hechos["bloques"] += nb
                    hechos["pagos"] += np_
                except ErrorFuente as exc:
                    hechos["ultimo_error"] = str(exc)[:240]
                    if not definitivo:
                        fallidos.append((a, b))
                        await asyncio.sleep(self.settings.relleno_pausa_s * 5)
                        return
                    hechos["fallidos"] += 1
                hechos["rangos"] += 1
                if progreso:
                    progreso(hechos["rangos"] / max(len(rangos), 1))
                await asyncio.sleep(self.settings.relleno_pausa_s)

        await asyncio.gather(*(uno(a, b, False) for a, b in rangos))
        pendientes, fallidos[:] = list(fallidos), []
        for a, b in pendientes:
            await uno(a, b, True)
        if rangos and hechos["fallidos"] > len(rangos) * 0.3:
            raise ErrorFuente(f"relleno de {self.red}: fallaron {hechos['fallidos']} de {len(rangos)} rangos ({hechos.get('ultimo_error')})")
        hechos.update({"bloques_solicitados": total, "segundos_por_bloque": round(dt, 3), "minutos": minutos})
        return hechos

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
