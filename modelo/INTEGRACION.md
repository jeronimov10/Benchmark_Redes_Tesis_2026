# Modelo de recomendación de red: guía de integración

Este paquete trae el modelo del proyecto de grado tal como está en la tesis
(sección 5.4). La aplicación debe **usarlo, no reescribirlo**.

## Archivos

| Archivo | Qué es | ¿Se puede modificar? |
|---|---|---|
| `modelo.py` | El modelo completo. Solo usa la biblioteca estándar de Python (json, math, random, argparse, pathlib). | No. Ni la lógica ni las constantes (escenarios, pesos, umbrales, γ, p, ε, d0). |
| `perfiles.json` | Los perfiles medidos de Polygon, Celo y Arbitrum (ventana de 90 días, octubre de 2026). Es la entrada de datos del modelo. | No a mano. Se reemplaza entero cuando hay una medición nueva. |
| `casos_referencia.json` | Salidas esperadas de cuatro pagos, para comprobar que la integración da lo mismo que la tesis. | No. |
| `pruebas_modelo.py` | Pruebas de la tesis (benchmark por escenario, barrido de 264 pagos, punto de quiebre). Es opcional en la app. | No. |

## Cómo se llama

```python
import json
import modelo

perfiles = json.load(open("perfiles.json", encoding="utf-8"))
r = modelo.recomendar(
    perfiles,
    monto_cop=1_200_000,        # monto en pesos colombianos (float o int)
    transfronterizo=True,       # bool
    espera_s=3600,              # espera tolerable hasta la confirmación, en segundos
    irrevocabilidad="baja",     # "baja" | "media" | "alta"
    trm=4000.0,                 # pesos por dólar
    replicas=10000,             # réplicas Monte Carlo (la tesis usa 10.000)
)
```

Si el usuario da el monto en dólares, se convierte antes: `monto_cop = usd * trm`.

Una llamada con 10.000 réplicas tarda cerca de 1 segundo. Si la app la llama
desde un servidor web, conviene correrla fuera del hilo de la petición o
guardar en caché el resultado por combinación de entradas. El resultado es
determinista porque el modelo usa `random.Random(42)`.

## Qué devuelve

Un diccionario con estas claves:

- `caso`: las entradas, más `ticket_usd`.
- `composicion`: cuánto se parece el pago a cada escenario, por ejemplo
  `{"remesas": 0.996, "comercio doméstico": 0.002, "alto valor": 0.002}`.
- `pesos`: pesos de los bloques A, B, C y D para este pago.
- `certidumbre`: κ entre 0 y 1. Alta ≥ 0,75; media entre 0,45 y 0,75; baja < 0,45.
- `inadmisibles`: redes descartadas por una compuerta, con el motivo.
- `bandas`: lista ordenada. Cada banda tiene `redes`, `puntajes` (mediana, p05,
  p95 por red) y, si aplica, `separacion_con_siguiente` o `no_distinguibles`.
  **La recomendación es la banda 1.** Si tiene más de una red, están empatadas
  y no se debe mostrar una sola como ganadora.
- `determinante`: la métrica que más separa la banda 1 de la 2. No es la única
  causa del resultado; mostrarla como "lo que más pesó", no como "la razón".
- `advertencias`: textos que se deben mostrar al usuario (certidumbre baja o
  media, métricas no concluyentes).

## Reglas para mostrar el resultado

1. Mostrar bandas, no un ranking 1-2-3, cuando hay empate.
2. Mostrar siempre la certidumbre y las advertencias.
3. Mostrar la fecha y la ventana de la medición: "perfiles medidos en 90 días,
   octubre de 2026". Los resultados envejecen.
4. No inventar métricas ni puntajes que el modelo no devuelve.

## Comprobación

Con `perfiles.json` y `replicas=10000`, los cuatro casos de
`casos_referencia.json` deben dar las mismas bandas, la misma métrica
determinante y medianas y certidumbre iguales con tolerancia de 0,005.
