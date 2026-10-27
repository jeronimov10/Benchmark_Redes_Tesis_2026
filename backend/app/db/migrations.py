"""Migraciones SQL versionadas del esquema SQLite; cada elemento de MIGRACIONES sube user_version en uno."""

MIGRACIONES = [
    """
    CREATE TABLE redes (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        responsable TEXT NOT NULL,
        endpoints TEXT NOT NULL,
        activa INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE muestras_bloque (
        red TEXT NOT NULL,
        numero INTEGER NOT NULL,
        ts REAL NOT NULL,
        productor TEXT,
        gas_usado REAL,
        gas_limite REAL,
        n_tx INTEGER,
        fuente TEXT,
        recogido_en REAL NOT NULL,
        PRIMARY KEY (red, numero)
    );
    CREATE INDEX ix_bloque_ts ON muestras_bloque (red, ts);
    CREATE TABLE muestras_tx (
        red TEXT NOT NULL,
        hash TEXT NOT NULL,
        bloque INTEGER,
        ts REAL NOT NULL,
        fee_usd REAL,
        precio_usado REAL,
        ocupacion REAL,
        gas_usado REAL,
        estado_ok INTEGER,
        patrocinada INTEGER,
        memo INTEGER,
        multi_transfer INTEGER,
        multi_activo INTEGER,
        tiene_transfer INTEGER,
        recogido_en REAL NOT NULL,
        PRIMARY KEY (red, hash)
    );
    CREATE INDEX ix_tx_ts ON muestras_tx (red, ts);
    CREATE TABLE muestras_finalidad (
        red TEXT NOT NULL,
        bloque INTEGER NOT NULL,
        tau_1 REAL NOT NULL,
        tau_f REAL NOT NULL,
        delta_s REAL NOT NULL,
        PRIMARY KEY (red, bloque)
    );
    CREATE INDEX ix_fin_ts ON muestras_finalidad (red, tau_f);
    CREATE TABLE lecturas_estado (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        red TEXT NOT NULL,
        clave TEXT NOT NULL,
        valor_json TEXT NOT NULL,
        ts REAL NOT NULL
    );
    CREATE INDEX ix_estado ON lecturas_estado (red, clave, ts);
    CREATE TABLE metricas_vivo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        red TEXT NOT NULL,
        metrica TEXT NOT NULL,
        valor REAL,
        sigma REAL,
        unidad TEXT,
        estado TEXT NOT NULL,
        n INTEGER,
        ventana_s REAL,
        ts REAL NOT NULL,
        fuente TEXT,
        nota TEXT,
        cota_inferior INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX ix_metricas ON metricas_vivo (red, metrica, ts);
    CREATE TABLE perfiles_base (
        red TEXT NOT NULL,
        metrica TEXT NOT NULL,
        valor REAL,
        sigma REAL,
        nota TEXT,
        cota_inferior INTEGER NOT NULL DEFAULT 0,
        origen TEXT NOT NULL,
        version INTEGER NOT NULL,
        ts REAL NOT NULL,
        PRIMARY KEY (red, metrica)
    );
    CREATE TABLE salud_colector (
        red TEXT NOT NULL,
        componente TEXT NOT NULL,
        ultimo_ok REAL,
        ultimo_error REAL,
        error TEXT,
        latencia_ms REAL,
        fallos_consecutivos INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (red, componente)
    );
    CREATE TABLE trabajos_recalibracion (
        id TEXT PRIMARY KEY,
        estado TEXT NOT NULL,
        redes TEXT,
        inicio REAL NOT NULL,
        fin REAL,
        progreso REAL NOT NULL DEFAULT 0,
        etapa TEXT,
        log_tail TEXT
    );
    CREATE TABLE recomendaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entrada_json TEXT NOT NULL,
        modo TEXT NOT NULL,
        version_perfil TEXT NOT NULL,
        resultado_json TEXT NOT NULL,
        ts REAL NOT NULL
    );
    CREATE TABLE meta (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE anclajes (
        red TEXT NOT NULL,
        l1_tx TEXT NOT NULL,
        log_index INTEGER NOT NULL,
        l1_bloque INTEGER NOT NULL,
        l1_ts REAL NOT NULL,
        l2_desde INTEGER,
        l2_hasta INTEGER,
        costo_eth REAL,
        costo_usd REAL,
        precio_eth_usd REAL,
        recogido_en REAL NOT NULL,
        PRIMARY KEY (red, l1_tx, log_index)
    );
    CREATE INDEX ix_anclaje_ts ON anclajes (red, l1_ts);
    """,
]
