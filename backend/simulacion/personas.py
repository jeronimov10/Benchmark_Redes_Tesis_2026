"""Catalogo de los 12 perfiles del banco de usuarios simulados y generacion determinista de usuarios (monto y espera en escala logaritmica)."""

import math
import random
from dataclasses import dataclass

TRM = 4000.0


@dataclass(frozen=True)
class Persona:
    id: int
    nombre: str
    tipo: str
    necesidad: str
    moneda: str
    monto: tuple
    transfronterizo: bool
    espera_s: tuple
    irrevocabilidad: str


PERSONAS = (
    Persona(1, "Remesa familiar", "control", "Enviar a la familia con el menor costo", "USD", (200, 500), True, (1800, 7200), "baja"),
    Persona(2, "Tendero con QR", "control", "Cobrar en mostrador sin hacer esperar", "COP", (15000, 159456), False, (5, 20), "media"),
    Persona(3, "Tesoreria de alto valor", "control", "Mover grandes sumas con firmeza", "COP", (50e6, 200e6), False, (300, 1200), "alta"),
    Persona(4, "Microremesa", "hueco", "Enviar poco, donde cada dolar de costo pesa", "USD", (20, 100), True, (3600, 86400), "baja"),
    Persona(5, "Freelancer", "hueco", "Cobrar del exterior sin depender de un banco", "USD", (500, 5000), True, (3600, 86400), "media"),
    Persona(6, "E-commerce", "hueco", "Confirmar la orden en minutos", "COP", (100000, 2e6), False, (60, 600), "media"),
    Persona(7, "Nomina de pyme", "hueco", "Pagar salarios sin apuro y sin reversos", "COP", (1.5e6, 8e6), False, (3600, 14400), "media"),
    Persona(8, "Proveedor B2B", "hueco", "Liquidar facturas grandes en firme", "COP", (20e6, 80e6), False, (600, 3600), "alta"),
    Persona(9, "Importador", "hueco", "Pagar al exterior montos altos", "USD", (20000, 250000), True, (3600, 86400), "alta"),
    Persona(10, "Remesa urgente", "hueco", "Enviar una emergencia en segundos", "USD", (200, 500), True, (5, 60), "media"),
    Persona(11, "Liquidacion urgente", "hueco", "Cerrar una operacion grande casi de inmediato", "COP", (50e6, 500e6), False, (5, 30), "alta"),
    Persona(12, "Micropago de transporte", "fuera de rango", "Pagar un pasaje al instante", "COP", (3000, 10000), False, (1, 5), "baja"),
)

POR_ID = {p.id: p for p in PERSONAS}


def _log_uniforme(rng, lo, hi):
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


def usuario(persona, indice, semilla, trm=TRM):
    rng = random.Random(f"{semilla}:{persona.id}:{indice}")
    monto = _log_uniforme(rng, *persona.monto)
    monto_cop = monto * trm if persona.moneda == "USD" else monto
    return {
        "perfil": persona.id, "indice": indice, "monto_cop": round(monto_cop, 2),
        "transfronterizo": persona.transfronterizo, "espera_s": round(_log_uniforme(rng, *persona.espera_s), 2),
        "irrevocabilidad": persona.irrevocabilidad, "trm": trm,
    }


def usuarios(persona, desde, hasta, semilla, trm=TRM):
    return [usuario(persona, i, semilla, trm) for i in range(desde, hasta)]


def panel(por_perfil, semilla, trm=TRM):
    return [u for p in PERSONAS for u in usuarios(p, 0, por_perfil, semilla, trm)]
