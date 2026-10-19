"""Repositorios SQLite: acceso a muestras crudas, metricas en vivo, perfiles base, salud, trabajos y auditoria."""

import json

from ..utils.tiempo import ahora


class MuestrasRepo:
    def __init__(self, db):
        self.db = db

    def guardar_bloques(self, red, bloques):
        t = ahora()
        filas = [(red, b["numero"], b["ts"], b.get("productor"), b.get("gas_usado"), b.get("gas_limite"),
                  b.get("n_tx"), b.get("fuente"), t) for b in bloques]
        return self.db.ejecutar_muchos(
            "INSERT OR IGNORE INTO muestras_bloque (red,numero,ts,productor,gas_usado,gas_limite,n_tx,fuente,recogido_en)"
            " VALUES (?,?,?,?,?,?,?,?,?)", filas)

    def guardar_txs(self, red, txs):
        t = ahora()
        filas = [(red, x["hash"], x.get("bloque"), x["ts"], x.get("fee_usd"), x.get("precio_usado"),
                  x.get("ocupacion"), x.get("gas_usado"), _b(x.get("estado_ok")), _b(x.get("patrocinada")),
                  _b(x.get("memo")), _b(x.get("multi_transfer")), _b(x.get("multi_activo")),
                  _b(x.get("tiene_transfer")), t) for x in txs]
        return self.db.ejecutar_muchos(
            "INSERT OR IGNORE INTO muestras_tx (red,hash,bloque,ts,fee_usd,precio_usado,ocupacion,gas_usado,estado_ok,"
            "patrocinada,memo,multi_transfer,multi_activo,tiene_transfer,recogido_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            filas)

    def guardar_finalidad(self, red, muestras):
        filas = [(red, m["bloque"], m["tau_1"], m["tau_f"], m["delta_s"]) for m in muestras]
        return self.db.ejecutar_muchos(
            "INSERT OR IGNORE INTO muestras_finalidad (red,bloque,tau_1,tau_f,delta_s) VALUES (?,?,?,?,?)", filas)

    def bloques_desde(self, red, desde_ts):
        return self.db.consultar(
            "SELECT numero,ts,productor,gas_usado,gas_limite,n_tx FROM muestras_bloque WHERE red=? AND ts>=? ORDER BY ts",
            (red, desde_ts))

    def txs_desde(self, red, desde_ts):
        return self.db.consultar(
            "SELECT * FROM muestras_tx WHERE red=? AND ts>=? ORDER BY ts", (red, desde_ts))

    def finalidad_desde(self, red, desde_ts):
        return self.db.consultar(
            "SELECT bloque,tau_1,tau_f,delta_s FROM muestras_finalidad WHERE red=? AND tau_f>=? ORDER BY tau_f",
            (red, desde_ts))

    def ultimo_bloque(self, red):
        r = self.db.uno("SELECT MAX(numero) AS n FROM muestras_bloque WHERE red=?", (red,))
        return r["n"] if r else None

    def conteos(self):
        out = {}
        for tabla in ("muestras_bloque", "muestras_tx", "muestras_finalidad"):
            for r in self.db.consultar(f"SELECT red, COUNT(*) AS n FROM {tabla} GROUP BY red"):
                out.setdefault(r["red"], {})[tabla] = r["n"]
        return out

    def podar(self, corte_muestras, corte_finalidad, corte_estado, corte_metricas):
        n = self.db.ejecutar("DELETE FROM muestras_bloque WHERE ts<?", (corte_muestras,))
        n += self.db.ejecutar("DELETE FROM muestras_tx WHERE ts<?", (corte_muestras,))
        n += self.db.ejecutar("DELETE FROM muestras_finalidad WHERE tau_f<?", (corte_finalidad,))
        n += self.db.ejecutar("DELETE FROM lecturas_estado WHERE ts<?", (corte_estado,))
        n += self.db.ejecutar("DELETE FROM metricas_vivo WHERE ts<?", (corte_metricas,))
        return n


class EstadoRepo:
    def __init__(self, db):
        self.db = db

    def guardar(self, red, clave, valor, ts=None):
        self.db.ejecutar("INSERT INTO lecturas_estado (red,clave,valor_json,ts) VALUES (?,?,?,?)",
                         (red, clave, json.dumps(valor), ts or ahora()))

    def ultima(self, red, clave):
        r = self.db.uno("SELECT valor_json,ts FROM lecturas_estado WHERE red=? AND clave=? ORDER BY ts DESC LIMIT 1",
                        (red, clave))
        return (json.loads(r["valor_json"]), r["ts"]) if r else (None, None)

    def historial(self, red, clave, desde_ts):
        return [(json.loads(r["valor_json"]), r["ts"]) for r in self.db.consultar(
            "SELECT valor_json,ts FROM lecturas_estado WHERE red=? AND clave=? AND ts>=? ORDER BY ts",
            (red, clave, desde_ts))]


class MetricasRepo:
    def __init__(self, db):
        self.db = db

    def guardar(self, metricas):
        filas = [(m.red, m.metrica, m.valor, m.sigma, m.unidad, m.estado.value, m.n, m.ventana_s, m.ts,
                  m.fuente, m.nota, int(m.cota_inferior)) for m in metricas]
        return self.db.ejecutar_muchos(
            "INSERT INTO metricas_vivo (red,metrica,valor,sigma,unidad,estado,n,ventana_s,ts,fuente,nota,cota_inferior)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", filas)

    def ultimas(self, red=None):
        sql = ("SELECT m.* FROM metricas_vivo m JOIN (SELECT red,metrica,MAX(id) AS mid FROM metricas_vivo "
               "GROUP BY red,metrica) u ON m.id=u.mid")
        params = ()
        if red:
            sql += " WHERE m.red=?"
            params = (red,)
        return self.db.consultar(sql, params)

    def serie(self, red, metrica, desde_ts, limite=300):
        return self.db.consultar(
            "SELECT ts,valor,estado,n FROM metricas_vivo WHERE red=? AND metrica=? AND ts>=? ORDER BY ts DESC LIMIT ?",
            (red, metrica, desde_ts, limite))[::-1]


class PerfilesRepo:
    def __init__(self, db):
        self.db = db

    def version(self):
        r = self.db.uno("SELECT valor FROM meta WHERE clave='version_base'")
        return int(r["valor"]) if r else 0

    def vacio(self):
        return self.db.uno("SELECT COUNT(*) AS n FROM perfiles_base")["n"] == 0

    def reemplazar_redes(self, perfiles_por_red, origen):
        v = self.version() + 1
        t = ahora()
        filas = []
        for red, perfil in perfiles_por_red.items():
            for mid, d in perfil.items():
                filas.append((red, mid, d.get("valor"), d.get("sigma"), d.get("nota"),
                              int(bool(d.get("cota_inferior"))), origen, v, t))
        with self.db._lock:
            for red in perfiles_por_red:
                self.db.ejecutar("DELETE FROM perfiles_base WHERE red=?", (red,))
            self.db.ejecutar_muchos(
                "INSERT INTO perfiles_base (red,metrica,valor,sigma,nota,cota_inferior,origen,version,ts)"
                " VALUES (?,?,?,?,?,?,?,?,?)", filas)
            self.db.ejecutar("INSERT OR REPLACE INTO meta (clave,valor) VALUES ('version_base',?)", (str(v),))
        return v

    def todos(self):
        perfiles, origenes = {}, {}
        for r in self.db.consultar("SELECT * FROM perfiles_base"):
            d = {"valor": r["valor"], "nota": r["nota"]}
            if r["sigma"] is not None:
                d["sigma"] = r["sigma"]
            if r["cota_inferior"]:
                d["cota_inferior"] = True
            perfiles.setdefault(r["red"], {})[r["metrica"]] = d
            origenes.setdefault(r["red"], {})[r["metrica"]] = {"origen": r["origen"], "ts": r["ts"]}
        return perfiles, origenes


class SaludRepo:
    def __init__(self, db):
        self.db = db

    def ok(self, red, componente, latencia_ms=None):
        self.db.ejecutar(
            "INSERT INTO salud_colector (red,componente,ultimo_ok,latencia_ms,fallos_consecutivos) VALUES (?,?,?,?,0)"
            " ON CONFLICT(red,componente) DO UPDATE SET ultimo_ok=excluded.ultimo_ok,"
            " latencia_ms=excluded.latencia_ms, fallos_consecutivos=0, error=NULL",
            (red, componente, ahora(), latencia_ms))

    def fallo(self, red, componente, error):
        self.db.ejecutar(
            "INSERT INTO salud_colector (red,componente,ultimo_error,error,fallos_consecutivos) VALUES (?,?,?,?,1)"
            " ON CONFLICT(red,componente) DO UPDATE SET ultimo_error=excluded.ultimo_error,"
            " error=excluded.error, fallos_consecutivos=fallos_consecutivos+1",
            (red, componente, ahora(), str(error)[:500]))

    def todos(self):
        return self.db.consultar("SELECT * FROM salud_colector ORDER BY red, componente")


class TrabajosRepo:
    def __init__(self, db):
        self.db = db

    def crear(self, id_, redes):
        self.db.ejecutar(
            "INSERT INTO trabajos_recalibracion (id,estado,redes,inicio,progreso,etapa,log_tail) VALUES (?,?,?,?,0,?,?)",
            (id_, "en_curso", json.dumps(redes), ahora(), "inicio", ""))

    def actualizar(self, id_, **campos):
        if not campos:
            return
        sets = ",".join(f"{k}=?" for k in campos)
        self.db.ejecutar(f"UPDATE trabajos_recalibracion SET {sets} WHERE id=?", (*campos.values(), id_))

    def obtener(self, id_):
        return self.db.uno("SELECT * FROM trabajos_recalibracion WHERE id=?", (id_,))

    def ultimo(self):
        return self.db.uno("SELECT * FROM trabajos_recalibracion ORDER BY inicio DESC LIMIT 1")

    def marcar_huerfanos(self):
        self.db.ejecutar(
            "UPDATE trabajos_recalibracion SET estado='interrumpido', fin=? WHERE estado='en_curso'", (ahora(),))


class RecomendacionesRepo:
    def __init__(self, db):
        self.db = db

    def registrar(self, entrada, modo, version, resultado):
        self.db.ejecutar(
            "INSERT INTO recomendaciones (entrada_json,modo,version_perfil,resultado_json,ts) VALUES (?,?,?,?,?)",
            (json.dumps(entrada), modo, version, json.dumps(resultado), ahora()))

    def recientes(self, limite=20):
        return self.db.consultar("SELECT id,entrada_json,modo,version_perfil,ts FROM recomendaciones "
                                 "ORDER BY id DESC LIMIT ?", (limite,))


class RedesRepo:
    def __init__(self, db):
        self.db = db

    def sembrar(self, definiciones):
        for d in definiciones:
            self.db.ejecutar(
                "INSERT OR REPLACE INTO redes (id,nombre,responsable,endpoints,activa) VALUES (?,?,?,?,1)",
                (d["id"], d["nombre"], d["responsable"], json.dumps(d["endpoints"])))


def _b(v):
    return None if v is None else int(bool(v))
