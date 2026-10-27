"""Registro de las seis redes monitoreadas: responsable, fuente de datos, metricas calculadas en vivo y metricas que solo existen en la
linea base (con la razon exacta). Es la unica tabla que hay que ampliar para anadir una red."""

REDES = {
    "polygon": {
        "nombre": "Polygon PoS", "responsable": "Dilan", "familia": "evm",
        "fuente": "JSON-RPC publico (polygon.publicnode.com) + checkpoints en Ethereum",
        "metricas_vivo": ["A1", "A2", "A3", "A4", "B1", "B2", "B2b", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "B3": "caudal sostenido de una hora sobre 90 dias; exige cobertura continua de la ventana, que el sondeo no tiene",
            "D2": "la definicion estricta de referencia de conciliacion de la tesis no esta publicada; no se reproduce desde recibos",
            "D3": "la lista de intercambios que la tesis excluye no esta publicada; no se reproduce desde recibos",
        },
    },
    "celo": {
        "nombre": "Celo", "responsable": "Dilan", "familia": "evm",
        "fuente": "JSON-RPC publico (forno.celo.org) + juegos de disputa en Ethereum",
        "metricas_vivo": ["A1", "A2", "A3", "A4", "B1", "B2", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "B2b": "requiere la resolucion de cada juego de disputa (3,5 dias): no implementada en vivo",
            "B3": "caudal sostenido de una hora sobre 90 dias; exige cobertura continua de la ventana, que el sondeo no tiene",
            "D2": "la definicion de referencia de la tesis no esta publicada",
            "D3": "la lista de intercambios excluidos no esta publicada",
        },
    },
    "arbitrum": {
        "nombre": "Arbitrum One", "responsable": "Dilan", "familia": "evm",
        "fuente": "JSON-RPC publico (arb1.arbitrum.io) + lotes del secuenciador en Ethereum",
        "metricas_vivo": ["A1", "A2", "A3", "A4", "B1", "B2", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "B2b": "requiere emparejar creacion y confirmacion de aserciones (6,4 dias): no implementada en vivo",
            "B3": "caudal sostenido de una hora sobre 90 dias; exige cobertura continua de la ventana, que el sondeo no tiene",
            "D2": "la definicion de referencia de la tesis no esta publicada",
            "D3": "la lista de intercambios excluidos no esta publicada",
        },
    },
    "tempo": {
        "nombre": "Tempo", "responsable": "Jeronimo", "familia": "tempo", "fuente": "JSON-RPC (rpc.tempo.xyz)",
        "metricas_vivo": ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "C4", "C5", "D1", "D2", "D3"],
        "metricas_base": {},
    },
    "aptos": {
        "nombre": "Aptos", "responsable": "Jeronimo", "familia": "aptos", "fuente": "REST (api.mainnet.aptoslabs.com)",
        "metricas_vivo": ["A1", "A2", "A3", "B1", "B3", "C1", "C2", "C4", "D1", "D3"],
        "metricas_base": {
            "B2": "bloques de ~20 ms mas rapidos que un round-trip HTTP: imposible por sondeo HTTP (D1 del plan)",
            "C3": "con bloques de ~20 ms el muestreo no cubre los pares consecutivos necesarios para detectar huecos (cobertura < 0,9)",
            "D2": "definicion de referencia apta (A-5) sin fijar por escrito; la muestra esta dominada por trading de derivados",
            "C5": "la definicion del benchmark (publicaciones de modulos de cualquier cuenta) no mide mutabilidad de la ruta de pago",
        },
    },
    "canton": {
        "nombre": "Canton", "responsable": "Jeronimo", "familia": "canton", "fuente": "Scan API (api.cantonnodes.com)",
        "metricas_vivo": ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "C4", "C5", "D2", "D3"],
        "metricas_base": {
            "D1": "sujeto declarado: no aplica por arquitectura",
        },
    },
}

REDES_TEMPO_APTOS_CANTON = ("tempo", "aptos", "canton")


def definiciones():
    return [{"id": k, "nombre": v["nombre"], "responsable": v["responsable"], "endpoints": {"fuente": v["fuente"]}}
            for k, v in REDES.items()]
