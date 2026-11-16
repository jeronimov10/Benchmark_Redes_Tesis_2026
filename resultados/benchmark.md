# Resultados del benchmark: seis redes

Generado el 2026-11-16 a partir de `resultados/metrics.csv` (Tempo, Aptos, Canton), `backend/modelo/perfiles.json` (Polygon, Celo, Arbitrum) y `backend/modelo/modelo.py` sin modificar. Todos los datos son historicos (ya producidos por la red); la unica metrica de tiempo real, B2 en Tempo y Aptos, se trata en las limitaciones.

## Resumen

- **Seis redes** comparadas con el mismo modelo de la tesis: Polygon, Celo y Arbitrum (medicion de 90 dias) frente a Tempo, Aptos y Canton (muestra reducida de verificacion).
- **Cobertura**: Polygon 15/16 con valor; Celo 15/16 con valor; Arbitrum 15/16 con valor; Tempo 14/16 con valor; Aptos 12/16 con valor; Canton 14/16 con valor.
- **Recomendacion por caso** (banda 1): Remesa de USD 300: Polygon; Compra en tienda: Polygon + Tempo; Pago domestico: Polygon + Tempo; Pago de alto valor: Tempo.
- **Lectura**: la recomendacion es la banda 1; si tiene varias redes, estan empatadas. Las limitaciones que condicionan esta lectura estan en [limitaciones.md](limitaciones.md) y no son un apendice.

## Cobertura de metricas por red

Metricas del catalogo del modelo (16) segun su estado.

| red | medidas | parciales | cota inferior | no computables | no aplican |
|---|---|---|---|---|---|
| Polygon | 14 | 0 | 1 | 1 | 0 |
| Celo | 14 | 0 | 1 | 1 | 0 |
| Arbitrum | 14 | 0 | 1 | 1 | 0 |
| Tempo | 8 | 6 | 0 | 2 | 0 |
| Aptos | 7 | 5 | 0 | 4 | 0 |
| Canton | 10 | 3 | 1 | 2 | 0 |

## Metricas por red

Valores tal como entran al modelo (`ServicioPerfiles`, modo `medicion`). Para T/A/C: A2 = p95/mediana, B3 x 48/18, C3 en %, C1 = C1b (HHI de peso de consenso). `n/d` = sin valor; el estado entre parentesis marca valores parciales o cota inferior.

| metrica | descripcion | unidad | Polygon | Celo | Arbitrum | Tempo | Aptos | Canton |
|---|---|---|---|---|---|---|---|---|
| **A1** | Costo mediano / ticket | USD | 0.004294 | 0.001339 | 0.007005 | 2.02e-05 (parcial) | 0.000286 (parcial) | 0.8953 (parcial) |
| **A2** | Cola de costo (p95 / mediana) | razon | 9.106 | 9.776 | 10.71 | 8.86 (parcial) | 2.318 (parcial) | 3.072 (parcial) |
| **A3** | Sensibilidad del costo a la congestion (beta) | indice | no computable | no computable | no computable | 2.02e+03 (parcial) | 8.628 (parcial) | 5.52e-08 |
| **A4** | Costo de anclaje por transaccion | USD | 7.01e-06 | 3.5e-06 | 2.88e-05 | no computable | no computable | no computable |
| **B1** | Latencia de inclusion p95 | s | 1.5 | 1 | 0.2503 | 0.59 | 0.08605 | 1.061 |
| **B2** | Tiempo a finalidad | s | 492 | 960 | 60 | 0.6302 (parcial) | no computable | 1.061 |
| **B2b** | Tiempo a irrevocabilidad en Ethereum | s | 492 | 3.04e+05 | 5.57e+05 | no computable | no computable | no computable |
| **B3** | Margen de capacidad (capacidad / 18 TPS) | razon | 7.828 (cota inferior) | 1.994 (cota inferior) | 6.416 (cota inferior) | 1.48e+03 (parcial) | 1.58e+03 (parcial) | 0.000621 (cota inferior) |
| **C1** | Concentracion de produccion o consenso (HHI) | indice | 0.1974 | 1 | 0.9939 | 0.06667 | 0.01686 | 0.2959 |
| **C2** | Operadores que concentran mas del 50 % | conteo | 3 | 1 | 1 | 8 | 24 | 1 |
| **C3** | Continuidad | % | 99.96 | 99.94 | 99.95 | 100 | 100 | 100 |
| **C4** | Tasa de fallo | fraccion | 0 | 0.001624 | 0 | 0 | 0 | 0.004125 |
| **C5** | Cambios de implementacion en la ventana | conteo | 0 | 0 | 0 | 0 | 0 | 11 |
| **D1** | Pago sin activo volatil propio | fraccion | 0.3861 | 0.5252 | 0.1011 | 1 | 0.01151 | 1 |
| **D2** | Transferencias con datos asociables a una orden | fraccion | 0.008984 | 0.005583 | 0.007061 | 0.45 | no computable | 0.1174 |
| **D3** | Transacciones multi-transferencia | fraccion | 0.3014 | 0.06007 | 0.2255 | 0.7682 (parcial) | 1 (parcial) | 0 (parcial) |

## Recomendaciones del modelo con las seis redes

`modelo.recomendar` con 10 000 replicas, semilla 42 y TRM 4 000, sobre los cuatro casos de referencia de la tesis y las seis redes.

### Remesa de USD 300 (COP 1 200 000, transfronteriza, espera 1 h, irrevocabilidad baja)

Ticket USD 300.00. Composicion: remesas 100%, comercio doméstico 0%, alto valor 0%. Certidumbre 0.985.

| banda | red | puntaje mediano | p05 - p95 |
|---|---|---|---|
| 1 | Polygon | 0.722 | 0.71 - 0.735 |
| 2 | Canton | 0.638 | 0.61 - 0.66 |
| 3 | Arbitrum | 0.63 | 0.602 - 0.654 |
| 3 | Tempo | 0.623 | 0.553 - 0.7 |
| 3 | Celo | 0.607 | 0.573 - 0.636 |

Metrica que mas separa la banda 1 de la 2: **D3** (contribucion 0.0833).

Inadmisibles: Aptos (G2: sin anclaje verificable en Ethereum).

Advertencia del modelo: métricas no concluyentes, excluidas del cálculo: A3, A4, B2b.

### Compra en tienda (COP 15 000, domestica, espera 3 s, irrevocabilidad media)

Ticket USD 3.75. Composicion: comercio doméstico 93%, alto valor 5%, remesas 2%. Certidumbre 0.62.

| banda | red | puntaje mediano | p05 - p95 |
|---|---|---|---|
| 1 | Polygon | 0.729 | 0.714 - 0.746 |
| 1 | Tempo | 0.699 | 0.621 - 0.777 |
| 2 | Arbitrum | 0.606 | 0.58 - 0.63 |
| 3 | Canton | 0.575 | 0.554 - 0.594 |
| 3 | Celo | 0.562 | 0.533 - 0.591 |

La banda 1 reune Polygon, Tempo: estan empatadas, no hay una ganadora unica (P(polygon > tempo) = 0.77).

Metrica que mas separa la banda 1 de la 2: **C1** (contribucion 0.0274).

Inadmisibles: Aptos (G2: sin anclaje verificable en Ethereum).

Advertencia del modelo: certidumbre media (0.62): el caso queda entre escenarios.

Advertencia del modelo: métricas no concluyentes, excluidas del cálculo: A3, A4, B2b.

### Pago domestico (COP 1 200 000, espera 60 s, irrevocabilidad media)

Ticket USD 300.00. Composicion: comercio doméstico 79%, alto valor 17%, remesas 4%. Certidumbre 0.403.

| banda | red | puntaje mediano | p05 - p95 |
|---|---|---|---|
| 1 | Polygon | 0.736 | 0.721 - 0.75 |
| 1 | Tempo | 0.719 | 0.639 - 0.796 |
| 2 | Arbitrum | 0.628 | 0.598 - 0.653 |
| 2 | Canton | 0.624 | 0.596 - 0.647 |
| 3 | Celo | 0.556 | 0.526 - 0.585 |

La banda 1 reune Polygon, Tempo: estan empatadas, no hay una ganadora unica (P(polygon > tempo) = 0.66).

Metrica que mas separa la banda 1 de la 2: **B3** (contribucion 0.0416).

Inadmisibles: Aptos (G2: sin anclaje verificable en Ethereum).

Advertencia del modelo: certidumbre de interpretación baja (0.40): el caso no está bien cubierto por los escenarios evaluados.

Advertencia del modelo: métricas no concluyentes, excluidas del cálculo: A3, A4, B2b.

### Pago de alto valor (COP 80 000 000, espera 10 min, irrevocabilidad alta)

Ticket USD 20,000.00. Composicion: alto valor 99%, comercio doméstico 0%, remesas 0%. Certidumbre 0.948.

| banda | red | puntaje mediano | p05 - p95 |
|---|---|---|---|
| 1 | Tempo | 0.887 | 0.815 - 0.938 |
| 2 | Polygon | 0.732 | 0.717 - 0.747 |
| 3 | Canton | 0.572 | 0.541 - 0.604 |
| 3 | Arbitrum | 0.57 | 0.54 - 0.601 |
| 4 | Celo | 0.505 | 0.474 - 0.538 |

Metrica que mas separa la banda 1 de la 2: **C3** (contribucion 0.0615).

Inadmisibles: Aptos (G2: sin anclaje verificable en Ethereum).

Advertencia del modelo: métricas no concluyentes, excluidas del cálculo: A3, A4, B2b.

## Benchmark de Tempo, Aptos y Canton con el motor del plan

Puntajes del motor `score_engine.py` (pesos y agregacion heredados del estudio de referencia) para los escenarios E1, E2 y E3 del plan. Este motor solo puntua las tres redes del plan; la comparacion de las seis redes es la de la seccion anterior. Un `--` es una red inadmisible por compuerta.

| red | escenario | admisible | compuertas fallidas | S_total | S_A | S_B | S_C | S_D | historicas | tiempo real | no aplica | computadas | parciales | no computables |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tempo | E1 | si | - | 0.851 | 0.789 | 1.000 | 0.692 | 1.000 | 14 | 1 | 1 | 10 | 6 | 0 |
| Tempo | E2 | si | - | 0.821 | 0.667 | 1.000 | 0.692 | 1.000 | 14 | 1 | 1 | 10 | 6 | 0 |
| Tempo | E3 | si | - | 0.829 | 0.667 | 1.000 | 0.692 | 1.000 | 14 | 1 | 1 | 10 | 6 | 0 |
| Aptos | E1 | si | - | 0.730 | 0.789 | 1.000 | 0.750 | 0.518 | 14 | 1 | 1 | 9 | 5 | 2 |
| Aptos | E2 | si | - | 0.753 | 0.667 | 1.000 | 0.750 | 0.518 | 14 | 1 | 1 | 9 | 5 | 2 |
| Aptos | E3 | si | - | 0.750 | 0.667 | 1.000 | 0.750 | 0.518 | 14 | 1 | 1 | 9 | 5 | 2 |
| Canton | E1 | si | - | 0.670 | 0.785 | 0.667 | 0.233 | 0.950 | 13 | 0 | 4 | 11 | 5 | 1 |
| Canton | E2 | no | G4 | -- | 0.611 | 0.800 | 0.233 | 0.950 | 13 | 0 | 4 | 11 | 5 | 1 |
| Canton | E3 | no | G4 | -- | 1.000 | 0.775 | 0.233 | 0.950 | 13 | 0 | 4 | 11 | 5 | 1 |

El catalogo de `metrics.csv` tiene 45 filas (16 metricas x 3 redes y E1, con C1 y C1b). Detalle: `resultados/metrics.csv`, `gates.csv`, `scores.csv`, `sensitivity.csv`, `discrimination.csv`, `benchmark_final.csv`.
