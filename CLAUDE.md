# CLAUDE.md — guía para sesiones futuras

Benchmark de tesis que compara **Tempo, Aptos y Canton** como destino de
liquidación de pagos en Colombia (remesas, comercio, alto valor), siguiendo
`docs/plan_medicion_tempo_aptos_canton.md` (adaptación de un benchmark previo
sobre Polygon/Celo/Arbitrum, en `docs/benchmark-medible-polygon-celo-arbitrum.pdf`).

## La regla de oro (no negociable)

> Ninguna métrica se puntúa si su valor no puede derivarse de una consulta
> reproducible al registro público de la red. **Nunca** se completa un valor
> con documentación, blogs o declaraciones de equipos. Un `no_computable` con
> su razón exacta es un resultado válido y valioso. **Un número mal calculado
> o adivinado es peor que no computarlo** — invalida el estudio entero.

Esto ya ha evitado errores concretos en este repo: en una pasada anterior no
se adivinó el ID de 32 bytes del price feed de Pyth en Aptos porque no se
podía verificar en ese momento (habría producido un precio fabricado), y no
se decodificó a ciegas el blob BCS de `ExecutionConfig`. **Ambos se
resolvieron después, correctamente**, en cuanto apareció una vía verificable
— ver "Estado actual" abajo. La regla no es "nunca lo intentes", es "nunca lo
reportes sin poder verificarlo".

Fuentes admisibles: el registro que la propia red publica para terceros
(JSON-RPC de Tempo, REST de Aptos, Scan API de Canton). Dos técnicas que
**sí respetan la regla** y ya rindieron frutos en este repo:

1. **Leer código fuente público para ubicar un identificador** (dirección,
   selector de evento, layout de un struct) y luego **verificarlo con una
   consulta en vivo/histórica**. Ejemplos reales: la dirección del
   precompilado `ValidatorConfigV2` de Tempo; el evento
   `TransferWithMemo(address,address,uint256,bytes32)` de TIP-20 (topic0
   calculado con keccak256, no copiado); el layout exacto de
   `OnChainExecutionConfig` en Aptos (79/79 bytes del blob BCS consumidos al
   decodificar, sin sobrante — esa exactitud es la prueba de que el layout es
   correcto). El VALOR final siempre sale de la consulta, nunca del código.
2. **Usar la API en vivo de un servicio auxiliar para resolver un
   identificador, y verificarlo con auto-consistencia en la propia red.**
   Ejemplo real: el feed ID de Pyth APT/USD se obtuvo de
   `hermes.pyth.network/v2/price_feeds?query=APT` (la API pública del propio
   Pyth, no un blog ni memoria), y se verificó porque la tabla on-chain
   devolvió un `PriceInfo` cuyo `price_identifier` coincide exactamente con
   el ID consultado — autoconsistente. **Nunca vale adivinar** ese tipo de
   identificador de memoria: un intento anterior en este mismo repo lo hizo
   mal por un dígito (63 vs. 64 caracteres hex) y se descartó a tiempo.

**Nota operativa que costó tiempo redescubrir**: `api.github.com/search/code`
devuelve 401 sin autenticación, pero **`api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1`
(listar el árbol del repo) y `raw.githubusercontent.com/...` (leer un archivo
por ruta exacta) NO requieren autenticación y funcionan siempre.** El bloqueo
real nunca fue "no se puede leer código fuente de Tempo/Aptos", era "no se
puede *buscar por palabra clave* en GitHub sin login". Si necesitas encontrar
un archivo, lista el árbol completo y filtra rutas localmente (así se
encontraron `transfer_with_memo.rs`, `fork_schedule.rs` y
`execution_config.rs` en esta pasada) — no asumas que el 401 de code search
también bloquea esto.

## Cómo correr esto

```
python main.py              # rápido: usa resultados/raw/ ya descargado
python main.py --collect    # lento: vuelve a consultar las 3 APIs en vivo primero
```

En cualquier caso corre `compute_*_metrics.py` → `build_deliverables.py` →
`score_engine.py`, imprime un reporte diferenciado en consola y deja todo en
`resultados/`. El entregable final para citar es `resultados/benchmark_final.csv`
(una fila por red × escenario: puntaje, admisibilidad, y cuántas métricas de
esa red son históricas / en vivo / sin computar).

## Arquitectura del pipeline

```
scripts/collect_{tempo,aptos,canton}.py   -> resultados/raw/<red>/*.json (crudo)
scripts/compute_{tempo,aptos,canton}_metrics.py -> resultados/raw/<red>_metrics.json
scripts/build_deliverables.py             -> resultados/metrics.csv, limitaciones.md, run_manifest.json
scripts/score_engine.py                   -> resultados/{gates,scores,sensitivity,discrimination}.csv
main.py                                   -> reporte en consola + resultados/benchmark_final.csv
```

Los tres `collect_*.py` **no comparten código** (a propósito, el plan lo pide
así: cada red expone un registro distinto). `poll_finality.py` es aparte: es
el único mecanismo de sondeo en vivo (W_L), pensado para correr horas en
background, no dentro de una sesión corta.

## La distinción tiempo real vs histórico (`modo_dato`)

`metrics.csv` tiene una columna `modo_dato` (y el reporte de consola un tag
`[HIST]`/`[VIVO]`/`[N/A]`) que viene literalmente del vocabulario de §7.1 del
plan:

- **`historico` (W_H)** — la métrica se reconstruye de bloques/eventos/estado
  ya producidos por la red. Aunque la petición se haga en vivo contra un
  nodo, **lo que se mide ya ocurrió**. Es la inmensa mayoría de las métricas.
- **`tiempo_real` (W_L)** — requiere sondeo continuo mientras el evento
  ocurre. Hoy eso es **únicamente B2 en Tempo y Aptos** (`τF − τ1`, vía
  `scripts/poll_finality.py`): ninguna de las dos redes deja un evento
  posterior que registre cuándo algo quedó finalizado, así que no es
  reconstruible con datos históricos por diseño (Sec. D1 del plan). En
  Canton, B2 **sí** es histórico porque el verdict trae su propio
  `finalization_time`.
- **`no_aplica`** — transversal o degenerada por arquitectura, sin ventana
  temporal (E1 en las tres redes, D1 en Canton, C1 en Canton).

Si en una sesión futura alguien pide "más datos en tiempo real" para B2,
significa correr `poll_finality.py` en background por las 72h que pide el
plan (`§7.1`), no re-ejecutar `main.py` — eso solo usa lo que ya está en
`resultados/raw/`.

## Estado actual (última pasada)

`resultados/benchmark_final.csv` y `resultados/limitaciones.md` son la fuente
de verdad siempre actualizada — no confíes en un resumen estático aquí si
huele a desactualizado, vuelve a correr `python main.py` y lee esos dos
archivos. A modo de orientación: de 49 filas en `metrics.csv` (16 métricas ×
3 redes + un E1 extra en Canton por sus dos activos), solo **3 quedan
`no_computable`**, y dos de esas tres no son un hueco de datos sino un límite
de arquitectura/alcance:

- **`aptos.B2`** — genuinamente no reconstruible con datos históricos (D1 del
  plan): Aptos no deja un evento posterior que registre cuándo un bloque
  quedó finalizado, y HTTP simple no alcanza (el bloque dura ~20ms, más
  rápido que el round-trip a la API pública). Necesita `poll_finality.py`
  corriendo 72h en background, no una sesión interactiva.
- **`aptos.D2`** — no es un dato bloqueado, es una decisión sin tomar: el
  plan exige fijar por escrito qué cuenta como "referencia apta" (A-5) antes
  de medir, y la muestra de bloques que tenemos está dominada por un
  protocolo de trading de derivados (`0x50ead22a...`), no por pagos simples
  — fijar A-5 sobre esta muestra sería forzado. Necesitaría una recolección
  dirigida a transferencias de pago reales, no solo más de la misma muestra.
- **`canton.C1`** — degenerada por diseño: Canton no tiene bloques. No es una
  falta, es el resultado correcto (por eso C1b es la métrica primaria de
  concentración en las tres redes, Sec. D3 del plan).

Todo lo demás — incluyendo varias métricas que en pasadas anteriores estaban
`no_computable` por un bloqueo que parecía estructural — se resolvió
reconstruyendo con datos ya descargados o con una consulta puntual nueva
(nunca con documentación). Los hallazgos más importantes, por si hace falta
repetir o extender el método:

- **Tempo quedó completo (16/16).** `C5` se resolvió encontrando una
  extensión RPC del propio nodo, `tempo_forkSchedule` (namespace `tempo_*`,
  admisible), que expone el schedule completo de TIPs con su
  `activationTime` real — no hay que tocar el changelog de GitHub para esto.
  `D2` se resolvió leyendo `crates/contracts/src/precompiles/tip20.rs`
  (código fuente público) para confirmar el evento
  `TransferWithMemo(address indexed from, address indexed to, uint256 amount, bytes32 indexed memo)`
  de la interfaz `ITIP20`, y midiendo su topic sobre los logs que ya estaban
  descargados.
- **Aptos pasó de 7 métricas bloqueadas a 2.** `A1`/`A2` se resolvieron
  ubicando el feed ID de Pyth vía la API de Hermes y verificándolo
  on-chain (ver la regla de oro arriba) — el precio sigue **congelado desde
  2026-08-26** (0.55654017 USD/APT) y se aplica fijo a toda la muestra,
  exactamente como el propio plan preveía como salida de contingencia
  (Sec.4.2, `[VERIFICAR A-2]`). `A3`/`B3` se resolvieron decodificando el
  blob BCS de `0x1::execution_config::ExecutionConfig` contra el layout
  exacto de `OnChainExecutionConfig` confirmado en
  `types/src/on_chain_config/execution_config.rs` de `aptos-labs/aptos-core`
  (79/79 bytes consumidos, variante V7 activa, `block_gas_limit_type=ComplexLimitV1`,
  `effective_block_gas_limit=300000`) — con una simplificación declarada: no
  se pondera `execution_gas`/`io_gas` por separado como hace el protocolo
  real. `D3` se resolvió resolviendo el `store` de cada evento
  `fungible_asset::Deposit/Withdraw` a su activo real vía
  `FungibleStore.metadata` (29 stores, colapsan a 3 activos) — con una
  advertencia fuerte de `n=12` y contaminación por rebalanceo de colateral
  de trading, igual que el resto de los D3 de este estudio.
- **Canton ya estaba casi completo** de la pasada anterior (solo falta C1,
  que no es una falta real). `C1b`/`C2` (pesos de SV), `A3` (regresión de
  costo vs. tráfico), `C3` (latido del DSO vía `ValidatorLicense_ReportActive`),
  `D1` (sujeto declarado), `D2` (campo `meta` del estándar de token) y `D3`
  (multi-salida/multi-instrumento) se reconstruyeron de `dso_state.json` y
  `events_sample.json` que ya estaban descargados. **Ojo con B3**: usa
  `baseRateTrafficLimits`, que es la asignación gratuita *por miembro* antes
  de comprar tráfico extra (`AmuletRules_BuyMemberTraffic`), no el techo
  agregado del sincronizador — está marcada `parcialmente_derivada` con esa
  advertencia explícita y probablemente **subestima** la capacidad real. Por
  eso Canton falla la compuerta G4 en E2/E3: no lo repitas como "Canton no
  puede sostener 48 TPS" sin citar esa advertencia.

Con esto, `discrimination.csv` pasó de tener varias métricas con "menos de 2
redes con dato" a tener las 15 métricas del catálogo con al menos 2 redes, y
la mayoría con las 3 — el estudio discrimina mucho mejor entre las tres redes
de lo que discriminaba antes.

## Quirk conocido del motor de puntajes (no es un bug que yo haya metido, pero lo vas a ver)

`score_engine.py::normaliza()` usa una transformación logarítmica. Para
métricas "mayor es mejor" (D1, D2, D3), un valor de **exactamente 0**
produce `math.log(0)` → excepción capturada → la métrica se excluye
silenciosamente del bloque (no cuenta como 0 puntos, simplemente no cuenta).
Esto ya afecta a `canton.D3 = 0.0` (multi-salida) en la pasada actual: mira
`n_D` en `scores.csv` antes de asumir que todas las métricas del bloque D
entraron al promedio. No se corrigió en esta pasada porque tocar la fórmula
de normalización afecta el puntaje de las 3 redes × 3 escenarios a la vez —
si se decide arreglarlo, que sea una decisión explícita y documentada, no un
efecto colateral de otra tarea.

## Si vuelves a esto para cerrar lo que falta

Solo quedan 3 huecos reales (ver "Estado actual"), y dos no son de datos:

- **`aptos.B2` en vivo** necesita `scripts/poll_finality.py` corriendo 72h en
  background, no una sesión interactiva corta.
- **`aptos.D2`** necesita una recolección dirigida a transferencias de pago
  reales (no la muestra actual, dominada por trading de derivados) para
  poder fijar por escrito la definición operativa de A-5 antes de medir.
- **Ventana W_H de 14 días completos**: todo lo de arriba sigue corriendo
  sobre una muestra reducida de minutos/segundos, no la ventana del plan.
  Si se decide correr la recolección completa, aumentar `N_BLOCKS` en
  `collect_tempo.py`/`collect_aptos.py` y `MAX_PAGES` en `collect_canton.py`
  (y paginar más allá si hace falta) — el resto del pipeline ya sabe qué
  hacer con más datos, no hace falta tocar los `compute_*` ni
  `build_deliverables.py`.
- Antes de tocar `score_engine.py`, lee `docs/plan_medicion_tempo_aptos_canton.md`
  §5.6/§5.7 completo — los pesos y la agregación están heredados
  deliberadamente sin cambios del estudio de referencia (Sec. D8 del plan)
  para mantener comparabilidad. Ojo con el quirk de `math.log(0)` de la
  sección anterior antes de asumir que un bloque D con una métrica en 0 está
  usando las tres métricas en el promedio.

## Mapa de archivos

- `docs/plan_medicion_tempo_aptos_canton.md` — la especificación completa
  (qué medir, cómo, compuertas, pesos, reglas de honestidad). Léelo antes de
  añadir o cambiar una métrica.
- `docs/matriz_requerimientos.md` y `docs/fase4_verificacion.md` — bitácora
  narrativa de qué se intentó, qué funcionó y qué no, con la evidencia de
  cada `[VERIFICAR]` del plan. Útil para no repetir investigación ya hecha
  (ej. la dirección del precompilado de Tempo, los endpoints de Canton que
  bloquean acceso directo).
- `resultados/raw/<red>/` — datos crudos, suficientes para recalcular todo
  sin volver a tocar la red.
- `resultados/limitaciones.md` — generado automáticamente por
  `build_deliverables.py`, entrega de primera clase, no un apéndice.
