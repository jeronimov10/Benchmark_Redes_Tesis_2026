#!/usr/bin/env python3
"""
Puente entre la app web y el modelo de recomendacion (modelo/modelo.py).

No reimplementa nada del modelo: lo importa y llama sus funciones. Lee una
peticion JSON por stdin y escribe la respuesta JSON por stdout, para que el
servidor de la app (Next.js) lo ejecute como subproceso sin bloquear.

Acciones:
  info         -> redes con perfil medido y fecha de la medicion.
  recomendar  -> modelo.recomendar() tal cual, mas el detalle por red que la
                  app usa para los semaforos (calculado con las funciones del
                  propio modelo: normalizar, puntuar, compuertas).
  interpretar  -> solo composicion y certidumbre (modelo.vector_caso +
                  modelo.interpolar), sin Monte Carlo. Para la vista previa.

Uso:
    echo '{"accion": "recomendar", "monto_cop": 1200000, ...}' | python recomendar.py
"""

import json
import sys
from pathlib import Path

DIR_MODELO = Path(__file__).resolve().parent.parent / "modelo"
sys.path.insert(0, str(DIR_MODELO))

import modelo  # noqa: E402

RUTA_PERFILES = DIR_MODELO / "perfiles.json"

# Texto que INTEGRACION.md exige mostrar junto a cada resultado.
MEDICION = "perfiles medidos en 90 días, octubre de 2026"

REPLICAS = 10000


def cargar_perfiles():
    # No se usa modelo.cargar_perfiles(): si falta el archivo, cae en perfiles
    # provisionales, y la app nunca debe recomendar con ellos.
    return json.loads(RUTA_PERFILES.read_text(encoding="utf-8"))


def nivel_certidumbre(kappa):
    # Cortes documentados en INTEGRACION.md ("Qué devuelve").
    return "alta" if kappa >= 0.75 else ("media" if kappa >= 0.45 else "baja")


class _ValorCentral:
    """Sustituye al generador aleatorio en modelo.puntuar(): cada metrica
    toma su valor medido, sin ruido. Da el puntaje del perfil en su centro."""

    def gauss(self, mu, sigma):
        return mu


def _contexto(e):
    a = modelo.vector_caso(e["monto_cop"], e["transfronterizo"], e["espera_s"],
                           e["irrevocabilidad"])
    lam, W, kappa, _ = modelo.interpolar(a)
    return lam, W, kappa, max(lam, key=lam.get), e["monto_cop"] / e["trm"]


def detalle_redes(perfiles, e):
    """Por red: cada metrica con su puntaje en [0,1] y los bloques en el valor
    central. Todo sale de funciones de modelo.py; aqui solo se ordena."""
    _, W, _, dominante, ticket_usd = _contexto(e)
    out = {}
    for red, perfil in perfiles.items():
        metricas = []
        for mid, m in modelo.METRICAS.items():
            d = perfil.get(mid, {})
            valor = d.get("valor")
            metricas.append({
                "id": mid,
                "bloque": m["bloque"],
                "direccion": m["dir"],
                "objetivo": modelo.umbral(m["t"], ticket_usd),
                "inaceptable": modelo.umbral(m["w"], ticket_usd),
                "valor": valor,
                "sigma": d.get("sigma"),
                "nota": d.get("nota"),
                "cota_inferior": bool(d.get("cota_inferior")),
                "puntaje": (modelo.normalizar(mid, valor, ticket_usd)
                            if valor is not None else None),
            })
        central, por_bloque = modelo.puntuar(perfil, W, ticket_usd, _ValorCentral())
        out[red] = {
            "metricas": metricas,
            "bloques": por_bloque,
            "puntaje_central": central,
            "compuertas_falladas": [
                {"compuerta": c, "motivo": motivo}
                for c, motivo in modelo.compuertas(red, perfil, dominante, ticket_usd)],
        }
    return out


def entradas(peticion):
    return {
        "monto_cop": float(peticion["monto_cop"]),
        "transfronterizo": bool(peticion["transfronterizo"]),
        "espera_s": float(peticion["espera_s"]),
        "irrevocabilidad": peticion["irrevocabilidad"],
        "trm": float(peticion.get("trm", 4000.0)),
    }


def ejecutar(peticion, perfiles=None):
    perfiles = perfiles if perfiles is not None else cargar_perfiles()
    accion = peticion.get("accion", "recomendar")
    if accion == "info":
        return {"redes": list(perfiles), "medicion": MEDICION}
    e = entradas(peticion)

    if accion == "interpretar":
        lam, W, kappa, _, ticket_usd = _contexto(e)
        return {
            "redes": list(perfiles),
            "composicion": {modelo.ETIQUETA[k]: v for k, v in
                            sorted(lam.items(), key=lambda x: -x[1])},
            "pesos": W,
            "certidumbre": kappa,
            "nivel_certidumbre": nivel_certidumbre(kappa),
            "ticket_usd": ticket_usd,
        }

    if accion != "recomendar":
        raise ValueError(f"acción desconocida: {accion}")

    r = modelo.recomendar(perfiles, replicas=int(peticion.get("replicas", REPLICAS)), **e)
    return {
        "resultado": r,
        "nivel_certidumbre": nivel_certidumbre(r["certidumbre"]),
        "detalle": detalle_redes(perfiles, e),
        "medicion": MEDICION,
        "trm": e["trm"],
    }


def main():
    try:
        respuesta = ejecutar(json.loads(sys.stdin.read()))
    except Exception as exc:  # el servidor recibe el motivo y responde 500
        sys.stdout.write(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(1)
    sys.stdout.write(json.dumps(respuesta))


if __name__ == "__main__":
    main()
