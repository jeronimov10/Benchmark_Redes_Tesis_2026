"""Almacen propio del banco (SQLite, simulacion.db): corridas por lotes, evaluaciones por prueba, ciclos del panel continuo y estado.
Es independiente de redes.db: una corrida del banco no agrega filas a la base de la aplicacion."""

import json
import uuid

from app.db.connection import Database
from app.utils.tiempo import ahora

MIGRACIONES_SIM = [
    """
    CREATE TABLE corridas (
        id TEXT PRIMARY KEY, inicio REAL NOT NULL, fin REAL, estado TEXT NOT NULL,
        config TEXT NOT NULL, manifiesto TEXT, log TEXT
    );
    CREATE TABLE evaluaciones (
        corrida_id TEXT NOT NULL, prueba TEXT NOT NULL, fuente TEXT NOT NULL, escenario TEXT NOT NULL,
        perfil INTEGER NOT NULL, indice INTEGER NOT NULL, datos TEXT NOT NULL
    );
    CREATE INDEX idx_eval ON evaluaciones (corrida_id, prueba, fuente);
    CREATE TABLE ciclos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, valido INTEGER NOT NULL, vivas INTEGER NOT NULL,
        esperadas INTEGER NOT NULL, version_perfil TEXT, datos TEXT NOT NULL
    );
    CREATE TABLE estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
    """,
]


class BaseSim(Database):
    def migrar(self):
        with self._lock:
            version = self._con.execute("PRAGMA user_version").fetchone()[0]
            for i, sql in enumerate(MIGRACIONES_SIM, start=1):
                if i <= version:
                    continue
                self._con.executescript("BEGIN;" + sql + f"PRAGMA user_version={i};COMMIT;")


class Almacen:
    def __init__(self, ruta):
        self.db = BaseSim(ruta)

    def cerrar(self):
        self.db.cerrar()

    def crear_corrida(self, config):
        id_ = uuid.uuid4().hex[:12]
        self.db.ejecutar("INSERT INTO corridas (id, inicio, estado, config) VALUES (?,?,?,?)",
                         (id_, ahora(), "en_curso", json.dumps(config)))
        return id_

    def cerrar_corrida(self, id_, estado, manifiesto=None, log=""):
        self.db.ejecutar("UPDATE corridas SET fin=?, estado=?, manifiesto=?, log=? WHERE id=?",
                         (ahora(), estado, json.dumps(manifiesto) if manifiesto else None, log, id_))

    def corrida(self, id_):
        c = self.db.uno("SELECT * FROM corridas WHERE id=?", (id_,))
        return self._decodificar(c)

    def ultima_corrida(self, estado=None):
        if estado:
            c = self.db.uno("SELECT * FROM corridas WHERE estado=? ORDER BY inicio DESC LIMIT 1", (estado,))
        else:
            c = self.db.uno("SELECT * FROM corridas ORDER BY inicio DESC LIMIT 1")
        return self._decodificar(c)

    @staticmethod
    def _decodificar(c):
        if not c:
            return None
        c["config"] = json.loads(c["config"])
        c["manifiesto"] = json.loads(c["manifiesto"]) if c["manifiesto"] else None
        return c

    def guardar_evaluaciones(self, corrida_id, prueba, fuente, escenario, registros):
        self.db.ejecutar_muchos(
            "INSERT INTO evaluaciones (corrida_id, prueba, fuente, escenario, perfil, indice, datos) VALUES (?,?,?,?,?,?,?)",
            [(corrida_id, prueba, fuente, escenario, r["perfil"], r["indice"], json.dumps(r)) for r in registros])

    def evaluaciones(self, corrida_id, prueba, fuente=None):
        sql = "SELECT prueba, fuente, escenario, perfil, indice, datos FROM evaluaciones WHERE corrida_id=? AND prueba=?"
        params = [corrida_id, prueba]
        if fuente:
            sql += " AND fuente=?"
            params.append(fuente)
        return [{**f, "datos": json.loads(f["datos"])} for f in self.db.consultar(sql + " ORDER BY perfil, indice", params)]

    def guardar_ciclo(self, ts, valido, vivas, esperadas, version, datos):
        self.db.ejecutar("INSERT INTO ciclos (ts, valido, vivas, esperadas, version_perfil, datos) VALUES (?,?,?,?,?,?)",
                         (ts, int(valido), vivas, esperadas, version, json.dumps(datos)))

    def ciclos(self, limite=None):
        if limite:
            filas = self.db.consultar("SELECT * FROM (SELECT * FROM ciclos ORDER BY id DESC LIMIT ?) ORDER BY id", (limite,))
        else:
            filas = self.db.consultar("SELECT * FROM ciclos ORDER BY id")
        for f in filas:
            f["datos"] = json.loads(f["datos"])
        return filas

    def ultimo_ciclo(self):
        f = self.db.uno("SELECT * FROM ciclos ORDER BY id DESC LIMIT 1")
        if f:
            f["datos"] = json.loads(f["datos"])
        return f

    def conteo_ciclos(self):
        return self.db.uno("SELECT COUNT(*) AS total, COALESCE(SUM(valido),0) AS validos FROM ciclos")

    def fijar(self, clave, valor):
        self.db.ejecutar("INSERT OR REPLACE INTO estado (clave, valor) VALUES (?,?)", (clave, json.dumps(valor)))

    def leer(self, clave, defecto=None):
        f = self.db.uno("SELECT valor FROM estado WHERE clave=?", (clave,))
        return json.loads(f["valor"]) if f else defecto
