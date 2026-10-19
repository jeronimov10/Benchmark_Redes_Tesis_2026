"""Colector de Canton (Scan API): estado del DSO (pesos de Super Validators, precio de trafico, limites base) y flujo continuo de eventos
con cursor persistido en SQLite. Los veredictos se submuestrean sistematicamente para acotar el volumen; transferencias y latidos se leen completos."""

import asyncio
from datetime import datetime, timedelta, timezone

from ..processors.canton import (epoch, pesos_super_validators, precio_trafico_usd_por_mb, procesar_evento, trafico_base)
from .base import Colector, ErrorFuente

MIGRACION_INICIAL = 4
PAGINA = 200
ESPERA_ENTRE_PAGINAS_S = 0.2
EDAD_CURSOR_REINTENTO_S = 600


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class ColectorCanton(Colector):
    red = "canton"

    def __init__(self, settings, cliente, repos):
        super().__init__(settings, cliente, repos)
        self.base = settings.scan_canton
        self._precio_mb = None
        self._contador = 0

    async def ciclo_estado(self):
        dso = await self.http.get(f"{self.base}/v0/dso")
        pesos = pesos_super_validators(dso)
        if not pesos:
            raise ErrorFuente("DSO sin Super Validators")
        burst, ventana = trafico_base(dso)
        self._precio_mb = precio_trafico_usd_por_mb(dso)
        self.repos["estado"].guardar(self.red, "dso", {"pesos": pesos, "n_sv": len(pesos), "precio_mb": self._precio_mb,
                                                       "burst_bytes": burst, "burst_ventana_s": ventana})
        return {"super_validators": len(pesos), "precio_mb": self._precio_mb}

    def _cursor(self, ahora):
        valor, ts = self.repos["estado"].ultima(self.red, "cursor_eventos")
        if valor is None:
            return {"after_record_time": _iso(ahora - 60), "after_migration_id": MIGRACION_INICIAL}, ahora
        return valor, ts

    async def _pagina(self, cursor):
        return (await self.http.post(f"{self.base}/v0/events", json={"after": cursor, "page_size": PAGINA})).get("events", [])

    async def ciclo_bloques(self):
        if self._precio_mb is None:
            valor, _ = self.repos["estado"].ultima(self.red, "dso")
            if valor:
                self._precio_mb = valor["precio_mb"]
            else:
                await self.ciclo_estado()
        ahora = datetime.now(timezone.utc).timestamp()
        cursor, ts_cursor = self._cursor(ahora)
        desde = epoch(cursor["after_record_time"])
        tx_filas, fin_filas, c3_puntos, estructurales, total = [], [], [], 0, 0
        ultimo_evento = None
        for pagina in range(self.settings.canton_paginas_por_ciclo):
            eventos = await self._pagina(cursor)
            if not eventos and pagina == 0 and ahora - ts_cursor > EDAD_CURSOR_REINTENTO_S:
                alterno = {**cursor, "after_migration_id": cursor["after_migration_id"] + 1}
                eventos = await self._pagina(alterno)
                if eventos:
                    cursor = alterno
            if not eventos:
                break
            for e in eventos:
                p = procesar_evento(e, self._precio_mb)
                self._contador += 1
                es_veredicto = e.get("verdict") is not None
                if es_veredicto and self._contador % self.settings.canton_submuestreo != 0:
                    p["txs"] = [t for t in p["txs"] if not t["hash"].startswith("v:")]
                    p["finalidad"] = None
                tx_filas += p["txs"]
                if p["finalidad"]:
                    fin_filas.append(p["finalidad"])
                if p["latido"]:
                    c3_puntos.append((p["latido"]["numero"], p["latido"]["ts"]))
                estructurales += p["estructurales"]
                total += 1
                src = e.get("verdict") or e.get("update")
                ultimo_evento = {"after_record_time": src["record_time"], "after_migration_id": src.get("migration_id", cursor["after_migration_id"])}
            cursor = ultimo_evento
            if len(eventos) < PAGINA:
                break
            await asyncio.sleep(ESPERA_ENTRE_PAGINAS_S)
        self.repos["muestras"].guardar_txs(self.red, tx_filas)
        self.repos["muestras"].guardar_finalidad(self.red, fin_filas)
        if ultimo_evento:
            self.repos["estado"].guardar(self.red, "cursor_eventos", ultimo_evento)
            hasta = epoch(ultimo_evento["after_record_time"])
            self.repos["estado"].guardar(self.red, "c5_cambios", {"cambios": estructurales, "desde": desde, "hasta": hasta})
        return {"eventos": total, "txs": len(tx_filas), "finalidad": len(fin_filas),
                "muestras": [], "latidos": sorted(c3_puntos, key=lambda x: x[1])}
