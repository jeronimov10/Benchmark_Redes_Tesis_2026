"""Validadores: chequeos de rango y unidades sobre muestras, y asignacion de estado (valida/insuficiente/obsoleta) a metricas."""

import math

from ...models.dominio import EstadoMetrica

LIMITE_FEE_USD = 1000.0


def numero_finito(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def fee_usd_valido(x):
    return numero_finito(x) and 0 <= x <= LIMITE_FEE_USD


def ocupacion_valida(x):
    return numero_finito(x) and 0 <= x <= 1.0


def timestamp_valido(ts, ahora, tolerancia_futuro_s=300):
    return numero_finito(ts) and ts > 1.4e9 and ts <= ahora + tolerancia_futuro_s


def estado_por_muestras(n, n_min, ts_ultima, ahora, obsolescencia_s):
    if n < n_min:
        return EstadoMetrica.INSUFICIENTE
    if ts_ultima is None or ahora - ts_ultima > obsolescencia_s:
        return EstadoMetrica.OBSOLETA
    return EstadoMetrica.VALIDA
