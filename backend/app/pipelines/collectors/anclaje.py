"""Rastreador de anclaje en Ethereum (tau_A de la tesis, seccion 5): observa en L1 el evento con que cada red publica su compromiso
(checkpoint de Polygon, juego de disputa de Celo, lote del secuenciador de Arbitrum), guarda marca de tiempo y costo de gas de cada publicacion
y alimenta A4, B2 y B2b. Cada contrato y evento se verifica en vivo (codigo, enlace desde el contrato raiz, coherencia temporal) antes de usarse."""

from ...utils.keccak import selector, topic
from .base import ErrorFuente

SEGUNDOS_POR_BLOQUE_L1 = 12
ANCLAJES = {
    "polygon": {
        "contrato": "0x86E4Dc95c7FBdBf52e33D563BbDB00823894C287",
        "evento": "NewHeaderBlock(address,uint256,uint256,uint256,uint256,bytes32)",
        "origen": "RootChainProxy publicado por Polygon en static.polygon.technology/network/mainnet/v1/index.json",
        "rango_l2": True,
    },
    "celo": {
        "contrato": "0xFbAC162162f4009Bb007C6DeBC36B1dAC10aF683",
        "evento": "DisputeGameCreated(address,uint32,bytes32)",
        "origen": "DisputeGameFactoryProxy de Celo en ethereum-optimism/superchain-registry (addresses.json, cadena 42220)",
        "rango_l2": False,
    },
    "arbitrum": {
        "contrato": "0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6",
        "evento": "SequencerBatchDelivered(uint256,bytes32,bytes32,bytes32,uint256,(uint64,uint64,uint64,uint64),uint8)",
        "origen": "SequencerInbox de Arbitrum One en OffchainLabs/arbitrum-sdk (networks.ts)",
        "raiz": "0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0",
        "rango_l2": False,
    },
}
TOLERANCIA_COHERENCIA_S = 6 * 3600


def _palabra(data, i):
    return int(data[2 + 64 * i:2 + 64 * (i + 1)], 16)


def costo_eth_de_recibo(recibo):
    gas = int(recibo["gasUsed"], 16) * int(recibo.get("effectiveGasPrice") or "0x0", 16)
    blob = int(recibo.get("blobGasUsed") or "0x0", 16) * int(recibo.get("blobGasPrice") or "0x0", 16)
    return (gas + blob) / 1e18


class RastreadorAnclaje:
    def __init__(self, red, settings, cliente, repos, precios):
        self.red = red
        self.cfg = ANCLAJES[red]
        self.settings = settings
        self.http = cliente
        self.repos = repos
        self.precios = precios
        self.topic0 = topic(self.cfg["evento"])
        self.verificado = False

    def _urls_l1(self):
        return [u for u in (self.settings.rpc_ethereum, self.settings.rpc_ethereum_respaldo) if u]

    async def _l1(self, metodo, params=None):
        ultimo = None
        for url in self._urls_l1():
            try:
                return await self.http.rpc(url, metodo, params)
            except ErrorFuente as exc:
                ultimo = exc
        raise ultimo or ErrorFuente("sin RPC de Ethereum configurado")

    async def _l1_lote(self, llamadas, tamano=25):
        ultimo = None
        for url in self._urls_l1():
            try:
                return await self.http.rpc_lote(url, llamadas, tamano=tamano)
            except ErrorFuente as exc:
                ultimo = exc
        raise ultimo or ErrorFuente("sin RPC de Ethereum configurado")

    async def _logs(self, desde, hasta):
        return await self._l1("eth_getLogs", [{"address": self.cfg["contrato"], "topics": [self.topic0],
                                                "fromBlock": hex(desde), "toBlock": hex(hasta)}])

    async def verificar(self):
        contrato = self.cfg["contrato"]
        codigo = await self._l1("eth_getCode", [contrato, "latest"])
        if codigo in (None, "0x"):
            raise ErrorFuente(f"{contrato} no tiene codigo en Ethereum ({self.red})")
        raiz = self.cfg.get("raiz")
        if raiz:
            enlazado = await self._l1("eth_call", [{"to": raiz, "data": selector("sequencerInbox()")}, "latest"])
            if not enlazado or "0x" + enlazado[-40:] != contrato.lower():
                raise ErrorFuente(f"el contrato raiz {raiz} no apunta a {contrato} como SequencerInbox")
        cabeza = int(await self._l1("eth_blockNumber"), 16)
        ventana = self.settings.anclaje_bloques_l1_por_consulta
        logs = await self._logs(cabeza - ventana, cabeza)
        if not logs:
            raise ErrorFuente(f"sin eventos {self.cfg['evento']} en {contrato} en los ultimos {ventana} bloques de Ethereum")
        if self.cfg["rango_l2"]:
            ultimo = logs[-1]
            fin_l2 = _palabra(ultimo["data"], 1)
            l1 = await self._l1("eth_getBlockByNumber", [ultimo["blockNumber"], False])
            l2 = await self.http.rpc(self.settings.rpc(self.red), "eth_getBlockByNumber", [hex(fin_l2), False])
            delta = int(l1["timestamp"], 16) - int(l2["timestamp"], 16)
            if not 0 <= delta <= TOLERANCIA_COHERENCIA_S:
                raise ErrorFuente(f"el checkpoint {ultimo['transactionHash']} no es coherente con el bloque {fin_l2} de {self.red} (delta {delta} s)")
        self.verificado = True
        self.repos["estado"].guardar(self.red, "anclaje_verificado", {
            "contrato": contrato, "evento": self.cfg["evento"], "topic0": self.topic0, "origen": self.cfg["origen"]})
        return {"contrato": contrato}

    def _decodificar(self, lg, ts):
        a = {"l1_tx": lg["transactionHash"].lower(), "log_index": int(lg["logIndex"], 16),
             "l1_bloque": int(lg["blockNumber"], 16), "l1_ts": ts}
        if self.cfg["rango_l2"]:
            a["l2_desde"], a["l2_hasta"] = _palabra(lg["data"], 0), _palabra(lg["data"], 1)
        return a

    async def _guardar_logs(self, logs):
        bloques = sorted({int(lg["blockNumber"], 16) for lg in logs})
        cabeceras = await self._l1_lote([("eth_getBlockByNumber", [hex(b), False]) for b in bloques])
        ts = {b: int(h["timestamp"], 16) for b, h in zip(bloques, cabeceras) if h}
        filas = [self._decodificar(lg, ts[int(lg["blockNumber"], 16)]) for lg in logs if int(lg["blockNumber"], 16) in ts]
        self.repos["anclajes"].guardar(self.red, filas)
        return len(filas)

    async def explorar(self, ventana_s, consultas=None):
        cursor, _ = self.repos["estado"].ultima(self.red, "anclaje_cursor")
        cabeza = int(await self._l1("eth_blockNumber"), 16)
        ancho = self.settings.anclaje_bloques_l1_por_consulta
        desde = cursor["l1_bloque"] + 1 if cursor else cabeza - int(ventana_s * 1.02 / SEGUNDOS_POR_BLOQUE_L1)
        nuevos, hechas = 0, 0
        limite = consultas or self.settings.anclaje_consultas_por_ciclo
        while desde <= cabeza and hechas < limite:
            hasta = min(cabeza, desde + ancho - 1)
            nuevos += await self._guardar_logs(await self._logs(desde, hasta))
            self.repos["estado"].guardar(self.red, "anclaje_cursor", {"l1_bloque": hasta})
            desde, hechas = hasta + 1, hechas + 1
        return nuevos, max(cabeza - desde + 1, 0)

    async def costos(self, ventana_s, maximo=None):
        corte = (self.repos["estado"].ultima(self.red, "anclaje_cursor")[1] or 0) - ventana_s
        repo = self.repos["anclajes"]
        if repo.con_costo(self.red, corte) >= self.settings.anclaje_recibos_objetivo:
            return 0
        pendientes = repo.sin_costo(self.red, corte, maximo or self.settings.anclaje_recibos_por_ciclo)
        if not pendientes:
            return 0
        precio = (await self.precios.precio("ETH"))["usd"]
        recibos = await self._l1_lote([("eth_getTransactionReceipt", [p["l1_tx"]]) for p in pendientes])
        n = 0
        for p, rc in zip(pendientes, recibos):
            if rc is None:
                continue
            repo.poner_costo(self.red, p["l1_tx"], costo_eth_de_recibo(rc) / p["n_logs"], precio)
            n += 1
        return n

    async def ciclo(self, ventana_s=None, consultas=None, recibos=None):
        ventana_s = ventana_s or self.settings.ventana_anclaje_s
        if not self.verificado:
            await self.verificar()
        nuevos, restantes = await self.explorar(ventana_s, consultas)
        costos = 0
        try:
            costos = await self.costos(ventana_s, recibos)
        except ErrorFuente as exc:
            self.repos["salud"].fallo(self.red, "precio_l1", exc)
        else:
            self.repos["salud"].ok(self.red, "precio_l1")
        return {"anclajes_nuevos": nuevos, "costos": costos, "bloques_l1_pendientes": restantes}
