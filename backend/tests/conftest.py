"""Fixtures compartidas: rutas del repositorio, settings aislados con SQLite temporal y base de datos en memoria."""

import dataclasses
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.config import Settings
from app.db.connection import Database


@pytest.fixture
def settings(tmp_path):
    return dataclasses.replace(Settings(), db_path=tmp_path / "test.db", colectores_activos=False,
                               http_reintentos=2, http_backoff_base_s=0.0, replicas_monte_carlo=400)


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.cerrar()
