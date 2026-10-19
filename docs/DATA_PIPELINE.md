# Pipeline de datos casi en tiempo real

## Componentes

| Pieza | Archivo | Qué hace |
|---|---|---|
| Cliente HTTP | `pipelines/collectors/base.py` | Timeout, reintentos con backoff exponencial + jitter (429/5xx/red), respeta `Retry-After`, no reintenta 4xx, JSON-RPC y lotes. Usa el almacén de certificados del SO |
| Colectores | `pipelines/collectors/{evm,tempo,aptos,canton}.py` | `ciclo_bloques`, `ciclo_estado`, `ciclo_finalidad` por red |
| Precios | `pipelines/collectors/precios.py` | Chainlink en cadena (ETH/Arbitrum, MATIC-POL/Polygon, CELO/Celo) y Pyth on-chain (APT/Aptos). Cada dirección se verifica en vivo (`description()`, `decimals()`, frescura < 1 h) |
| Procesadores | `pipelines/processors/*.py` | Payload crudo → muestra normalizada (segundos, USD, fracciones). Funciones puras |
| Validadores | `pipelines/validators/validadores.py` | Rangos, unidades, estado de la métrica (`valida`/`insuficiente`/`obsoleta`) |
| Scheduler | `pipelines/scheduler.py` | Tareas asyncio, sin solapamiento, backoff, apagado limpio |
| Métricas | `services/analytics/metricas.py`, `continuidad.py` | Muestras → `MetricaValor` por ventana |

## Frecuencias y ventanas (configurables por entorno)

| Qué | Por defecto |
|---|---|
| Bloques/eventos | cada 20 s (máx. 40 bloques por ciclo; Aptos 6; Canton hasta 10 páginas) |
| Estado (validadores, config, ranura de proxy) | cada 300 s |
| Finalidad Tempo | cada 0,3 s (continuo) |
| Cálculo de métricas | cada 30 s |
| Ventanas | flujo 15 min · distribución 24 h · finalidad 72 h · continuidad 14 d |
| Obsolescencia | 15 min (métricas), 2 h (estado) |

## Muestreo

Redes rápidas no se leen completas: si el sondeo se atrasa más que el tope, se toman los bloques más recientes y se registran los saltados. Consecuencias documentadas en cada métrica:

- B1 usa solo pares de bloques consecutivos.
- C3 exige cobertura ≥ 0,9 de pares; si no (Aptos, Arbitrum) queda `no_computable` y se usa la base.
- C1/C2 de Polygon/Celo/Arbitrum son sobre la muestra de bloques, no un censo.
- Canton guarda 1 de cada 4 veredictos (`CANTON_SUBMUESTREO`); A3 escala el tráfico por ese factor.

## Estados de una métrica

`valida` · `insuficiente` (n < mínimo, o ventana larga sin completar) · `obsoleta` (última muestra vieja) · `fallida` (lectura de estado fallida) · `no_computable` (con la razón en `nota`). Solo `valida` y fresca entra al perfil efectivo.

## Ventana completa exigida

B2 (72 h), C3 y C5 (14 d) solo son `valida` cuando el tiempo observado cubre la ventana; antes de eso la base sigue vigente. Una cota parcial de C5 subestimaría los cambios, por eso no se usa.

## Fallos y recuperación

Cada componente registra `ultimo_ok`, `ultimo_error`, `fallos_consecutivos` y latencia en `salud_colector`. Tras un fallo el bucle espera `intervalo × min(2^fallos, 8)`. Un precio no disponible deja `fee_usd` nulo (nunca un valor inventado). El estado `degradada`/`caida` de una red se ve en `/api/salud` y en la página Monitoreo.

## Recalibración (botón)

`POST /api/recalibracion` corre `backend/benchmark/main.py --collect` en un subproceso aislado (`backend/data/recalibracion/<id>/`), sigue su avance por las marcas `>>>` del log y al terminar reconstruye los perfiles base de Tempo, Aptos y Canton desde su `metrics.csv`. No toca `resultados/` del repositorio. Parámetros opcionales: `bloques_tempo`, `bloques_aptos`, `paginas_canton`. Polygon, Celo y Arbitrum no tienen colector por lotes en el repositorio y se reportan como `no_disponible`.
