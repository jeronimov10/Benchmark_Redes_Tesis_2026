# Limitaciones

Generado el 2026-11-16. Aplican a los resultados de [benchmark.md](benchmark.md) y [pruebas.md](pruebas.md). Un `no_computable` con su razon es un resultado valido; un valor parcial se publica con su advertencia, nunca como un numero limpio.

## Estados

- **medida**: el valor sale de una consulta reproducible al registro publico de la red.
- **parcial** (`parcialmente_derivada`): hay valor, con un supuesto o una advertencia que no se pudo verificar.
- **cota inferior**: la red no se saturo en la ventana; el valor es un minimo de lo que sostiene.
- **no computable**: no se puede derivar de una consulta reproducible; no se completa con documentacion.
- **no aplica**: la metrica no tiene sentido para esa arquitectura.

## Limitaciones que afectan a todas las redes

- **Ventanas distintas entre grupos.** Polygon, Celo y Arbitrum vienen de la medicion de la tesis (ventana de 90 dias, octubre de 2026, `backend/modelo/perfiles.json`). Tempo, Aptos y Canton vienen de una muestra reducida de verificacion (Tempo: 700 bloques y 220 transacciones; Aptos: 350 bloques; Canton: 8 000 eventos en unos 493 s del 2026-09-07, una ventana dominada por un burst periodico y no representativa del trafico tipico), no de la ventana W_H de 14 dias que fija el plan. Las seis columnas son comparables en definicion de metrica, no en tamano de muestra ni en fecha.
- **Un solo proveedor por red.** El plan exige un segundo proveedor independiente por red para el control de concordancia. No se cumplio para ninguna: cada red se consulto con un unico endpoint publico (`resultados/run_manifest.json`). En Canton ademas es un espejo publico de terceros (`api.cantonnodes.com`), porque los Scan de los Super Validadores rechazan el acceso publico (403/RBAC).
- **Sin bootstrap en Tempo, Aptos y Canton.** Los valores de T/A/C no traen intervalo de confianza; en el modelo entran con `sigma = 0`, de modo que la incertidumbre del Monte Carlo para esas redes viene solo de los pesos, no de la medicion.
- **A4 solo existe en Polygon, Celo y Arbitrum.** A4 (costo de anclaje) aplica a los rollups que publican en Ethereum. Tempo, Aptos y Canton son redes de capa 1 propia: A4 no aplica y no se imputa.
- **Compuerta G2 y Aptos.** El modelo marca a Aptos como inadmisible por G2 (`sin anclaje verificable en Ethereum`) porque su B2 no es computable. Es un efecto de que falta la medicion, no una evidencia de que Aptos no sea apta: sin B2 la red no puede pasar la compuerta.
- **Monte Carlo sin semilla en el motor de puntajes.** El Monte Carlo del motor del plan (`score_engine.py`) usa el generador de numeros aleatorios sin semilla, asi que `sensitivity.csv` cambia ligeramente entre ejecuciones; el modelo de la tesis (`modelo.recomendar`) usa semilla 42 y es determinista.
- **TRM fija.** Todos los casos usan 4 000 COP/USD, como la tesis; el ticket en USD depende de ese supuesto.
- **Quirk de `normaliza()` con log(0).** En `score_engine.py`, una metrica `mayor es mejor` con valor exactamente 0 (hoy `canton.D3 = 0`) se excluye del promedio del bloque sin contar como cero puntos; mirar `n_D` en `scores.csv` antes de leer el bloque D. No se corrigio porque cambiaria el puntaje de las 18 combinaciones red x escenario.
- **Los RPC publicos son inestables.** Los endpoints publicos cambian de proveedor, limitan por IP (Aptos anonimo cobra por tamano de respuesta) y los nodos L1 publicos guardan solo ~10 000 bloques; por eso la recalibracion en vivo de P/C/A usa una ventana de 24 h y no sustituye la linea base de 90 dias.

## Por red

### Polygon

- A3 no computable: el ajuste de la pendiente de congestion no es util (R2 0,003).
- B3 es cota inferior: la red no se saturo en la ventana (141,3 TPS en el percentil 99 frente a 18 requeridos).
- C3 esta marcada como documental en la linea base: cota al 95 % con 0 incidentes en 356 dias, no un valor medido con una consulta a la red.
- C1 y C2 salen de 8 productores de bloques observados en 19 509 bloques; C5 sale de 61 lecturas de la ranura de implementacion del proxy (zeppelin).
- B3, D2 y D3 provienen solo de la linea base: la metrica en vivo no las reemplaza porque necesita ventanas largas.

### Celo

- A3 no computable: el ajuste no es util (R2 0,046).
- B3 es cota inferior: 36,0 TPS en el percentil 99 frente a 18 requeridos, sin saturacion.
- C1 = 1 y C2 = 1 reflejan un productor unico de direccion de sistema, que no identifica a una organizacion; el valor describe la arquitectura, no el reparto entre operadores.
- B2b tiene n = 122 confirmaciones en Ethereum (p95 3,52 dias).
- C3 esta marcada como documental en la linea base: cota al 95 % con 1 incidente en 552 dias, no una medicion con una consulta a la red.
- B3, D2 y D3 provienen solo de la linea base: la metrica en vivo no las reemplaza porque necesita ventanas largas.

### Arbitrum

- A3 no computable: la ocupacion es casi constante (rango 0,0000), no hay variacion para ajustar.
- B3 es cota inferior: 115,8 TPS en el percentil 99 frente a 18 requeridos, sin saturacion.
- C1 = 0,994 y C2 = 1 sobre 16 direcciones productoras observadas en 20 000 bloques.
- B2b tiene n = 118 confirmaciones en Ethereum (p95 6,45 dias); el tamano de muestra de D2 y D3 es el menor de las tres (2 266 transacciones).
- C3 esta marcada como documental en la linea base: cota al 95 % con 0 incidentes en 271 dias, no una medicion con una consulta a la red.
- B3, D2 y D3 provienen solo de la linea base: la metrica en vivo no las reemplaza porque necesita ventanas largas.

### Tempo

- **A1** (parcialmente_derivada) = 2.02e-05 : muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap; supuesto 18 decimales de precio de gas no confirmado contra TIP publicado
- **A2** (parcialmente_derivada) = 0.000179 : muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap
- **A3** (parcialmente_derivada) = 2.02e+03 : muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap; n muy pequeno para una regresion confiable, sin R2
- **B2** (parcialmente_derivada) = 0.6302 : Mecanismo de sondeo en vivo (backend/benchmark/poll_finality.py) verificado y corrido 30s como demostracion (no las 72h de W_L que exige el plan). p95=0.81s. Confirma la advertencia del plan: tau_F es sub-segundo en Tempo, no discrimina frente al umbral t=60s/w=604800s -- el eje de irreversibilidad no separa a esta red en esta muestra.
- **B3** (parcialmente_derivada) = 556.8 : H_cfg = (gasLimit=500000000 / gasUsed_mediana=33587) / cadencia_mediana=0.557s, sobre 48 TPS de referencia. No separa carril de pagos de ocupacion global (T-4 sigue abierto) -- es capacidad agregada del bloque completo, un limite superior optimista.
- **D3** (parcialmente_derivada) = 0.7682 : probablemente sobreestimada: incluye Transfer logs del reparto de comision (TipFeeManager), no solo pagos multi-instrumento genuinos
- **C1b** (medida, con nota): T-2 RESUELTO: direccion 0xCCCCCCCC...01 (ValidatorConfigV2) hallada en codigo fuente (github.com/tempoxyz/tempo, crates/contracts/src/precompiles/mod.rs) y verificada con eth_call en vivo. El ABI no expone campo de peso/stake por validador -> consenso es de peso igualitario (1/N), no ponderado como en Aptos
- **C2** (medida, con nota): sobre C1b (peso real, ahora resuelta): con pesos iguales entre 15 validadores activos, el umbral del 50% se cruza en el validador numero 8
- **C3** (medida, con nota): Reconstruido con datos historicos, no requiere sondeo en vivo (a diferencia de B2): huecos > 10x la cadencia mediana sobre los mismos bloques ya descargados. muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap
- **C5** (medida, con nota): RESUELTO en esta pasada: se encontro una extension RPC admisible del propio nodo, tempo_forkSchedule (confirmada leyendo crates/node/src/rpc/fork_schedule.rs en el codigo fuente publico), que expone el schedule completo de TIPs con su activationTime real -- fuente del registro, no el changelog/TIPs de GitHub (eso si violaria la regla de oro). En la ventana muestreada ([1788918165.369, 1788918555.9], ~6.5 min) no se activo ningun fork nuevo ([]); fork activo actual: T11. 0 en una ventana de minutos es el resultado esperado, no una falla -- los forks de Tempo se activan con semanas de separacion segun el propio schedule.
- **D1** (medida, con nota): OJO: 100% en la muestra; posible artefacto de la abstraccion de cuentas nativa de Tempo (feePayer podria estar siempre poblado por diseno, no solo cuando un tercero patrocina)
- **D2** (medida, con nota): RESUELTO en esta pasada: la interfaz ITIP20 (crates/contracts/src/precompiles/tip20.rs, codigo fuente publico) confirma la funcion transferWithMemo(address,uint256,bytes32) y su evento TransferWithMemo(address indexed from, address indexed to, uint256 amount, bytes32 indexed memo). D2 se mide via el topic0 de ese evento (keccak256 calculado, no copiado) sobre los logs ya descargados de las mismas transacciones usadas para D3 -- reconstruible con datos historicos, no requirio nueva consulta a la red.

### Aptos

- **A1** (parcialmente_derivada) = 0.000286 : RESUELTO en esta pasada: el ID de 32 bytes del feed APT/USD de Pyth se obtuvo de la propia API en vivo de Pyth (hermes.pyth.network/v2/price_feeds?query=APT), no se adivino -- y se verifico contra el contrato en Aptos (POST /v1/tables/{handle}/item devuelve el mismo price_identifier que se consulto, autoconsistente). El oraculo sigue CONGELADO desde 2026-08-26 (timestamp on-chain confirmado: 1787760528 unix = 2026-08-26 16:08:48 UTC, coincide con la fecha de congelamiento documentada). Precio usado: 0.55654017 USD/APT, fijo para toda la muestra -- exactamente la desviacion explicita que preve el plan (Sec.4.2 [VERIFICAR A-2]: precio congelado, parcialmente_derivada, no computada limpia). costo_usd = gas_used*gas_unit_price/1e8 (octas->APT) * precio congelado.
- **A2** (parcialmente_derivada) = 0.000662 : misma resolucion y misma advertencia de precio congelado que A1
- **B2** (no_computable) : Se intento un sondeo corto (30s, backend/benchmark/poll_finality.py) y produjo 17 alturas nuevas pero solo 3 con delta valido, con signos mezclados (-0.09s, +0.03s, -0.56s). Hallazgo metodologico real: el tiempo de bloque de Aptos (~20ms) es mas rapido que el round-trip HTTP hacia la API publica, asi que un sondeo secuencial simple no puede resolver B2 aqui -- se necesitaria un nodo de baja latencia o streaming, no polling HTTP estandar. NO es reconstruible con datos historicos por definicion (D1 del plan): requiere W_L en vivo.
- **A3** (parcialmente_derivada) = 8.628 : RESUELTO en esta pasada: el blob BCS de 0x1::execution_config::ExecutionConfig se decodifico contra el layout EXACTO de OnChainExecutionConfig (verificado leyendo types/src/on_chain_config/execution_config.rs en aptos-labs/aptos-core, codigo fuente publico -- 79 de 79 bytes consumidos sin sobrante, fuerte indicio de que el layout es correcto). Variante V7 activa, block_gas_limit_type=ComplexLimitV1, effective_block_gas_limit=300000. SIMPLIFICACION DECLARADA: la formula real del protocolo pondera execution_gas/io_gas por separado y penaliza conflictos en una ventana (ver comentario en el propio struct); aqui se usa gas_used total sin ponderar como proxy de ocupacion (los multiplicadores son 1 y el conflict_penalty_window no se rastrea desde REST), asi que beta es aproximado, no exacto. muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap
- **B3** (parcialmente_derivada) = 593.2 : RESUELTO en esta pasada, mismo decode verificado que A3: H_cfg = (block_gas_limit=300000 / gas_used_mediana=477) / cadencia_mediana_bloque, sobre 48 TPS de referencia. Es capacidad agregada del bloque completo (no separa por tipo de transaccion), igual limitacion declarada que en Tempo B3 -- limite superior optimista, no un carril de pagos aislado.
- **D2** (no_computable) : depende de fijar primero la definicion operativa de A-5, como exige el propio plan
- **D3** (parcialmente_derivada) = 1 : RESUELTO en esta pasada: se resolvio el `store` de cada evento 0x1::fungible_asset::Deposit/Withdraw a su activo real via 0x1::fungible_asset::FungibleStore.metadata (29 stores distintos, 29/29 resueltos, colapsan a solo 3 activos reales). multi-transferencia (>1 evento FA por tx) = 1.0; multi-activo (>1 activo distinto por tx) = 0.4166666666666667. ADVERTENCIA: n=12 es MUY pequeno (la muestra de bloques esta dominada por un protocolo de trading de derivados, modulo 0x50ead22a..., no por transferencias de pago simples), y estos numeros probablemente miden rebalanceo de colateral de trading (depositar/retirar garantia en mas de un activo durante una operacion), no pagos multi-instrumento genuinos -- mismo tipo de contaminacion que D3 en Tempo (TipFeeManager) y Canton (reward coupons), reportada con la misma regla: el dato real con la advertencia, no un numero limpio sin verificar la causa.
- **C1b** (medida, con nota): peso de consenso completo (84 validadores activos), no es muestra temporal
- **C2** (medida, con nota): sobre C1b (peso), que es la metrica primaria segun el plan (D3)
- **C5** (medida, con nota): Reconstruido con datos historicos (mismos bloques ya descargados): cuenta entry functions de publicacion de codigo (0x1::code::publish_package_txn y variantes) entre las transacciones de la muestra. 0 en la ventana muestreada es un resultado valido, no una falla. muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap

### Canton

- **A1** (parcialmente_derivada) = 0.8953 : Unidad CONFIRMADA via docs.sync.global (Synchronizer Traffic Fees, CIP-0042/CIP-0084): trafficPrice=60 USD/MB, total_traffic_cost en bytes. Coincide con el objetivo de diseno de CIP-0042 (~1 USD por transferencia estandar de CC). Sigue parcial porque la ventana (~189s) cae en un burst periodico de ValidatorLicense_ReportActive, no en trafico de pagos tipico.
- **A2** (parcialmente_derivada) = 2.75 : misma confirmacion de unidad que A1; misma limitacion de ventana no representativa
- **B3** (parcialmente_derivada) = 0.000233 : Reconstruido con datos historicos: baseRateTrafficLimits en dso_rules ya estaba descargado (burstAmount=200000.0 bytes cada burstWindow=1200.0s -> 166.67 bytes/s), dividido por el costo mediano en bytes de una transferencia (A1). ADVERTENCIA METODOLOGICA IMPORTANTE: este campo es la asignacion GRATUITA por MIEMBRO antes de tener que comprar trafico extra (ver choice AmuletRules_BuyMemberTraffic, extraTrafficPrice=60 USD/MB en el mismo estado) -- no es un techo agregado del sincronizador completo. H_cfg=0.00023270707206100275 probablemente SUBESTIMA drasticamente la capacidad real de Canton, porque el trafico adicional se compra sin un limite aparente en el estado consultado. Se reporta como lectura conservadora de un miembro individual, no como el techo real de la red -- no interpretar como 'Canton no puede sostener 48 TPS'.
- **C1** (no_computable) : degenerada por diseno: Canton no tiene bloques
- **D3** (parcialmente_derivada) = 0 : Reconstruido con datos historicos sobre las mismas choices de transferencia. multi-transferencia (>1 salida) = 0.0. multi-activo (>1 instrumento de entrada, normalizando holdings bloqueados del mismo activo) = 0.20939334637964774: este segundo numero esta probablemente CONTAMINADO por la redencion de reward coupons (SvRewardCoupon/AppRewardCoupon/ValidatorRewardCoupon) dentro de la misma choice AmuletRules_Transfer -- mecanica de protocolo/incentivos, no pagos multi-instrumento genuinos por el usuario. Mismo tipo de advertencia que D3 en Tempo con TipFeeManager.
- **E1** (parcialmente_derivada) = 0 : USDCx esta confirmado vivo en mainnet por fuente externa (canton.network/blog, circle.com/blog, CIP-56), pero la busqueda propia de template_id tipo Holding/Token en 10.400 eventos reales sobre DOS ventanas distintas (una de burst de medianoche, otra de 8 min en horario habil) no encontro ninguno -- todos los templates visibles son nativos de Amulet/Splice. Esto es evidencia mas fuerte que antes de que, si USDCx circula, su actividad visible es muy escasa frente a la nativa, o bien nunca deja `update` visible (solo verdict) -- consistente con D7 del plan: si es privada, E1=0 para ese activo es precisamente el resultado esperado, no una falla de busqueda.
- **A3** (medida, con nota): Reconstruido con datos historicos ya descargados: regresion ln(costo individual) ~ trafico total del sincronizador en buckets de 10s (sustituto de ocupacion, Sec.5.1 del plan). beta≈0 (5.520907138389642e-08) es el resultado ESPERADO por diseno de tarifa fija (trafficPrice constante en USD/MB, no varia con la congestion) -- confirma la prediccion del plan, no es un calculo fallido.
- **B1** (medida, con nota): En Canton B1 (latencia de inclusion) y B2 (irreversibilidad) coinciden: finalization_time - record_time del mismo verdict es, a la vez, cuando se incluye y cuando queda firme. No hay un segundo instante de finalidad separado como en Tempo/Aptos. muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap; ventana de solo ~189s dominada por un burst, no representativa de latencia tipica
- **B2** (medida, con nota): En Canton B1 (latencia de inclusion) y B2 (irreversibilidad) coinciden: finalization_time - record_time del mismo verdict es, a la vez, cuando se incluye y cuando queda firme. No hay un segundo instante de finalidad separado como en Tempo/Aptos.
- **C1b** (medida, con nota): Reconstruido con datos historicos ya descargados: dso_rules.svs (dso_state.json, collect_canton.py) trae svRewardWeight por cada Super Validador; no requirio nueva consulta, solo leerlo. Cobertura completa del conjunto de SV (no es muestra temporal).
- **C2** (medida, con nota): sobre C1b (peso real via svRewardWeight)
- **C3** (medida, con nota): Reconstruido con datos historicos: se identifico el latido del DSO independiente del trafico de usuarios (choice ValidatorLicense_ReportActive, cadencia mediana observada 2.574089s), tal como pide C-5/C3 del plan para no confundir ausencia de demanda con caida del sincronizador. Continuidad sobre ese latido, no sobre pagos. muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap
- **C5** (medida, con nota): Definicion operativa declarada (el plan no fija una lista cerrada de que choice cuenta como 'cambio de la ruta de pago'): se cuentan choices DsoRules_* que exceden el ruido rutinario (votos de precio, reportes de estado, confirmaciones y merges de recompensa ya contados por otras metricas); detalle: {"DsoRules_ExpireStaleConfirmation": 1, "DsoRules_AdvanceOpenMiningRounds": 1, "DsoRules_MiningRound_Close": 1, "DsoRules_ExecuteConfirmedAction": 3, "DsoRules_ClaimExpiredRewards": 3, "DsoRules_ProcessRewardsV2_ProcessBatch": 1, "DsoRules_MergeUnclaimedRewards": 1}. 0 en la ventana muestreada seria un resultado igualmente valido.
- **D1** (medida, con nota): Sujeto declarado segun Sec.5.4 del plan: 'el operador compra trafico, no el usuario'. Degenerada por arquitectura, igual que Tempo D1=100%: el costo de red (trafico del sincronizador) lo adquiere el operador del validador/app provider, no el usuario final gastando un activo volatil propio para pagar la comision de red.
- **D2** (medida, con nota): Reconstruido con datos historicos: sobre las choices de transferencia real (TransferFactory_Transfer, AmuletRules_Transfer), se mide la fraccion con el campo `meta` del estandar de token no vacio -- exactamente el mecanismo que el plan preve para D2 en activos visibles al DSO.

## Por metrica

| metrica | Polygon | Celo | Arbitrum | Tempo | Aptos | Canton |
|---|---|---|---|---|---|---|
| **A1** | medida | medida | medida | parcial | parcial | parcial |
| **A2** | medida | medida | medida | parcial | parcial | parcial |
| **A3** | no computable | no computable | no computable | parcial | parcial | medida |
| **A4** | medida | medida | medida | no computable | no computable | no computable |
| **B1** | medida | medida | medida | medida | medida | medida |
| **B2** | medida | medida | medida | parcial | no computable | medida |
| **B2b** | medida | medida | medida | no computable | no computable | no computable |
| **B3** | cota inferior | cota inferior | cota inferior | parcial | parcial | cota inferior |
| **C1** | medida | medida | medida | medida | medida | medida |
| **C2** | medida | medida | medida | medida | medida | medida |
| **C3** | medida | medida | medida | medida | medida | medida |
| **C4** | medida | medida | medida | medida | medida | medida |
| **C5** | medida | medida | medida | medida | medida | medida |
| **D1** | medida | medida | medida | medida | medida | medida |
| **D2** | medida | medida | medida | medida | no computable | medida |
| **D3** | medida | medida | medida | parcial | parcial | parcial |

## Que falta para cerrar los huecos

- **aptos.B2**: sondeo en vivo de la finalidad durante 72 h en al menos dos fullnodes (`backend/benchmark/poll_finality.py`); el tiempo de bloque de Aptos (~20 ms) es menor que el viaje HTTP a la API publica, asi que un sondeo HTTP simple no basta.
- **aptos.D2**: fijar por escrito la definicion operativa de referencia apta (A-5) y recolectar transferencias de pago reales; la muestra actual esta dominada por un protocolo de derivados.
- **canton.C1**: no es un hueco de datos; Canton no tiene bloques y C1b es la metrica de concentracion primaria.
- **canton.B3**: usar el techo agregado del sincronizador en lugar de la asignacion gratuita por miembro (`baseRateTrafficLimits`); hasta entonces es una lectura conservadora que no debe citarse como que Canton no puede sostener 48 TPS.
- **Ventana W_H completa**: aumentar `N_BLOCKS_TEMPO`, `N_BLOCKS_APTOS` y `MAX_PAGES` y volver a correr `python backend/benchmark/main.py --collect`.
- **Segundo proveedor por red** para el control de concordancia.
- **Precio de APT**: el oraculo Pyth esta congelado desde 2026-08-26 en 0,55654017 USD/APT y se aplica fijo a toda la muestra (`aptos.A1`, `aptos.A2`); no hay otra fuente verificable.

## Banco de usuarios simulados

- Los 12 perfiles son personas sinteticas: los rangos de los perfiles 4 a 12 son supuestos de diseno, no datos de usuarios reales. Los resultados se leen por perfil, nunca como porcentaje de la poblacion.
- El panel continuo (P7) usa 60 a 63 de 74 metricas vivas esperadas; el resto cae a la linea base y el informe marca la procedencia.
- Un perfil que llega al tope de 400 usuarios en P1 (Micropago de transporte, y Remesa urgente en vivo) indica que la cuota modal no se estabilizo con el tope fijado.
- El umbral de lo que cuenta como cuota relevante de alertas no se fijo: se reportan las cifras, no un veredicto.
- Los contrafactuales solo quitan redes, metricas o sigma; no inventan datos.
- El panel corrio unos 11,9 dias, por encima del minimo de 3 dias que pide B2 de Tempo (72 h) y por debajo de los 14 dias ideales.
