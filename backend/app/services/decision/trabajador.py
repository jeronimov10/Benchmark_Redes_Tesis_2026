"""Funcion ejecutada en un proceso aparte: corre el modelo de la tesis (modelo.recomendar) sin competir por el GIL con los colectores."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modelo"))
import modelo  # noqa: E402


def ejecutar_modelo(perfiles, entrada, replicas):
    return modelo.recomendar(perfiles, replicas=replicas, **entrada)


def calentar():
    return modelo.METRICAS is not None
