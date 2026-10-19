"""Registro de las seis redes monitoreadas: responsable, fuente de datos, metricas calculadas en vivo y metricas que solo existen en la
linea base (con la razon exacta). Es la unica tabla que hay que ampliar para anadir una red."""

REDES = {
    "polygon": {
        "nombre": "Polygon PoS", "responsable": "Dilan", "familia": "evm", "fuente": "JSON-RPC publico (polygon.publicnode.com)",
        "metricas_vivo": ["A1", "A2", "B1", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "A3": "la regresion de la tesis exige un ajuste con R2 suficiente; la linea base la reporta no concluyente",
            "A4": "requiere el rastreador de anclaje en Ethereum (contratos de checkpoint verificados); no reproducible hoy",
            "B2": "tau_F depende del evento de anclaje en Ethereum que cubre cada bloque; rastreador no disponible",
            "B2b": "igual que B2",
            "B3": "caudal sostenido de una hora sobre 90 dias; no reproducible con una ventana corta",
            "D2": "definicion estricta de referencia de conciliacion de la tesis no reproducible desde recibos",
            "D3": "exclusion de intercambios de la tesis no reproducible desde recibos",
        },
    },
    "celo": {
        "nombre": "Celo", "responsable": "Dilan", "familia": "evm", "fuente": "JSON-RPC publico (forno.celo.org)",
        "metricas_vivo": ["A1", "A2", "B1", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "A3": "regresion no concluyente en la linea base", "A4": "rastreador de anclaje no disponible",
            "B2": "rastreador de anclaje no disponible", "B2b": "rastreador de anclaje no disponible",
            "B3": "caudal sostenido de una hora sobre 90 dias", "D2": "definicion de la tesis no reproducible",
            "D3": "definicion de la tesis no reproducible",
        },
    },
    "arbitrum": {
        "nombre": "Arbitrum One", "responsable": "Dilan", "familia": "evm", "fuente": "JSON-RPC publico (arb1.arbitrum.io)",
        "metricas_vivo": ["A1", "A2", "B1", "C1", "C2", "C3", "C4", "C5", "D1"],
        "metricas_base": {
            "A3": "regresion no concluyente en la linea base", "A4": "rastreador de anclaje no disponible",
            "B2": "rastreador de anclaje no disponible", "B2b": "rastreador de anclaje no disponible",
            "B3": "caudal sostenido de una hora sobre 90 dias", "D2": "definicion de la tesis no reproducible",
            "D3": "definicion de la tesis no reproducible",
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
