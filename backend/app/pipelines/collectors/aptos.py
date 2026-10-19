"""Colector de Aptos (REST): muestrea los bloques mas recientes con sus transacciones, resuelve el activo de cada store de Fungible Asset,
lee ExecutionConfig (BCS), ValidatorSet y el precio APT/USD on-chain de Pyth (marcando si esta congelado)."""

import asyncio

from ..processors.aptos import decodificar_execution_config, procesar_bloque, stores_de_bloque
from .base import Colector, ErrorFuente
from .precios import ServicioPrecios


class ColectorAptos(Colector):
    red = "aptos"

    def __init__(self, settings, cliente, repos, precios):
        super().__init__(settings, cliente, repos)
        self.base = settings.rest_aptos
        self.precios: ServicioPrecios = precios
        self._stores = {}
        self._limite_gas = None

    async def _resolver_stores(self, nuevos):
        pendientes = [s for s in nuevos if s not in self._stores]

        async def uno(s):
            try:
                r = await self.http.get(f"{self.base}/accounts/{s}/resource/0x1::fungible_asset::FungibleStore")
                self._stores[s] = r["data"]["metadata"]["inner"]
            except ErrorFuente:
                self._stores[s] = None

        await asyncio.gather(*[uno(s) for s in pendientes])

    async def ciclo_estado(self):
        cfg = await self.http.get(f"{self.base}/accounts/0x1/resource/0x1::execution_config::ExecutionConfig")
        dec = decodificar_execution_config(cfg["data"]["config"])
        limite = dec["block_gas_limit_type"].get("effective_block_gas_limit")
        if not limite:
            raise ErrorFuente("ExecutionConfig sin limite efectivo de gas de bloque")
        self._limite_gas = limite
        self.repos["estado"].guardar(self.red, "execution_config", {"limite_gas": limite, "variante": dec["variante"],
                                                                   "tipo": dec["block_gas_limit_type"]["type"]})
        vs = await self.http.get(f"{self.base}/accounts/0x1/resource/0x1::stake::ValidatorSet")
        pesos = [int(v["voting_power"]) for v in vs["data"]["active_validators"]]
        if not pesos:
            raise ErrorFuente("ValidatorSet vacio")
        self.repos["estado"].guardar(self.red, "validator_set", {"pesos": pesos, "n": len(pesos)})
        p = await self.precios.precio("APT")
        self.repos["estado"].guardar(self.red, "precio_apt", {"usd": p["usd"], "publicado": p["publicado"],
                                                             "congelado": p["congelado"], "fuente": p["fuente"]})
        return {"limite_gas": limite, "validadores": len(pesos), "precio_congelado": p["congelado"]}

    async def ciclo_bloques(self):
        if self._limite_gas is None:
            valor, _ = self.repos["estado"].ultima(self.red, "execution_config")
            if valor:
                self._limite_gas = valor["limite_gas"]
            else:
                await self.ciclo_estado()
        info = await self.http.get(self.base)
        cabeza = int(info["block_height"])
        k = self.settings.bloques_aptos_por_ciclo
        ultimo = self.repos["muestras"].ultimo_bloque(self.red)
        inicio = cabeza - k + 1 if ultimo is None or cabeza - ultimo > k else ultimo + 1
        alturas = list(range(inicio, cabeza + 1))
        if not alturas:
            return {"bloques": 0, "txs": 0, "muestras": []}
        crudos = await asyncio.gather(*[
            self.http.get(f"{self.base}/blocks/by_height/{h}", params={"with_transactions": "true"}) for h in alturas])
        stores = set()
        for b in crudos:
            stores |= stores_de_bloque(b)
        await self._resolver_stores(stores)
        precio = None
        try:
            precio = (await self.precios.precio("APT"))["usd"]
            self.repos["salud"].ok(self.red, "precio")
        except Exception as exc:
            self.repos["salud"].fallo(self.red, "precio", exc)
        bloques, txs = [], []
        for b in crudos:
            bl, tx = procesar_bloque(b, self._limite_gas, precio, self._stores)
            bloques.append(bl)
            txs += tx
        self.repos["muestras"].guardar_bloques(self.red, bloques)
        self.repos["muestras"].guardar_txs(self.red, txs)
        return {"bloques": len(bloques), "txs": len(txs), "muestras": bloques}
