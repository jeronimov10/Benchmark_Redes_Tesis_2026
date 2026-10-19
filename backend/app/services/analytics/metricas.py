"""Calculo de metricas en vivo por red a partir de las muestras en SQLite (ventanas moviles configurables). Replica las definiciones de
los scripts del benchmark (Tempo, Aptos, Canton) y de la metodologia de Polygon, Celo y Arbitrum. Lo que no se puede reproducir
fielmente no se emite: el perfil efectivo conserva entonces la linea base."""

import math
import random
import statistics as st
from collections import Counter
from dataclasses import dataclass

from ...models.dominio import EstadoMetrica, MetricaValor
from ...pipelines.validators.validadores import estado_por_muestras
from .continuidad import metrica_c3

N_MIN = {"B1": 30, "B2": 100, "B3": 30, "C1": 100, "C3": 100, "C4": 50, "A1": 30, "A2": 30, "A3": 50,
         "D1": 30, "D2": 30, "D3": 30}
TPS_REQUERIDO_MODELO = 18.0
TPS_REQUERIDO_BENCHMARK = 48.0
UMBRAL_HUECO = 10
REMUESTREOS_BOOTSTRAP = 200
COBERTURA_MIN_CONTINUIDAD = 0.9
EVM = ("polygon", "celo", "arbitrum")


@dataclass
class Contexto:
    settings: object
    muestras: object
    estado: object
    ahora: float


def percentil_ceil(valores, p):
    s = sorted(valores)
    idx = min(len(s) - 1, math.ceil(p * len(s)) - 1)
    return s[idx]


def error_estandar(valores, estadistico, semilla=7):
    if len(valores) < 10:
        return None
    rng = random.Random(semilla)
    n = len(valores)
    est = [estadistico([valores[rng.randrange(n)] for _ in range(n)]) for _ in range(REMUESTREOS_BOOTSTRAP)]
    return st.pstdev(est)


def herfindahl(pesos):
    total = sum(pesos)
    return sum((p / total) ** 2 for p in pesos) if total else None


def min_operadores_mayoria(pesos):
    total = sum(pesos)
    if not total:
        return None
    acum = 0.0
    for i, w in enumerate(sorted(pesos, reverse=True), start=1):
        acum += w
        if acum / total > 0.5:
            return i
    return len(pesos)


def regresion_lineal(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    beta = sxy / sxx
    r2 = (sxy * sxy) / (sxx * syy) if syy else 0.0
    return beta, r2


def _mv(ctx, red, metrica, valor, unidad, n, ventana_s, fuente, nota="", sigma=None, ts_ultima=None, n_min=None,
        estado=None, cota=False):
    if estado is None:
        if valor is None:
            estado = EstadoMetrica.NO_COMPUTABLE
        else:
            estado = estado_por_muestras(n, n_min if n_min is not None else N_MIN.get(metrica, 1), ts_ultima,
                                         ctx.ahora, ctx.settings.obsolescencia_s)
    return MetricaValor(red=red, metrica=metrica, valor=valor, sigma=sigma, unidad=unidad, estado=estado, n=n,
                        ventana_s=ventana_s, ts=ctx.ahora, fuente=fuente, nota=nota, cota_inferior=cota)


def _vacia(ctx, red, metrica, razon, unidad="", fuente="", estado=EstadoMetrica.NO_COMPUTABLE):
    return _mv(ctx, red, metrica, None, unidad, 0, None, fuente, razon, estado=estado)


def pares_consecutivos(bloques):
    pares = []
    for a, b in zip(bloques, bloques[1:]):
        if b["numero"] == a["numero"] + 1 and b["ts"] >= a["ts"]:
            pares.append((a, b))
    return pares


def m_b1_bloques(ctx, red, fuente):
    ventana = ctx.settings.ventana_flujo_s
    bloques = ctx.muestras.bloques_desde(red, ctx.ahora - ventana)
    deltas = [b["ts"] - a["ts"] for a, b in pares_consecutivos(bloques)]
    if not deltas:
        return _mv(ctx, red, "B1", None, "s", 0, ventana, fuente, "sin pares de bloques consecutivos en la ventana")
    return _mv(ctx, red, "B1", percentil_ceil(deltas, 0.95), "s", len(deltas), ventana, fuente,
               "p95 de la diferencia entre marcas de tiempo de bloques consecutivos",
               sigma=error_estandar(deltas, lambda v: percentil_ceil(v, 0.95)), ts_ultima=bloques[-1]["ts"])


def m_c1_produccion(ctx, red, fuente):
    ventana = ctx.settings.ventana_distribucion_s
    bloques = ctx.muestras.bloques_desde(red, ctx.ahora - ventana)
    cuenta = Counter(b["productor"] for b in bloques if b["productor"])
    if not cuenta:
        return [_vacia(ctx, red, "C1", "los bloques no exponen productor", fuente=fuente),
                _vacia(ctx, red, "C2", "los bloques no exponen productor", fuente=fuente)]
    pesos = list(cuenta.values())
    nota = f"{len(cuenta)} productores en {sum(pesos)} bloques muestreados (muestra, no censo)"
    ts = bloques[-1]["ts"]
    return [_mv(ctx, red, "C1", herfindahl(pesos), "indice", sum(pesos), ventana, fuente, nota, sigma=0.0, ts_ultima=ts),
            _mv(ctx, red, "C2", float(min_operadores_mayoria(pesos)), "conteo", sum(pesos), ventana, fuente, nota,
                sigma=0.0, ts_ultima=ts, n_min=N_MIN["C1"])]


def _filas_pago(ctx, red, ventana, solo_transfer):
    filas = ctx.muestras.txs_desde(red, ctx.ahora - ventana)
    return [f for f in filas if f["tiene_transfer"]] if solo_transfer else filas


def m_costos(ctx, red, fuente, solo_transfer):
    ventana = ctx.settings.ventana_distribucion_s
    filas = [f for f in _filas_pago(ctx, red, ventana, solo_transfer) if f["fee_usd"] is not None]
    if not filas:
        return [_vacia(ctx, red, "A1", "sin costos en USD en la ventana", "USD", fuente),
                _vacia(ctx, red, "A2", "sin costos en USD en la ventana", "razon", fuente)]
    costos = [f["fee_usd"] for f in filas]
    ts = max(f["ts"] for f in filas)
    mediana = st.median(costos)
    p95 = percentil_ceil(costos, 0.95)
    precio = next((f["precio_usado"] for f in reversed(filas) if f["precio_usado"]), None)
    nota = f"n={len(costos)} transferencias; precio USD del token de comision {precio}"
    out = [_mv(ctx, red, "A1", mediana, "USD", len(costos), ventana, fuente, nota,
               sigma=error_estandar(costos, st.median), ts_ultima=ts)]
    if mediana > 0:
        out.append(_mv(ctx, red, "A2", p95 / mediana, "razon p95/mediana", len(costos), ventana, fuente, nota,
                       sigma=error_estandar(costos, lambda v: percentil_ceil(v, 0.95) / st.median(v)), ts_ultima=ts))
    else:
        out.append(_vacia(ctx, red, "A2", "mediana de costo cero", "razon", fuente))
    return out


def m_a3_ocupacion(ctx, red, fuente):
    ventana = ctx.settings.ventana_distribucion_s
    filas = [f for f in ctx.muestras.txs_desde(red, ctx.ahora - ventana)
             if f["fee_usd"] and f["fee_usd"] > 0 and f["ocupacion"] is not None]
    xs = [f["ocupacion"] for f in filas]
    ys = [math.log(f["fee_usd"]) for f in filas]
    reg = regresion_lineal(xs, ys) if len(xs) >= N_MIN["A3"] else None
    if reg is None:
        return _mv(ctx, red, "A3", None, "indice", len(xs), ventana, fuente, "regresion no estimable (pocos datos o sin variacion de ocupacion)",
                   estado=EstadoMetrica.INSUFICIENTE if len(xs) < N_MIN["A3"] else EstadoMetrica.NO_COMPUTABLE)
    beta, r2 = reg
    return _mv(ctx, red, "A3", beta, "indice", len(xs), ventana, fuente,
               f"pendiente de ln(costo) sobre ocupacion de bloque; R2={r2:.3f}", ts_ultima=max(f["ts"] for f in filas))


def m_a3_trafico_canton(ctx, red, fuente, cubeta_s=10):
    ventana = ctx.settings.ventana_distribucion_s
    filas = [f for f in ctx.muestras.txs_desde(red, ctx.ahora - ventana) if f["gas_usado"] and f["gas_usado"] > 0]
    if not filas:
        return _vacia(ctx, red, "A3", "sin costos de trafico", "indice", fuente)
    t0 = filas[0]["ts"]
    tot = Counter()
    for f in filas:
        tot[int((f["ts"] - t0) // cubeta_s)] += f["gas_usado"] * ctx.settings.canton_submuestreo
    xs = [tot[int((f["ts"] - t0) // cubeta_s)] for f in filas]
    ys = [math.log(f["gas_usado"]) for f in filas]
    reg = regresion_lineal(xs, ys) if len(xs) >= N_MIN["A3"] else None
    if reg is None:
        return _mv(ctx, red, "A3", None, "indice", len(xs), ventana, fuente, "regresion no estimable",
                   estado=EstadoMetrica.INSUFICIENTE)
    return _mv(ctx, red, "A3", reg[0], "indice", len(xs), ventana, fuente,
               f"pendiente de ln(costo) sobre trafico total del sincronizador por cubeta de {cubeta_s} s; R2={reg[1]:.3f}",
               ts_ultima=filas[-1]["ts"])


def m_c4(ctx, red, fuente, solo_transfer=False, extra_nota=""):
    ventana = ctx.settings.ventana_distribucion_s
    filas = [f for f in ctx.muestras.txs_desde(red, ctx.ahora - ventana) if f["estado_ok"] is not None]
    if not filas:
        return _vacia(ctx, red, "C4", "sin transacciones con estado", "fraccion", fuente)
    fallos = sum(1 for f in filas if not f["estado_ok"])
    return _mv(ctx, red, "C4", fallos / len(filas), "fraccion", len(filas), ventana, fuente,
               f"{fallos} fallos de {len(filas)}{extra_nota}", sigma=0.0, ts_ultima=max(f["ts"] for f in filas))


def m_fraccion(ctx, red, metrica, campo, fuente, nota, denominador_transfer=True):
    ventana = ctx.settings.ventana_distribucion_s
    filas = ctx.muestras.txs_desde(red, ctx.ahora - ventana)
    if denominador_transfer:
        filas = [f for f in filas if f["tiene_transfer"]]
    filas = [f for f in filas if f[campo] is not None]
    if not filas:
        return _vacia(ctx, red, metrica, "sin muestras con el campo requerido", "fraccion", fuente)
    k = sum(1 for f in filas if f[campo])
    return _mv(ctx, red, metrica, k / len(filas), "fraccion", len(filas), ventana, fuente, f"{k} de {len(filas)}; {nota}",
               sigma=0.0, ts_ultima=max(f["ts"] for f in filas))


def m_b2_finalidad(ctx, red, fuente, exigir_ventana_completa):
    ventana = ctx.settings.ventana_finalidad_s
    filas = ctx.muestras.finalidad_desde(red, ctx.ahora - ventana)
    deltas = [f["delta_s"] for f in filas]
    if not deltas:
        return _mv(ctx, red, "B2", None, "s", 0, ventana, fuente, "sin muestras de finalidad", estado=EstadoMetrica.INSUFICIENTE)
    span = filas[-1]["tau_f"] - filas[0]["tau_f"]
    estado = None
    if exigir_ventana_completa and span < ventana * 0.99:
        estado = EstadoMetrica.INSUFICIENTE
    return _mv(ctx, red, "B2", st.median(deltas), "s", len(deltas), ventana, fuente,
               f"mediana de tau_F - tau_1; cubierto {span / 3600:.1f} h de {ventana / 3600:.0f} h",
               sigma=error_estandar(deltas, st.median), ts_ultima=filas[-1]["tau_f"], estado=estado, n_min=N_MIN["B2"])


def _estado_reciente(ctx, red, clave):
    valor, ts = ctx.estado.ultima(red, clave)
    if valor is None:
        return None, None, "sin lectura de estado"
    if ctx.ahora - ts > ctx.settings.obsolescencia_estado_s:
        return valor, ts, f"lectura de estado obsoleta ({int(ctx.ahora - ts)} s)"
    return valor, ts, None


def m_concentracion_consenso(ctx, red, fuente, pesos):
    ts = ctx.ahora
    return [_mv(ctx, red, "C1", herfindahl(pesos), "indice", len(pesos), None, fuente,
                "HHI del peso de consenso (C1b del plan)", sigma=0.0, ts_ultima=ts, n_min=1),
            _mv(ctx, red, "C2", float(min_operadores_mayoria(pesos)), "conteo", len(pesos), None, fuente,
                "minimo de operadores con mas de la mitad del peso", sigma=0.0, ts_ultima=ts, n_min=1)]


def _mediana_tx_gas(ctx, red, ventana):
    g = [f["gas_usado"] for f in ctx.muestras.txs_desde(red, ctx.ahora - ventana) if f["gas_usado"]]
    return (st.median(g), len(g)) if g else (None, 0)


def calcular_tempo(ctx):
    red, s = "tempo", ctx.settings
    f = "tempo:rpc"
    out = [m_b1_bloques(ctx, red, f), metrica_c3(ctx, red, f)]
    out += m_costos(ctx, red, f, solo_transfer=False)
    out.append(m_a3_ocupacion(ctx, red, f))
    out.append(m_c4(ctx, red, f))
    out.append(m_fraccion(ctx, red, "D1", "patrocinada", f, "recibos con feePayer", denominador_transfer=False))
    out.append(m_fraccion(ctx, red, "D2", "memo", f, "evento TransferWithMemo sobre transferencias"))
    out.append(m_fraccion(ctx, red, "D3", "multi_transfer", f, "transacciones con mas de una transferencia"))
    out.append(m_b2_finalidad(ctx, red, "tempo:finalized", exigir_ventana_completa=True))
    val, ts, err = _estado_reciente(ctx, red, "validadores")
    if val and not err:
        n = val["n"]
        out += [_mv(ctx, red, "C1", 1 / n, "indice", n, None, "tempo:ValidatorConfigV2",
                    "voto igualitario (la interfaz no expone pesos): C1b=1/N", sigma=0.0, ts_ultima=ts, n_min=1),
                _mv(ctx, red, "C2", float(n // 2 + 1), "conteo", n, None, "tempo:ValidatorConfigV2",
                    "voto igualitario: operadores necesarios para mayoria", sigma=0.0, ts_ultima=ts, n_min=1)]
    else:
        out += [_vacia(ctx, red, "C1", err or "sin lectura", fuente="tempo:ValidatorConfigV2", estado=EstadoMetrica.FALLIDA),
                _vacia(ctx, red, "C2", err or "sin lectura", fuente="tempo:ValidatorConfigV2", estado=EstadoMetrica.FALLIDA)]
    fs, ts_fs, err = _estado_reciente(ctx, red, "fork_schedule")
    if fs and not err:
        ventana = s.ventana_continuidad_s
        cuenta = [x for x in fs["schedule"] if x["name"] != "T0" and ctx.ahora - ventana <= x["activationTime"] <= ctx.ahora]
        out.append(_mv(ctx, red, "C5", float(len(cuenta)), "conteo", len(fs["schedule"]), ventana, "tempo:tempo_forkSchedule",
                       f"activaciones de fork en la ventana: {[x['name'] for x in cuenta]}; fork activo {fs.get('active')}",
                       sigma=0.0, ts_ultima=ts_fs, n_min=1))
    else:
        out.append(_vacia(ctx, red, "C5", err or "sin lectura", fuente="tempo:tempo_forkSchedule", estado=EstadoMetrica.FALLIDA))
    cfg, ts_cfg = None, None
    bloques = ctx.muestras.bloques_desde(red, ctx.ahora - s.ventana_distribucion_s)
    gas_med, n_gas = _mediana_tx_gas(ctx, red, s.ventana_distribucion_s)
    pares = pares_consecutivos(bloques)
    if bloques and gas_med and len(pares) >= N_MIN["B3"]:
        gl = sum(b["gas_limite"] for b in bloques) / len(bloques)
        cad = st.median([b["ts"] - a["ts"] for a, b in pares])
        tps = (gl / gas_med) / cad
        out.append(_mv(ctx, red, "B3", tps / TPS_REQUERIDO_MODELO, "razon", n_gas, s.ventana_distribucion_s, f,
                       f"(gasLimit medio {gl:.0f} / gas mediano por tx {gas_med:.0f}) / cadencia mediana {cad:.3f}s = {tps:.0f} TPS; "
                       f"sobre {TPS_REQUERIDO_MODELO:.0f} TPS requeridos", ts_ultima=bloques[-1]["ts"], n_min=N_MIN["B3"]))
    else:
        out.append(_mv(ctx, red, "B3", None, "razon", n_gas, s.ventana_distribucion_s, f, "faltan bloques o recibos",
                       estado=EstadoMetrica.INSUFICIENTE))
    return out


def calcular_aptos(ctx):
    red, s = "aptos", ctx.settings
    f = "aptos:rest"
    out = [m_b1_bloques(ctx, red, f), metrica_c3(ctx, red, f)]
    costos = m_costos(ctx, red, f, solo_transfer=False)
    precio, ts_precio, _ = _estado_reciente(ctx, red, "precio_apt")
    if precio and precio.get("congelado"):
        for m in costos:
            m.nota += f" | precio_congelado: Pyth on-chain publicado en {int(precio['publicado'])} (edad {int(ctx.ahora - precio['publicado'])} s)"
    out += costos
    out.append(m_a3_ocupacion(ctx, red, f))
    out.append(m_c4(ctx, red, f))
    out.append(m_fraccion(ctx, red, "D1", "patrocinada", f, "transacciones con fee payer", denominador_transfer=False))
    out.append(m_fraccion(ctx, red, "D3", "multi_transfer", f, "transacciones con mas de un evento de Fungible Asset"))
    out.append(_vacia(ctx, red, "B2", "los bloques (~20 ms) son mas rapidos que un round-trip HTTP: no es medible por sondeo HTTP",
                      "s", "aptos:rest"))
    out.append(_vacia(ctx, red, "D2", "definicion de referencia apta (A-5) sin fijar por escrito", "fraccion", "aptos:rest"))
    val, ts, err = _estado_reciente(ctx, red, "validator_set")
    if val and not err:
        out += m_concentracion_consenso(ctx, red, "aptos:ValidatorSet", val["pesos"])
    else:
        out += [_vacia(ctx, red, m, err or "sin lectura", fuente="aptos:ValidatorSet", estado=EstadoMetrica.FALLIDA) for m in ("C1", "C2")]
    cfg, ts_cfg, err = _estado_reciente(ctx, red, "execution_config")
    bloques = ctx.muestras.bloques_desde(red, ctx.ahora - s.ventana_distribucion_s)
    gas_med, n_gas = _mediana_tx_gas(ctx, red, s.ventana_distribucion_s)
    pares = pares_consecutivos(bloques)
    if cfg and not err and gas_med and len(pares) >= 10:
        cad = st.median([b["ts"] - a["ts"] for a, b in pares])
        tps = (cfg["limite_gas"] / gas_med) / cad
        out.append(_mv(ctx, red, "B3", tps / TPS_REQUERIDO_MODELO, "razon", n_gas, s.ventana_distribucion_s, "aptos:ExecutionConfig",
                       f"(limite efectivo de gas de bloque {cfg['limite_gas']} / gas mediano por tx {gas_med:.0f}) / cadencia mediana "
                       f"{cad:.4f}s = {tps:.0f} TPS; simplificacion declarada: no pondera execution/io gas por separado",
                       ts_ultima=bloques[-1]["ts"], n_min=N_MIN["B3"]))
    else:
        out.append(_mv(ctx, red, "B3", None, "razon", n_gas, s.ventana_distribucion_s, "aptos:ExecutionConfig",
                       err or "faltan bloques, transacciones o configuracion", estado=EstadoMetrica.INSUFICIENTE))
    return out


def calcular_canton(ctx):
    red, s = "canton", ctx.settings
    f = "canton:scan"
    out = []
    filas = ctx.muestras.finalidad_desde(red, ctx.ahora - s.ventana_distribucion_s)
    lat = [x["delta_s"] for x in filas]
    if lat:
        ts = filas[-1]["tau_f"]
        out.append(_mv(ctx, red, "B1", percentil_ceil(lat, 0.95), "s", len(lat), s.ventana_distribucion_s, f,
                       "p95 de finalization_time - record_time del veredicto",
                       sigma=error_estandar(lat, lambda v: percentil_ceil(v, 0.95)), ts_ultima=ts, n_min=N_MIN["B1"]))
        out.append(_mv(ctx, red, "B2", st.median(lat), "s", len(lat), s.ventana_distribucion_s, f,
                       "mediana de finalization_time - record_time del veredicto (B1 y B2 coinciden en Canton)",
                       sigma=error_estandar(lat, st.median), ts_ultima=ts, n_min=N_MIN["B1"]))
    else:
        out += [_vacia(ctx, red, m, "sin veredictos en la ventana", "s", f, EstadoMetrica.INSUFICIENTE) for m in ("B1", "B2")]
    out += m_costos(ctx, red, f, solo_transfer=False)
    out.append(m_a3_trafico_canton(ctx, red, f))
    out.append(m_c4(ctx, red, f, extra_nota=" veredictos rechazados"))
    out.append(m_fraccion(ctx, red, "D2", "memo", f, "transferencias con meta/referencia"))
    out.append(m_fraccion(ctx, red, "D3", "multi_transfer", f, "transferencias con mas de una salida"))
    dso, ts_dso, err = _estado_reciente(ctx, red, "dso")
    if dso and not err:
        out += [m for m in m_concentracion_consenso(ctx, red, "canton:DsoRules", dso["pesos"])]
        tx_bytes = [x["gas_usado"] for x in ctx.muestras.txs_desde(red, ctx.ahora - s.ventana_distribucion_s) if x["gas_usado"]]
        if tx_bytes:
            tasa = dso["burst_bytes"] / dso["burst_ventana_s"]
            tps = tasa / st.median(tx_bytes)
            out.append(_mv(ctx, red, "B3", tps / TPS_REQUERIDO_MODELO, "razon", len(tx_bytes), s.ventana_distribucion_s, "canton:AmuletRules",
                           f"baseRateTrafficLimits ({dso['burst_bytes']:.0f} B / {dso['burst_ventana_s']:.0f} s) / bytes medianos por transferencia: "
                           f"asignacion gratuita POR MIEMBRO, no el techo agregado; probablemente subestima la capacidad real",
                           ts_ultima=ts_dso, n_min=N_MIN["B3"], cota=True))
    else:
        out += [_vacia(ctx, red, m, err or "sin lectura del DSO", fuente="canton:DsoRules", estado=EstadoMetrica.FALLIDA)
                for m in ("C1", "C2", "B3")]
    out.append(metrica_c3(ctx, red, "canton:latido ValidatorLicense_ReportActive"))
    hist = ctx.estado.historial(red, "c5_cambios", ctx.ahora - s.ventana_continuidad_s)
    if hist:
        cambios = sum(h["cambios"] for h, _ in hist)
        cubierto = hist[-1][0]["hasta"] - hist[0][0]["desde"]
        completo = cubierto >= s.ventana_continuidad_s * 0.99
        out.append(_mv(ctx, red, "C5", float(cambios), "conteo", len(hist), s.ventana_continuidad_s, f,
                       f"choices DsoRules_* no rutinarias; cubierto {cubierto / 3600:.1f} h de {s.ventana_continuidad_s / 3600:.0f} h",
                       sigma=0.0, ts_ultima=hist[-1][1], n_min=1, estado=None if completo else EstadoMetrica.INSUFICIENTE))
    else:
        out.append(_vacia(ctx, red, "C5", "sin lecturas de cambios estructurales", "conteo", f, EstadoMetrica.INSUFICIENTE))
    return out


def calcular_evm(ctx, red):
    s = ctx.settings
    f = f"{red}:rpc"
    out = [m_b1_bloques(ctx, red, f), metrica_c3(ctx, red, f)]
    out += m_c1_produccion(ctx, red, f)
    out += m_costos(ctx, red, f, solo_transfer=True)
    usdc, ts_u, err = _estado_reciente(ctx, red, "usdc_verificado")
    nota_tok = f" token de pago {usdc['direccion']}" if usdc else ""
    out.append(m_c4(ctx, red, f, extra_nota=f" (transacciones de pago a/desde USDC{nota_tok})"))
    out.append(m_fraccion(ctx, red, "D1", "patrocinada", f,
                          "transferencias con autorizacion firmada (EIP-3009), delegacion EIP-7702, EntryPoint ERC-4337 o feeCurrency"))
    hist = ctx.estado.historial(red, "proxy_impl", ctx.ahora - s.ventana_continuidad_s)
    if hist and all(h.get("impl") for h, _ in hist):
        impls = [h["impl"] for h, _ in hist]
        cambios = sum(1 for a, b in zip(impls, impls[1:]) if a != b)
        cubierto = hist[-1][1] - hist[0][1]
        completo = cubierto >= s.ventana_continuidad_s * 0.99
        out.append(_mv(ctx, red, "C5", float(cambios), "conteo", len(hist), s.ventana_continuidad_s, f"{red}:proxy_slot",
                       f"cambios de implementacion del proxy de USDC (ranura zeppelinos); cubierto {cubierto / 3600:.1f} h de "
                       f"{s.ventana_continuidad_s / 3600:.0f} h", sigma=0.0, ts_ultima=hist[-1][1], n_min=1,
                       estado=None if completo else EstadoMetrica.INSUFICIENTE))
    else:
        out.append(_vacia(ctx, red, "C5", "sin lecturas validas de la ranura de implementacion del proxy", "conteo", f,
                          EstadoMetrica.INSUFICIENTE))
    return out


def calcular_metricas(red, ctx):
    if red == "tempo":
        return calcular_tempo(ctx)
    if red == "aptos":
        return calcular_aptos(ctx)
    if red == "canton":
        return calcular_canton(ctx)
    if red in EVM:
        return calcular_evm(ctx, red)
    raise KeyError(red)
