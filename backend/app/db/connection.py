"""Conexion SQLite (modo WAL) con un candado de escritura, y ejecucion de migraciones por PRAGMA user_version."""

import sqlite3
import threading
from pathlib import Path

from .migrations import MIGRACIONES


class Database:
    def __init__(self, ruta):
        self.ruta = str(ruta)
        if self.ruta != ":memory:":
            Path(self.ruta).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._con = sqlite3.connect(self.ruta, check_same_thread=False, isolation_level=None)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.execute("PRAGMA foreign_keys=ON")
        self.migrar()

    def migrar(self):
        with self._lock:
            version = self._con.execute("PRAGMA user_version").fetchone()[0]
            for i, sql in enumerate(MIGRACIONES, start=1):
                if i <= version:
                    continue
                self._con.executescript("BEGIN;" + sql + f"PRAGMA user_version={i};COMMIT;")

    def version(self):
        with self._lock:
            return self._con.execute("PRAGMA user_version").fetchone()[0]

    def ejecutar(self, sql, params=()):
        with self._lock:
            return self._con.execute(sql, params).rowcount

    def ejecutar_muchos(self, sql, filas):
        filas = list(filas)
        if not filas:
            return 0
        with self._lock:
            self._con.execute("BEGIN")
            try:
                self._con.executemany(sql, filas)
                self._con.execute("COMMIT")
            except Exception:
                self._con.execute("ROLLBACK")
                raise
        return len(filas)

    def consultar(self, sql, params=()):
        with self._lock:
            return [dict(r) for r in self._con.execute(sql, params).fetchall()]

    def uno(self, sql, params=()):
        with self._lock:
            r = self._con.execute(sql, params).fetchone()
            return dict(r) if r else None

    def cerrar(self):
        with self._lock:
            self._con.close()
