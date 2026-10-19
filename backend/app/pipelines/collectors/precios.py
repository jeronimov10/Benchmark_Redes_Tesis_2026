"""Precios USD de tokens nativos leidos del registro de cada red: agregadores Chainlink en cadena (ETH en Arbitrum, MATIC/POL en Polygon,
CELO en Celo) y la tabla Pyth en Aptos. Cada direccion se verifica en vivo (description(), decimals(), frescura) antes de usarse."""

import time

from ...utils.keccak import selector
from .base import ErrorFuente

SEL_DESCRIPCION = selector("description()")
SEL_DECIMALES = selector("decimals()")
SEL_ULTIMA_RONDA = selector("latestRoundData()")

FEEDS_CHAINLINK = {
    "ETH": {"red": "arbitrum", "direccion": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612", "descripcion": "ETH / USD"},
    "POL": {"red": "polygon", "direccion": "0xAB594600376Ec9fD91F8e885dADF0CE036862dE0", "descripcion": "MATIC / USD"},
    "CELO": {"red": "celo", "direccion": "0x0568fD19986748cEfF3301e55c0eb1E729E0Ab7e", "descripcion": "CELO / USD"},
}
MAX_EDAD_CHAINLINK_S = 3600
TTL_PRECIO_S = 60.0
PYTH_APTOS = "0x7e783b349d3e89cf5931af376ebeadbfab855b3fa239b7ada8f5a92fbea6b387"
SIMBOLO_PYTH_APT = "Crypto.APT/USD"
UMBRAL_CONGELADO_S = 86400


def _palabras(hexa, n):
    cuerpo = hexa[2:]
    return [int(cuerpo[64 * i:64 * (i + 1)], 16) for i in range(n)]


def _con_signo(x):
    return x - (1 << 256) if x >> 255 else x


class ServicioPrecios:
    def __init__(self, settings, cliente):
        self.settings = settings
        self.http = cliente
        self._verificados = {}
        self._cache = {}
        self._pyth_id = None

    async def verificar_chainlink(self, activo):
        if activo in self._verificados:
            return self._verificados[activo]
        f = FEEDS_CHAINLINK[activo]
        url = self.settings.rpc(f["red"])
        crudo = await self.http.rpc(url, "eth_call", [{"to": f["direccion"], "data": SEL_DESCRIPCION}, "latest"])
        b = bytes.fromhex(crudo[2:])
        largo = int.from_bytes(b[32:64], "big")
        descripcion = b[64:64 + largo].decode(errors="replace")
        if descripcion != f["descripcion"]:
            raise ErrorFuente(f"feed {f['direccion']} en {f['red']} describe '{descripcion}', se esperaba '{f['descripcion']}'")
        dec = int(await self.http.rpc(url, "eth_call", [{"to": f["direccion"], "data": SEL_DECIMALES}, "latest"]), 16)
        if not 0 < dec <= 18:
            raise ErrorFuente(f"decimales inesperados ({dec}) en feed {descripcion}")
        self._verificados[activo] = {"decimales": dec, "descripcion": descripcion}
        return self._verificados[activo]

    async def _chainlink(self, activo):
        v = await self.verificar_chainlink(activo)
        f = FEEDS_CHAINLINK[activo]
        r = await self.http.rpc(self.settings.rpc(f["red"]), "eth_call",
                                [{"to": f["direccion"], "data": SEL_ULTIMA_RONDA}, "latest"])
        p = _palabras(r, 5)
        precio = _con_signo(p[1]) / 10 ** v["decimales"]
        publicado = float(p[3])
        if precio <= 0:
            raise ErrorFuente(f"precio no positivo en {v['descripcion']}")
        if time.time() - publicado > MAX_EDAD_CHAINLINK_S:
            raise ErrorFuente(f"precio {v['descripcion']} obsoleto ({int(time.time() - publicado)} s)")
        return {"activo": activo, "usd": precio, "publicado": publicado, "congelado": False,
                "fuente": f"chainlink:{f['red']}:{f['direccion']}:{v['descripcion']}"}

    async def _pyth_aptos(self):
        base = self.settings.rest_aptos
        if self._pyth_id is None:
            lista = await self.http.get(f"{self.settings.hermes_pyth}/v2/price_feeds",
                                        params={"query": "APT/USD", "asset_type": "crypto"})
            ids = [x["id"] for x in lista if x.get("attributes", {}).get("symbol") == SIMBOLO_PYTH_APT]
            if not ids:
                raise ErrorFuente("Hermes no devolvio el feed Crypto.APT/USD")
            self._pyth_id = "0x" + ids[0]
        estado = await self.http.get(f"{base}/accounts/{PYTH_APTOS}/resource/{PYTH_APTOS}::state::LatestPriceInfo")
        handle = estado["data"]["info"]["handle"]
        item = await self.http.post(f"{base}/tables/{handle}/item", json={
            "key_type": f"{PYTH_APTOS}::price_identifier::PriceIdentifier",
            "value_type": f"{PYTH_APTOS}::price_info::PriceInfo",
            "key": {"bytes": self._pyth_id}})
        feed = item["price_feed"]
        if "0x" + feed["price_identifier"]["bytes"].removeprefix("0x") != self._pyth_id:
            raise ErrorFuente("el PriceInfo on-chain no corresponde al feed consultado")
        pr = feed["price"]
        magnitud = int(pr["price"]["magnitude"])
        expo = int(pr["expo"]["magnitude"])
        usd = magnitud / 10 ** expo if pr["expo"]["negative"] else magnitud * 10 ** expo
        if pr["price"]["negative"] or usd <= 0:
            raise ErrorFuente("precio APT/USD no positivo")
        publicado = float(pr["timestamp"])
        return {"activo": "APT", "usd": usd, "publicado": publicado,
                "congelado": (time.time() - publicado) > UMBRAL_CONGELADO_S,
                "fuente": f"pyth-aptos:{PYTH_APTOS}:APT/USD"}

    async def precio(self, activo):
        hit = self._cache.get(activo)
        if hit and time.monotonic() - hit[0] < TTL_PRECIO_S:
            return hit[1]
        res = await (self._pyth_aptos() if activo == "APT" else self._chainlink(activo))
        self._cache[activo] = (time.monotonic(), res)
        return res
