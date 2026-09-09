# Plan de medición — Tempo, Aptos y Canton
## Especificación ejecutable para el agente de recolección

**Versión:** 1.0 · **Fecha:** septiembre de 2026
**Origen:** adaptación del benchmark medible de redes EVM para pagos en Colombia (Polygon PoS / Celo / Arbitrum One)
**Destinatario:** agente autónomo de recolección y cálculo
**Salida esperada:** tablas de métricas, compuertas, puntajes y bitácora de limitaciones. No un informe.

---

## 0. Cómo usar este documento

Este documento es la especificación completa. El agente debe:

1. Ejecutar primero la **§4 (verificación de configuración)** por entero, y detenerse a reportar antes de recolectar nada. Todos los ítems marcados `[VERIFICAR]` son bloqueantes.
2. Recolectar según **§8**, respetando la ventana de **§7**.
3. Calcular según **§5** y **§6**.
4. Entregar exactamente los artefactos de **§9**.
5. Cumplir sin excepción las reglas de **§10**.

**Regla de oro:** este instrumento vale por lo que declara que no puede medir. Una métrica marcada `no_computable` con su razón es un resultado válido y valioso. Una métrica rellenada con un número tomado de documentación es una falsificación del estudio completo.

---

## 1. Objeto y regla metodológica

### 1.1 Pregunta

> Para cada escenario transaccional relevante en Colombia, ¿qué red es admisible como destino de liquidación, cómo se ordenan las admisibles entre sí, y qué operaciones de pago se usan efectivamente en cada una?

### 1.2 Regla heredada (§2.1 del documento de referencia)

Ninguna métrica se puntúa si su valor no puede derivarse de datos del propio registro de la red mediante consultas reproducibles. Nada de documentación oficial, agregadores comerciales ni declaraciones de los equipos.

### 1.3 Enmienda obligatoria: de "en cadena" a "en el registro"

El benchmark de referencia dice *datos en cadena*. Canton no tiene cadena de bloques en el sentido de las otras dos. La regla se reformula sin aflojarla:

> Una métrica es admisible si su valor puede obtenerse consultando el registro que la propia red publica para terceros, mediante una consulta que un tercero puede reejecutar y cuyo resultado no depende de ser contraparte de las transacciones observadas.

Las fuentes admisibles quedan fijadas así:

| Red | Registro admisible | Registro NO admisible |
|---|---|---|
| Tempo | JSON-RPC de nodo Tempo (`eth_*` + extensiones `tempo_*`), estado de precompilados | Explorador web, documentación, TIDX si no se puede reejecutar la consulta |
| Aptos | Fullnode REST API `/v1/*` e Indexer GraphQL, recursos Move de `0x1` | Dashboards, agregadores |
| Canton | Scan API de super validadores (`/api/scan/v2/updates`, `/v0/events`, `/v0/state/acs`, `/v0/scans`, `/v0/dso-sequencers`) | Ledger API de un participante propio, cualquier dato al que se acceda por ser contraparte |

La última fila importa: **está prohibido crear una parte propia en Canton y observar transacciones desde dentro.** Eso mediría lo que un participante ve, no lo que un tercero puede auditar, y destruiría la comparabilidad con las otras dos.

### 1.4 Las tres redes evaluadas

*(Sección añadida el 2026-09-09; el documento de referencia sobre Polygon/Celo/Arbitrum trae una sección equivalente en su §3 que esta adaptación había omitido. Se incorpora aquí para mantener la misma estructura.)*

**Criterios de inclusión.** A diferencia del documento de referencia, donde las tres redes comparten compatibilidad EVM y ancla verificable en Ethereum, aquí el criterio es el opuesto: se eligieron deliberadamente tres **arquitecturas de registro distintas** — una L1 EVM permisionada de propósito específico para pagos, una L1 de propósito general basada en Move, y una plataforma DLT sin cadena de bloques para finanzas institucionales — precisamente para poner a prueba si el instrumento de medición sobrevive al cambio de arquitectura (la enmienda de §1.3 existe por esto). Las tres cumplen, además:

- **Historia operativa suficiente para observar tráfico real.** Tempo mainnet arrancó el 16 de enero de 2026 (confirmado por marca de tiempo del bloque 1, corrigiendo el 18 de marzo que figuraba como valor asumido antes de verificarlo); Aptos mainnet opera desde octubre de 2022; el Global Synchronizer de Canton, desde junio de 2024 (confirmado por el evento `DsoBootstrap` más antiguo recuperable).
- **Registro público consultable por terceros**, aunque con distinto grado de fricción — ver la asimetría de acceso documentada en la tabla de la §1.3 y, para Canton en particular, el hallazgo de que los Scan de Super Validador individuales rechazan acceso directo (§4.3, `[C-1]`).
- **Ninguna aloja una stablecoin del peso colombiano**, a diferencia de Polygon (COPW) y Celo (COPM). Esto obliga a la decisión D6: el activo de pago se elige por red según lo que efectivamente circula, no por relevancia para el peso colombiano.

**Perfil de cada red.**

| Atributo | Tempo | Aptos | Canton |
|---|---|---|---|
| Arquitectura | L1 EVM permisionada; consenso BFT propio (Simplex, sobre Commonware) | L1 de propósito general; máquina virtual Move; consenso AptosBFT | DLT sin cadena de bloques global; sub-ledgers de cada participante sincronizados por un Global Synchronizer operado por Super Validators |
| Mecanismo de finalidad | Determinística por consenso BFT; sub-segundo (mediana medida: 0,63 s, n=53, sondeo de 30 s) | Determinística por AptosBFT; sub-segundo (no se logró medir con sondeo HTTP simple — ver limitación en §4.2) | Verdict del mediador con `record_time` y `finalization_time`; mediana medida ~0,65–1,08 s según ventana |
| Producción / ordenamiento | Proponente elegido por VRF entre validadores permisionados — 15 activos confirmados vía `ValidatorConfigV2` | Proponente rotativo ponderado por stake — 84 validadores activos confirmados vía `0x1::stake::ValidatorSet` | No existe "bloque": cada Synchronizer ordena vía los sequencers de sus SV |
| Activo de comisión | TIP-20 denominado en USD; no hay token nativo de gas | APT (token nativo) | Tráfico de red, tarifado en USD (`trafficPrice`, USD/MB) y liquidado en Canton Coin |
| Activo de pago evaluado aquí | El TIP-20 USD observado con más actividad de comisión en la muestra | Fungible Asset / Coin con mayor actividad (inventario pendiente vía Indexer, §4.2 `[A-1]`) | Canton Coin (Amulet) y USDCx (Circle xReserve, CIP-56) evaluados por separado, conforme a D7 |
| Ruta de gobernanza / actualizaciones | TIPs (Tempo Improvement Proposals), activados por hardfork | AIPs (Aptos Improvement Proposals) y publicación de módulos Move | CIPs (Canton Improvement Proposals) y votos de gobernanza del DSO |

Estos datos, igual que en el documento de referencia, sirven para configurar el sistema de recolección y para que el lector se sitúe. **Ninguno entra al puntaje**: todo lo puntuado se mide, conforme a §1.2.

---

## 2. Qué expone cada red: tabla de equivalencias

Esta tabla sustituye a la §4 del documento de referencia. Es la materia prima de todo lo demás.

| Necesidad | Tempo | Aptos | Canton |
|---|---|---|---|
| Cadencia y marca de tiempo | `eth_getBlockByNumber` → `timestamp` (s) | `GET /v1/blocks/by_height/{h}` → `block_timestamp` (µs) | `record_time` de cada update en `POST /v2/updates` |
| Productor / ordenador | Cabecera del bloque `[VERIFICAR §4.1]` + precompilado ValidatorConfig | `block_metadata_transaction` → `proposer`, `round`, `epoch` | No existe. Solo conjunto de sequencers/SV vía `/v0/dso-sequencers` y `/v0/scans` |
| Participación en consenso | `[VERIFICAR]` conjunto y pesos de validadores | `previous_block_votes_bitvec`, `failed_proposer_indices`, `0x1::stake` vía `POST /v1/view` | Pesos de gobernanza/recompensa de los SV en el ACS del DSO |
| Ocupación / congestión | `gasUsed / gasLimit` de la cabecera, **por carril** | gas del bloque / límite de gas de bloque `[VERIFICAR §4.2]` | Volumen de tráfico por intervalo; no hay concepto de ocupación de bloque |
| Costo de la transacción | Recibo EVM; comisión denominada en TIP-20 USD `[VERIFICAR §4.1]` | `gas_used × gas_unit_price` en octas → requiere precio APT/USD | `traffic_summary` en el update; tarifa denominada en USD por diseño |
| Éxito / fallo | `status` del recibo | `success` y `vm_status` | `verdict_result` en `/v0/events` |
| Transferencias del activo de pago | Logs del TIP-20 | Eventos de Fungible Asset / `0x1::fungible_asset` | Eventos de transferencia en los updates, solo si son visibles al DSO |
| Referencia de conciliación | Memo nativo de 32 bytes del TIP-20 | No nativo. Argumentos de entry function o eventos del emisor | Campos `meta` del estándar de token, solo en activos visibles |
| Irreversibilidad | Etiqueta `finalized` de `eth_getBlockByNumber` | Compromiso del bloque; finalidad determinística en el commit | `record_time` del verdict del mediador |
| Cambios de la ruta de pago | Activación de actualizaciones de red (T2…T11), cambios de TIP-403 | Publicaciones de módulo en `0x1` y en la dirección del emisor | Cambios de versión de paquete y de las reglas del DSO en el ACS |
| Actividad no visible | — | — | `/v0/events` devuelve el verdict de transacciones privadas: se cuenta su existencia y su tiempo, no su contenido |

**Consecuencia central.** Las tres redes exponen conteo, tiempo y resultado de todas sus transacciones. Solo dos exponen monto y contrapartes de todas. En Canton eso depende del activo: Canton Coin es visible al DSO; USDCx y cualquier stablecoin emitida bajo el estándar de token no lo es. Esta asimetría no se disimula: se convierte en la compuerta G2′ y en la métrica E1.

---

## 3. Decisiones de diseño

Cada decisión se aparta del documento de referencia. Todas deben quedar registradas en el informe final.

### D1 — El ancla en Ethereum desaparece; τA se sustituye por τF

Ninguna de las tres publica compromisos de estado en Ethereum. La métrica B2 y la compuerta G2 originales, aplicadas literalmente, declaran a las tres inadmisibles en todos los escenarios, lo cual no es un resultado sino un error de portabilidad.

Se sustituye por:

> **Instante de irreversibilidad observable τF.** Primer momento en el que un tercero, consultando únicamente el registro público de la red, puede verificar que la transferencia ya no puede revertirse. Se mide `τF − τ1`, donde τ1 es la marca de tiempo del bloque o update que la contiene.

Y se sustituye la compuerta G2 por **G2′** (ver §6).

**Nota crítica de implementación.** En Tempo y Aptos la finalidad es determinística y no deja un evento posterior que la registre: no es reconstruible desde el histórico. `τF − τ1` solo puede medirse **observando en vivo**. En Canton sí es reconstruible a posteriori, porque el verdict del mediador tiene su propio `record_time`. Por eso §7 define dos ventanas.

**Advertencia sobre el resultado.** Es probable que τF resulte sub-segundo en Tempo y Aptos, y de segundos en Canton, sin discriminar realmente. Eso es un hallazgo, no un fracaso: significa que el eje de irreversibilidad que separaba a las tres redes EVM del estudio de referencia deja de separar a estas tres, y el peso explicativo se traslada al bloque C, es decir, a *quién* produce esa finalidad.

### D2 — A4 se elimina

El costo de anclaje amortizado no existe sin ancla. Se elimina la métrica y su peso se redistribuye proporcionalmente dentro del bloque A (ver §5.5). No se sustituye por un proxy: el costo de operar la infraestructura de estas tres redes no es observable desde el registro.

### D3 — Se añade C1b y se degrada C1 a métrica secundaria

C1 (Herfindahl sobre producción de bloques) no es computable en Canton y podría ser engañosa en Tempo, donde la elección de proponente es por VRF y reparte propuestas uniformemente aunque el conjunto de validadores sea pequeño y permisionado.

Se añade **C1b — concentración del poder de consenso**: Herfindahl sobre el peso de voto o participación de cada operador, leído del estado del registro (precompilado de validadores en Tempo, `0x1::stake` en Aptos, ACS del DSO en Canton). Es la única métrica de concentración computable en las tres y pasa a ser la primaria del bloque C. C1 se conserva donde exista y se reporta como secundaria.

### D4 — Se añade E1, observabilidad por terceros

**E1 — Proporción de transferencias del activo de pago cuyo monto, contrapartes y resultado son verificables por un tercero que no es contraparte.**

Es la diferencia arquitectónica más importante entre Canton y las otras dos, y ninguna de las quince métricas heredadas la captura. Se reporta siempre, aunque no se puntúe: entra como compuerta.

### D5 — B3 se reporta desdoblado

El margen de capacidad basado en caudal *observado* castiga a una red por no tener usuarios, no por no tener capacidad. Tempo lleva seis meses en producción y Canton procesa volumen institucional de baja frecuencia; ambas saldrían con H ≈ 0 por ausencia de demanda.

Se reportan dos cantidades:
- **H_obs** — caudal máximo sostenido durante una hora en la ventana / requisito de 48 TPS.
- **H_cfg** — capacidad configurada derivable del estado del registro (parámetros de gas y capacidad del carril de pagos en Tempo, límite de gas de bloque en Aptos, límites de tráfico del sincronizador en Canton) / 48 TPS.

**La compuerta G4 se evalúa contra H_cfg. El puntaje usa H_cfg. H_obs se reporta como contexto y nunca se puntúa.** Justificación: la pregunta del benchmark es si la red *puede* sostener el escenario, no si hoy lo sostiene.

### D6 — El activo de pago deja de ser una stablecoin del peso

Ninguna de las tres aloja COPW ni COPM. El activo de pago se elige por red según §4, y A1 sigue expresándose como fracción del ticket del escenario, que es precisamente por qué el documento de referencia la definió como fracción. Los umbrales de §6 del original no cambian.

### D7 — En Canton se miden dos activos, no uno

- **Canton Coin (Amulet):** visible al DSO. Es el único activo sobre el que Canton puede puntuarse en el bloque A y en D2/D3.
- **USDCx (u otra stablecoin bajo el estándar de token):** no visible. Se mide únicamente E1 = 0, y se reporta como caso de inadmisibilidad por G2′.

Reportar ambos. La conclusión "Canton es admisible con su activo nativo e inadmisible con el activo que un pagador colombiano realmente usaría" es, si se confirma, el hallazgo más fuerte de este trabajo.

### D8 — Los umbrales, escenarios, pesos, normalización y agregación no se tocan

Todo lo de §6, §7, §9 y §10 del documento de referencia se hereda sin cambios, salvo la redistribución del peso de A4. Esto es deliberado: la comparabilidad con el trabajo sobre Polygon, Celo y Arbitrum es más valiosa que cualquier mejora marginal en los umbrales.

---

## 4. Configuración por red — FASE BLOQUEANTE

El agente ejecuta esta sección primero y reporta antes de continuar. Cada `[VERIFICAR]` debe resolverse con evidencia de una consulta real, no con documentación.

### 4.1 Tempo

| Parámetro | Valor conocido | Acción |
|---|---|---|
| Chain ID | 4217 (mainnet) | Confirmar con `eth_chainId` |
| Inicio de mainnet | 18 de marzo de 2026 | Confirmar por marca de tiempo del bloque 1 |
| Cadencia | ~600 ms | Medir, no asumir |
| Consenso | Simplex BFT (Commonware), proponente por VRF | Contexto |
| Activo de comisión | TIP-20 denominado en USD; no hay token nativo | Contexto |
| Proveedores de nodo | Dos independientes | Obligatorio |

`[VERIFICAR T-1]` **Identificación del proponente en la cabecera.** Determinar si el campo `miner`/`beneficiary` del bloque identifica al validador que lo produjo, o si hace falta el contexto de consenso embebido en la cabecera. Si ninguna vía identifica al productor, C1 se marca `no_computable` en Tempo y solo se reporta C1b.

`[VERIFICAR T-2]` **Conjunto y pesos de validadores.** Localizar el precompilado de configuración de validadores y comprobar que su estado es legible por `eth_call` en un bloque histórico. Sin esto, C1b no es computable en Tempo.

`[VERIFICAR T-3]` **Campos de comisión del recibo.** Determinar cómo expone el recibo el token de comisión y el monto cobrado. Si la comisión es denominada en un TIP-20 USD, A1 no necesita oráculo. Documentar el campo exacto.

`[VERIFICAR T-4]` **Ocupación por carril.** Determinar si la cabecera o el estado permiten separar el gas consumido por el carril de pagos del gas total. A3 se calcula contra ambas ocupaciones; si no se pueden separar, se calcula solo contra la global y se anota la limitación.

`[VERIFICAR T-5]` **Activo de pago.** Inventariar los TIP-20 con transferencias reales en los últimos 30 días y elegir los dos de mayor conteo. Reportar la lista completa con conteos. No elegir por reputación del emisor.

`[VERIFICAR T-6]` **Actualizaciones de red en la ventana.** Listar las actualizaciones activadas y su altura de activación. Alimenta C5 y condiciona la ventana.

### 4.2 Aptos

| Parámetro | Valor conocido | Acción |
|---|---|---|
| Endpoint | `https://api.mainnet.aptoslabs.com/v1` | Segundo proveedor obligatorio |
| Bloques | `GET /v1/blocks/by_height/{h}?with_transactions=true` | Marca de tiempo en microsegundos |
| Proponente | `block_metadata_transaction.proposer` | Directo |
| Unidad de versión | `first_version` / `last_version` por bloque | Posición intrabloque = versión |

`[VERIFICAR A-1]` **Activo de pago.** Inventariar las stablecoins con mayor conteo de transferencias (USDT y USDC nativas son las candidatas) y elegir las dos mayores. Reportar si son Fungible Asset o Coin: cambia el evento a filtrar.

`[VERIFICAR A-2]` **Oráculo de precio APT/USD legible en histórico.** A1 en Aptos requiere convertir octas a USD. Localizar un oráculo en cadena y comprobar que se puede leer su precio a una versión pasada. Si no se puede: se declara una desviación explícita de la regla §1.2, se toma el precio del oráculo al inicio de cada estrato horario, y se marca A1 de Aptos como `parcialmente_derivada`. Nunca usar un precio diario de una fuente externa.

`[VERIFICAR A-3]` **Límite de gas de bloque.** Localizar el recurso de configuración de ejecución que fija el límite, comprobar lectura histórica. Alimenta A3 y H_cfg.

`[VERIFICAR A-4]` **Transacciones patrocinadas.** Confirmar cómo se identifica el pagador de comisión distinto del remitente en el cuerpo de la transacción. Alimenta D1.

`[VERIFICAR A-5]` **Referencia de conciliación.** Inventariar qué funciones de entrada producen las transferencias del activo elegido y qué campos adicionales portan. Definir por escrito, antes de medir, qué se cuenta como referencia apta. Alimenta D2 y la compuerta G3, que Aptos podría no pasar.

### 4.3 Canton

| Parámetro | Valor conocido | Acción |
|---|---|---|
| Descubrimiento de Scans | `GET /api/scan/v0/scans` desde cualquier Scan de SV | Obligatorio: da la lista de SV |
| Historia de updates | `POST /api/scan/v2/updates` con cursor por `update_index` | Paginado |
| Verdicts | `/v0/events` y `/v0/events/{update_id}` | Da conteo y resultado de transacciones privadas |
| Estado | `POST /v0/state/acs` con `record_time` | Snapshots ACS |
| Sequencers | `GET /v0/dso-sequencers` | Alimenta C1b |

`[VERIFICAR C-1]` **Disponibilidad del API de verdicts en mainnet.** El API de eventos con verdicts existe en la especificación pero su exposición pública en mainnet debe comprobarse con una llamada real. Sin él, no hay conteo de actividad total, y C4, C3 y B3 quedan restringidos a lo visible al DSO. Es el ítem más crítico de toda esta fase.

`[VERIFICAR C-2]` **Retención de verdicts.** La documentación advierte que los verdicts son efímeros en el mediador y que Scan solo conserva lo que alcanzó a guardar. Determinar hasta qué fecha hay verdicts recuperables: eso fija el inicio máximo de la ventana histórica.

`[VERIFICAR C-3]` **Campos de tiempo del verdict.** Determinar si el evento expone el instante de solicitud además del de resolución. Si los expone, B1 en Canton se mide como latencia de confirmación real y es homogénea con las otras dos. Si no, B1 se marca `no_homogenea` y se mide solo cadencia del sincronizador.

`[VERIFICAR C-4]` **Tarifa de tráfico denominada en USD.** Localizar en el ACS las reglas vigentes que fijan el precio por unidad de tráfico y confirmar que `traffic_summary` permite atribuir un costo a cada update. Alimenta A1 y A3.

`[VERIFICAR C-5]` **Latido para C3.** Identificar el evento periódico del DSO que avanza independientemente del tráfico de usuarios, para no confundir ausencia de demanda con caída del sincronizador. Reportar su periodo medido.

`[VERIFICAR C-6]` **Presencia de una stablecoin bajo el estándar de token.** Confirmar que existe y estimar, desde los verdicts, cuántas transacciones involucran su registro sin exponer contenido. Alimenta D7 y E1.

`[VERIFICAR C-7]` **Concordancia entre SV.** Consultar los mismos updates desde dos Scans de super validadores distintos y comparar. Es el equivalente en Canton al control de dos proveedores de nodo.

---

## 5. Catálogo de métricas adaptado

Quince métricas: catorce heredadas (menos A4, más C1b y E1). `t` = umbral objetivo, `w` = umbral inaceptable. Sin cambios respecto del documento de referencia salvo donde se indica.

### 5.1 Bloque A — Costo

| ID | Definición | Tempo | Aptos | Canton | t | w |
|---|---|---|---|---|---|---|
| **A1** | Costo mediano por transferencia como fracción del ticket del escenario | Comisión del recibo en TIP-20 USD; sin oráculo | `gas_used × gas_unit_price` en octas → USD por oráculo en cadena | Costo de tráfico del update, ya en USD | 0,1 % | 1,0 % |
| **A2** | Percentil 95 sobre mediana, misma muestra | Igual en las tres | Igual | Igual | 1,5 | 10 |
| **A3** | Pendiente β de `ln(costo) = α + β·ocupación` | Regresar contra ocupación global **y** de carril de pagos; reportar ambas | Ocupación = gas de bloque / límite | Sustituto: tráfico total del sincronizador por intervalo. Se espera β≈0 por diseño de tarifa fija | 0,2 | 2,0 |
| ~~A4~~ | *Eliminada (D2)* | — | — | — | — | — |

### 5.2 Bloque B — Tiempo y caudal

| ID | Definición | Tempo | Aptos | Canton | t | w |
|---|---|---|---|---|---|---|
| **B1** | Latencia de inclusión, percentil 95 | Δ entre marcas de tiempo de bloques consecutivos + posición en el bloque | Igual, con marca en µs y posición por versión | Latencia de confirmación si `[C-3]` lo permite; si no, cadencia de `record_time`, marcada no homogénea | 5 s | 20 s |
| **B2** | `τF − τ1`, mediana | **Medición en vivo:** sondeo del encabezado finalizado; registrar el instante en que cada altura pasa a finalizada | **Medición en vivo:** sondeo de la altura comprometida en dos fullnodes independientes | **Histórica:** `record_time` del verdict menos `record_time` del update | 60 s | 604.800 s |
| **B3** | Margen de capacidad, desdoblado en H_obs y H_cfg (D5) | H_cfg desde parámetros de gas y capacidad del carril | H_cfg desde límite de gas de bloque y gas típico de transferencia | H_cfg desde límites de tráfico del sincronizador | 5 | 1 |

Requisito de capacidad heredado: **48 TPS** (ρ = 10 % del volumen nacional, φ = 8, N_max = 5,2 millones diarios).

### 5.3 Bloque C — Concentración y continuidad

| ID | Definición | Tempo | Aptos | Canton | t | w |
|---|---|---|---|---|---|---|
| **C1b** | Herfindahl sobre el peso de consenso de cada operador *(nueva, primaria — D3)* | Pesos del precompilado de validadores | Poder de voto de `0x1::stake` | Pesos de los SV en el ACS del DSO | 0,10 | 1,00 |
| **C1** | Herfindahl sobre fracción de bloques producidos *(secundaria)* | Según `[T-1]` | `proposer` de cada bloque | `no_computable` | 0,10 | 1,00 |
| **C2** | Mínimo número de operadores que concentran más del 50 % | Sobre C1b si C1 no es computable | Sobre producción y sobre voto | Sobre peso de SV | 15 | 1 |
| **C3** | 1 − fracción de tiempo en huecos superiores a 10× la cadencia mediana | Directo | Directo | Sobre el latido de `[C-5]`, no sobre tráfico de usuarios | 99,999 % | 99,9 % |
| **C4** | Tasa de fallo | `status` del recibo | `success` / `vm_status` | `verdict_result` rechazado sobre total | 0,1 % | 5,0 % |
| **C5** | Cambios de implementación en la ruta de pago durante la ventana | Actualizaciones de red activadas + cambios de política | Publicaciones de módulo en `0x1` y en el emisor | Cambios de versión de paquete y de reglas del DSO | 0 | 5 |

C4 es la métrica que porta con mayor limpieza a las tres: el verdict del mediador es un equivalente exacto del estado de un recibo.

### 5.4 Bloque D — Primitivas observadas en uso

| ID | Definición | Tempo | Aptos | Canton | t | w |
|---|---|---|---|---|---|---|
| **D1** | Proporción de transferencias en que el pagador no gastó un activo volátil de su propio balance para poder pagar | 100 % por construcción — reportar como **degenerada**; sub-métrica útil: proporción con comisión patrocinada por un tercero | Transacciones con pagador de comisión distinto del remitente | Declarar el sujeto: el usuario final no compra tráfico, lo compra el operador. Medir y explicar | 50 % | 1 % |
| **D2** | Proporción de transferencias que portan datos aptos para asociarse a una orden externa | Memo nativo de 32 bytes no nulo | Definición operativa de `[A-5]`; riesgo real de resultar ≈ 0 | Campos de metadatos del estándar de token, solo en activos visibles | 20 % | 0,1 % |
| **D3** | Proporción de transacciones con más de una transferencia, y con transferencias de dos o más activos | Conteo de eventos por transacción; Tempo soporta agrupación nativa | Eventos por transacción y transacciones multi-agente | Updates con más de un evento de transferencia y con dos o más instrumentos | 10 % | 0,1 % |

### 5.5 Métrica transversal

| ID | Definición | Reporte |
|---|---|---|
| **E1** | Proporción de transferencias del activo de pago cuyo monto, contrapartes y resultado son verificables por un tercero no contraparte *(nueva — D4)* | Se reporta siempre por red **y por activo**. No se puntúa: opera como compuerta G2′ |

### 5.6 Pesos

Pesos por bloque heredados sin cambio:

| Bloque | E1 Remesas | E2 Comercio | E3 Alto valor |
|---|---|---|---|
| A Costo | 0,45 | 0,35 | 0,10 |
| B Tiempo y caudal | 0,15 | 0,35 | 0,30 |
| C Concentración | 0,15 | 0,15 | 0,40 |
| D Primitivas | 0,25 | 0,15 | 0,20 |

Pesos internos de A, renormalizados tras eliminar A4:

- E1 Remesas: A1 = 0,526 · A2 = 0,263 · A3 = 0,211
- E2 Comercio: A1 = 0,389 · A2 = 0,278 · A3 = 0,333
- E3 Alto valor: uniformes

Dentro de B: B1 domina en E2 con 0,60; B2 domina en E3 con 0,55. Dentro de C, C1b toma el peso que C1 tenía y el resto uniforme. Dentro de D, uniformes.

### 5.7 Normalización y agregación

Sin cambios respecto del documento de referencia.

```
menor es mejor:  s = clip[ (ln w − ln x) / (ln w − ln t), 0, 1 ]
mayor es mejor:  s = clip[ (ln x − ln w) / (ln t − ln w), 0, 1 ]
```

Para C3, transformar antes al número de nueves: `ν(A) = −log₁₀(1 − A/100)`.

Agregación: media aritmética ponderada dentro de cada bloque; media geométrica ponderada entre bloques con piso ε = 0,05.

```
S_d = Σ ω_i s_i          S = Π_d [ max(S_d, 0,05) ] ^ W_d
```

Sensibilidad: `W ~ Dirichlet(50·W₀)`, 10.000 réplicas, reporte por bandas de desempeño y no por puestos.

---

## 6. Compuertas

Se evalúan antes del puntaje. Fallar una compuerta aplicable significa **inadmisible sin puntaje**, no cero.

| ID | Condición | Escenarios | Cambio respecto del original |
|---|---|---|---|
| **G1** | B1 no superior a 20 s | E2 | Sin cambio |
| **G2′** | Existe un registro público consultable por un tercero no contraparte que permite verificar tanto la inclusión como la irreversibilidad de la transferencia. Operacionalmente: **E1 = 1 y τF computable** | Todos | **Sustituye a G2.** Tempo y Aptos pasan. Canton pasa con Canton Coin y falla con una stablecoin bajo el estándar de token |
| **G3** | D2 mayor que cero | Todos | Sin cambio. Aptos podría fallarla |
| **G4** | **H_cfg** no inferior a 1 | E2, E3 | Se evalúa contra capacidad configurada, no contra caudal observado (D5) |

Cada evaluación de compuerta debe registrar el valor medido que la sustenta, no solo el veredicto.

---

## 7. Ventana, muestreo y controles

### 7.1 Dos ventanas

**Ventana histórica (W_H)** — para todas las métricas salvo B2.

- Duración: 14 días consecutivos completos.
- Debe contener al menos: una quincena (día 15 o 30), un fin de mes, dos fines de semana.
- Debe iniciar después del último cambio arquitectónico relevante en cualquiera de las tres redes. Tempo ha publicado actualizaciones de red con alta frecuencia: si no existe una ventana común de 14 días libre de actualizaciones, se elige la ventana más larga disponible, se declara su duración real y se listan las actualizaciones contenidas.
- Límite superior de antigüedad en Canton: lo que fije la retención de verdicts de `[C-2]`.

**Ventana en vivo (W_L)** — solo para B2 en Tempo y Aptos.

- Duración mínima: 72 horas continuas, solapadas con W_H o inmediatamente posteriores.
- Sondeo del encabezado finalizado a intervalo no mayor a 100 ms.
- Registrar la marca de tiempo local del observador junto a la de la red, y reportar la deriva del reloj del observador. Sin ese registro la medición no es auditable.

### 7.2 Estratificación

- 24 estratos por hora del día × 3 tipos de día (hábil, no hábil, quincena).
- Objetivo: 100 transferencias por celda, del orden de 7.200 por red.
- **Regla de contingencia obligatoria:** si una celda no alcanza 100 transferencias, se toman todas las existentes (censo, no muestra) y se registra `n` real por celda. Con Tempo y Canton es probable que ocurra en la mayoría de celdas. Un `n` bajo declarado es válido; un `n` inventado o un percentil calculado sobre 4 observaciones sin advertirlo, no.
- Módulos de bloques y de mutabilidad: cobertura completa, no muestral.

### 7.3 Controles de validez

- Dos proveedores de nodo independientes por red. En Canton, dos Scans de super validadores distintos `[C-7]`. Toda discrepancia superior al 5 % se investiga y se documenta.
- Precio del activo de comisión desde oráculo en el registro, en la versión o bloque correspondiente. Solo Aptos lo necesita.
- Criterio de filtrado de "qué cuenta como transferencia de pago" publicado por escrito antes de recolectar.
- Transacciones fallidas incluidas en la muestra y reportadas en C4, nunca excluidas.
- Rango exacto publicado junto al código: alturas de bloque en Tempo, versiones de ledger en Aptos, `record_time` y `update_index` en Canton.
- Registro del número de consultas consumidas por red y proveedor.

---

## 8. Módulos del recolector

| # | Módulo | Tempo | Aptos | Canton | Alimenta |
|---|---|---|---|---|---|
| 1 | Lector de bloques / updates | Recorre todas las alturas de W_H | Recorre todas las alturas, guarda `block_metadata_transaction` | Recorre el histórico de updates paginando por cursor | B1, B3, C1, C1b, C3, A3 |
| 2 | Indexador de transferencias | Logs del TIP-20 + recibos | Eventos de Fungible Asset + transacciones | Eventos de transferencia visibles al DSO | A1, A2, C4, E1 |
| 3 | Observador de finalidad | Sondeo en vivo del encabezado finalizado | Sondeo en vivo de altura comprometida en dos fullnodes independientes | Lectura histórica de verdicts | B2 |
| 4 | Clasificador de primitivas | Memos, tipo de transacción, patrocinio, eventos por transacción | Pagador de comisión, argumentos de entrada, eventos por transacción | Metadatos, eventos por update, instrumentos por update | D1, D2, D3 |
| 5 | Detector de mutabilidad | Activaciones de actualización de red y cambios de política | Publicaciones de módulo | Cambios de paquete y de reglas del DSO | C5 |
| 6 | Lector de estado de consenso | Precompilado de validadores | `0x1::stake` vía vista | ACS del DSO y lista de sequencers | C1b, C2 |
| 7 | Contador de actividad total | Todas las transacciones del bloque | Todas las transacciones | **Verdicts**, incluidas las privadas | C4, B3, E1 |
| 8 | Motor de cálculo | Común a las tres | | | Todas |

A diferencia del estudio de referencia, **los módulos 1 a 7 no son compartidos entre redes**. Solo el módulo 8 lo es. Presupuestar tres implementaciones separadas para los módulos 1, 2 y 4, y dos para el 3.

---

## 9. Entregables — esto es lo único que se recibe

Directorio `resultados/`, con:

**`metrics.csv`** — formato largo, una fila por combinación:

| columna | contenido |
|---|---|
| `red` | tempo / aptos / canton |
| `activo` | identificador del activo de pago medido |
| `metrica_id` | A1, A2, A3, B1, B2, B3, C1, C1b, C2, C3, C4, C5, D1, D2, D3, E1 |
| `escenario` | E1 / E2 / E3 / global |
| `valor` | valor medido |
| `unidad` | fracción, segundos, USD, índice, conteo, porcentaje |
| `n` | tamaño muestral efectivo |
| `ic_bajo`, `ic_alto` | bootstrap de 10.000 réplicas |
| `estado` | `computada` / `parcialmente_derivada` / `no_computable` / `degenerada` / `no_homogenea` |
| `razon_estado` | obligatorio si el estado no es `computada` |
| `consulta_ref` | identificador de la consulta reproducible que produjo el valor |

**`gates.csv`** — red × activo × escenario × compuerta → `pasa` / `falla` / `no_evaluable`, con el valor medido que lo sustenta.

**`scores.csv`** — puntajes normalizados por métrica, puntaje por bloque, puntaje agregado S por escenario. Redes inadmisibles aparecen con S vacío y la compuerta que las excluyó, nunca con cero.

**`sensitivity.csv`** — banda de desempeño por red y escenario sobre 10.000 réplicas Dirichlet.

**`discrimination.csv`** — por métrica: rango de valores entre las tres redes, y si discriminó o no. Es un resultado propio del estudio.

**`run_manifest.json`** — endpoints y proveedores usados, rangos exactos (alturas, versiones, `record_time`), fechas de W_H y W_L, conteo de consultas, discrepancias entre proveedores detectadas y cómo se resolvieron, versión del código.

**`limitaciones.md`** — generado automáticamente: una entrada por cada métrica no computada, con la razón y la consulta que se intentó. Este archivo es un entregable de primera clase, no un apéndice.

**`raw/`** — datos crudos por red en formato columnar, suficientes para recalcular todo sin volver a consultar la red.

---

## 10. Reglas de honestidad para el agente

1. **Nunca completar un valor con documentación.** Si la red no lo expone, el estado es `no_computable` y se explica por qué. Un número tomado de un blog o de una especificación invalida el estudio entero.
2. **Nunca extrapolar de testnet a mainnet.** Si mainnet no tiene el dato, no lo tiene.
3. **Nunca emitir transacciones propias.** El estudio observa tráfico real de terceros. Emitir transacciones para generar muestra cambia el objeto medido.
4. **Nunca convertirse en contraparte en Canton** para acceder a datos privados.
5. **Reportar `n` siempre**, y marcar todo percentil calculado sobre menos de 30 observaciones.
6. **Distinguir capacidad de demanda.** Un caudal bajo por ausencia de usuarios no es un caudal bajo por falta de capacidad, y se reporta como lo primero.
7. **Marcar `degenerada`** toda métrica cuyo valor esté determinado por la arquitectura y no por el comportamiento. Ejemplo: D1 en Tempo vale 100 % porque no existe token nativo, no porque los usuarios hayan adoptado nada.
8. **Detenerse y reportar** ante cualquier `[VERIFICAR]` no resuelto, en vez de continuar con un supuesto.

---

## Anexo — Umbrales heredados del mercado colombiano

Fuente: documento técnico del Banco de la República sobre Bre-B, febrero de 2026. No se recolectan: se usan como umbrales.

| Hecho | Valor | Uso |
|---|---|---|
| Tiempo máximo de transferencia inmediata | 20 s | Umbral inaceptable de B1 y compuerta G1 |
| Ticket promedio | COP 159.456 | Denominador de A1 |
| Máximo diario observado (31-ene-2026) | 5,2 millones de operaciones | Requisito de capacidad |
| Costo entre personas naturales | Sin costo | Contrafactual de E2 |
| Operaciones desde billeteras de bajo monto | 50 % | Justifica el peso de D1 |
| Estándar de mensajería | ISO 20022 | Justifica D2 |
| Remesas recibidas en 2025 | USD 13.098 millones | Dimensiona E1 |
| Meta internacional de costo de remesas | Menos del 3 % | Umbral de A1 en remesas |

**Requisito de capacidad:** `TPS_req(ρ) = ρ · φ · N_max / 86.400`. Con φ = 8 y ρ = 10 %: **48 TPS**.

**Techos de comisión por segmento:**

| Segmento | Ticket ≈ USD | Techo al 1 % | Techo al 0,1 % |
|---|---|---|---|
| Comercio de barrio | 3,8 | USD 0,038 | USD 0,004 |
| Transferencia P2P promedio | 40 | USD 0,40 | USD 0,04 |
| Remesa familiar | 300 | USD 3,00 | USD 0,30 |

**Escenarios:**

| | E1 Remesas | E2 Comercio doméstico | E3 Alto valor |
|---|---|---|---|
| Ticket | USD 200–500 | COP 15.000 a 159.456 | Superior a COP 100 millones |
| Restricción dominante | Costo | Latencia de inclusión | Irreversibilidad y concentración |
| Tolerancia a latencia | Alta: horas | Baja: segundos | Media: minutos |
| Compuertas | G2′, G3 | G1, G2′, G3, G4 | G2′, G3, G4 |
