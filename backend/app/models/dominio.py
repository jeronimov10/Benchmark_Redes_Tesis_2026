"""Entidades de dominio: estados de medicion, metricas normalizadas, redes y peticiones al modelo."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class EstadoMetrica(str, Enum):
    VALIDA = "valida"
    INSUFICIENTE = "insuficiente"
    OBSOLETA = "obsoleta"
    FALLIDA = "fallida"
    NO_COMPUTABLE = "no_computable"


class Origen(str, Enum):
    VIVO = "vivo"
    BASE = "base"


class MetricaValor(BaseModel):
    red: str
    metrica: str
    valor: Optional[float] = None
    sigma: Optional[float] = None
    unidad: str = ""
    estado: EstadoMetrica = EstadoMetrica.NO_COMPUTABLE
    n: int = 0
    ventana_s: Optional[float] = None
    ts: float
    fuente: str = ""
    nota: str = ""
    cota_inferior: bool = False


class DefinicionRed(BaseModel):
    id: str
    nombre: str
    responsable: str
    familia: str
    fuente: str
    metricas_vivo: list[str]
    metricas_base: dict[str, str]


class PeticionModelo(BaseModel):
    accion: Literal["interpretar", "recomendar"] = "recomendar"
    monto_cop: float = Field(gt=0, le=1e13)
    transfronterizo: bool = False
    espera_s: float = Field(gt=0, le=1e7)
    irrevocabilidad: Literal["baja", "media", "alta"] = "media"
    trm: float = Field(default=4000.0, gt=0, le=1e6)
    modo: Literal["vivo", "medicion"] = "vivo"


class PeticionRecalibracion(BaseModel):
    redes: Optional[list[str]] = None
    bloques_tempo: Optional[int] = Field(default=None, ge=50, le=5000)
    bloques_aptos: Optional[int] = Field(default=None, ge=20, le=1500)
    paginas_canton: Optional[int] = Field(default=None, ge=1, le=200)
    minutos_evm: Optional[int] = Field(default=None, ge=5, le=1440)


class PeticionLote(BaseModel):
    pruebas: list[Literal["P1", "P2", "P3", "P4", "P5", "P6"]] = ["P1", "P2", "P3", "P4", "P5", "P6"]
    fuente: Literal["base", "vivo", "ambas"] = "ambas"
    semilla: Optional[int] = None
    replicas: Optional[int] = Field(default=None, ge=100, le=100000)
    tope: int = Field(default=400, ge=50, le=400)
    panel_por_perfil: int = Field(default=10, ge=1, le=50)
    niveles_replicas: list[int] = Field(default=[500, 2000, 10000, 40000], min_length=2, max_length=6)
