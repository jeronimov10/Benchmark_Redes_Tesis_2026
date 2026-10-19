"""Configuracion del backend: lee variables de entorno y expone un objeto Settings inmutable."""

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_REPO = RAIZ_BACKEND.parent


def _entero(nombre, defecto):
    return int(os.environ.get(nombre, defecto))


def _decimal(nombre, defecto):
    return float(os.environ.get(nombre, defecto))


def _texto(nombre, defecto):
    return os.environ.get(nombre, defecto)


def _booleano(nombre, defecto):
    return os.environ.get(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "yes")


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(_texto("DB_PATH", RAIZ_BACKEND / "data" / "redes.db")))
    dir_resultados: Path = field(default_factory=lambda: Path(_texto("RESULTADOS_DIR", RAIZ_REPO / "resultados")))
    perfiles_json: Path = field(default_factory=lambda: RAIZ_BACKEND / "modelo" / "perfiles.json")
    cors_origenes: tuple = field(default_factory=lambda: tuple(
        o.strip() for o in _texto("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()))

    colectores_activos: bool = field(default_factory=lambda: _booleano("COLECTORES_ACTIVOS", True))
    redes_activas: tuple = field(default_factory=lambda: tuple(
        r.strip() for r in _texto("REDES_ACTIVAS", "tempo,aptos,canton,polygon,celo,arbitrum").split(",") if r.strip()))

    http_timeout_s: float = field(default_factory=lambda: _decimal("HTTP_TIMEOUT_S", 20))
    http_reintentos: int = field(default_factory=lambda: _entero("HTTP_REINTENTOS", 4))
    http_backoff_base_s: float = field(default_factory=lambda: _decimal("HTTP_BACKOFF_BASE_S", 1.0))

    intervalo_bloques_s: float = field(default_factory=lambda: _decimal("INTERVALO_BLOQUES_S", 20))
    intervalo_finalidad_s: float = field(default_factory=lambda: _decimal("INTERVALO_FINALIDAD_S", 0.3))
    intervalo_estado_s: float = field(default_factory=lambda: _decimal("INTERVALO_ESTADO_S", 300))
    intervalo_metricas_s: float = field(default_factory=lambda: _decimal("INTERVALO_METRICAS_S", 30))
    max_bloques_por_ciclo: int = field(default_factory=lambda: _entero("MAX_BLOQUES_POR_CICLO", 40))

    bloques_aptos_por_ciclo: int = field(default_factory=lambda: _entero("BLOQUES_APTOS_POR_CICLO", 6))
    canton_submuestreo: int = field(default_factory=lambda: _entero("CANTON_SUBMUESTREO", 4))
    canton_paginas_por_ciclo: int = field(default_factory=lambda: _entero("CANTON_PAGINAS_POR_CICLO", 10))

    ventana_flujo_s: int = field(default_factory=lambda: _entero("VENTANA_FLUJO_S", 900))
    ventana_distribucion_s: int = field(default_factory=lambda: _entero("VENTANA_DISTRIBUCION_S", 86400))
    ventana_finalidad_s: int = field(default_factory=lambda: _entero("VENTANA_FINALIDAD_S", 72 * 3600))
    ventana_continuidad_s: int = field(default_factory=lambda: _entero("VENTANA_CONTINUIDAD_S", 14 * 86400))

    obsolescencia_s: int = field(default_factory=lambda: _entero("OBSOLESCENCIA_S", 900))
    obsolescencia_estado_s: int = field(default_factory=lambda: _entero("OBSOLESCENCIA_ESTADO_S", 7200))
    cache_ttl_s: float = field(default_factory=lambda: _decimal("CACHE_TTL_S", 30))
    replicas_monte_carlo: int = field(default_factory=lambda: _entero("REPLICAS_MONTE_CARLO", 10000))

    rpc_tempo: str = field(default_factory=lambda: _texto("RPC_TEMPO", "https://rpc.tempo.xyz"))
    rest_aptos: str = field(default_factory=lambda: _texto("REST_APTOS", "https://api.mainnet.aptoslabs.com/v1"))
    scan_canton: str = field(default_factory=lambda: _texto("SCAN_CANTON", "https://api.cantonnodes.com"))
    rpc_polygon: str = field(default_factory=lambda: _texto("RPC_POLYGON", "https://polygon.publicnode.com"))
    rpc_celo: str = field(default_factory=lambda: _texto("RPC_CELO", "https://forno.celo.org"))
    rpc_arbitrum: str = field(default_factory=lambda: _texto("RPC_ARBITRUM", "https://arb1.arbitrum.io/rpc"))
    rpc_ethereum: str = field(default_factory=lambda: _texto("RPC_ETHEREUM", "https://eth.drpc.org"))
    hermes_pyth: str = field(default_factory=lambda: _texto("HERMES_PYTH", "https://hermes.pyth.network"))
    usdc_polygon: str = field(default_factory=lambda: _texto("USDC_POLYGON", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"))
    usdc_celo: str = field(default_factory=lambda: _texto("USDC_CELO", "0xcebA9300f2b948710d2653dD7B07f33A8B32118C"))
    usdc_arbitrum: str = field(default_factory=lambda: _texto("USDC_ARBITRUM", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"))

    dias_recalibracion: int = field(default_factory=lambda: _entero("DIAS_RECALIBRACION", 14))
    horas_finalidad_recalibracion: float = field(default_factory=lambda: _decimal("HORAS_FINALIDAD_RECALIBRACION", 72))

    def usdc(self, red):
        return {"polygon": self.usdc_polygon, "celo": self.usdc_celo, "arbitrum": self.usdc_arbitrum}[red]

    def rpc(self, red):
        return {
            "tempo": self.rpc_tempo, "polygon": self.rpc_polygon,
            "celo": self.rpc_celo, "arbitrum": self.rpc_arbitrum,
        }[red]


def cargar_settings():
    return Settings()
