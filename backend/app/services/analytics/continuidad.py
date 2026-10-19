"""Continuidad (C3) acumulada de forma incremental: cada ciclo de muestreo resume sus pares consecutivos (conteo, suma, mediana y huecos
grandes) en SQLite, de modo que la ventana de 14 dias no exige conservar cada bloque. C3 = 1 - fraccion del tiempo en huecos mayores
que 10 veces la cadencia mediana."""

import statistics as st

from ...models.dominio import EstadoMetrica, MetricaValor

FACTOR_HUECO = 10
FACTOR_CANDIDATO = 3
COBERTURA_MIN = 0.9
N_MIN_PARES = 100


def resumen_ciclo(puntos, previo, exigir_consecutivos):
    secuencia = ([previo] if previo else []) + list(puntos)
    secuencia = [p for p in secuencia if p is not None]
    saltados = 0
    deltas = []
    for (na, ta), (nb, tb) in zip(secuencia, secuencia[1:]):
        if tb < ta:
            continue
        if exigir_consecutivos and nb != na + 1:
            saltados += max(nb - na - 1, 1)
            continue
        deltas.append(tb - ta)
    if not deltas:
        return {"n": 0, "saltados": saltados, "suma": 0.0, "mediana": None, "grandes": [],
                "desde": secuencia[0][1] if secuencia else None, "hasta": secuencia[-1][1] if secuencia else None}
    med = st.median(deltas)
    return {"n": len(deltas), "saltados": saltados, "suma": sum(deltas), "mediana": med,
            "grandes": [d for d in deltas if d > FACTOR_CANDIDATO * med], "desde": secuencia[0][1], "hasta": secuencia[-1][1]}


def metrica_c3(ctx, red, fuente):
    ventana = ctx.settings.ventana_continuidad_s
    hist = ctx.estado.historial(red, "c3_ciclo", ctx.ahora - ventana)

    def vacia(razon, estado):
        return MetricaValor(red=red, metrica="C3", unidad="%", estado=estado, ventana_s=ventana, ts=ctx.ahora,
                            fuente=fuente, nota=razon)

    datos = [h for h, _ in hist if h["n"] > 0]
    if not datos:
        return vacia("sin pares consecutivos observados", EstadoMetrica.INSUFICIENTE)
    n = sum(h["n"] for h in datos)
    saltados = sum(h["saltados"] for h, _ in hist)
    cobertura = n / (n + saltados)
    if cobertura < COBERTURA_MIN:
        return vacia(f"muestreo insuficiente para detectar huecos (cobertura {cobertura:.2f} < {COBERTURA_MIN})",
                     EstadoMetrica.NO_COMPUTABLE)
    mediana = st.median([h["mediana"] for h in datos])
    umbral = FACTOR_HUECO * mediana
    suma = sum(h["suma"] for h in datos)
    huecos = sum(d for h in datos for d in h["grandes"] if d > umbral)
    valor = (1 - huecos / suma) * 100 if suma else None
    cubierto = hist[-1][0]["hasta"] - hist[0][0]["desde"]
    completo = cubierto >= ventana * 0.99
    estado = EstadoMetrica.VALIDA if completo and n >= N_MIN_PARES else EstadoMetrica.INSUFICIENTE
    ultimo = hist[-1][1]
    if estado == EstadoMetrica.VALIDA and ctx.ahora - ultimo > ctx.settings.obsolescencia_s:
        estado = EstadoMetrica.OBSOLETA
    return MetricaValor(red=red, metrica="C3", valor=valor, sigma=0.0, unidad="%", estado=estado, n=n, ventana_s=ventana,
                        ts=ctx.ahora, fuente=fuente,
                        nota=f"1 - fraccion de tiempo en huecos > {FACTOR_HUECO}x la cadencia mediana ({mediana:.4f} s); "
                             f"cubierto {cubierto / 3600:.1f} h de {ventana / 3600:.0f} h; cobertura {cobertura:.2f}")
