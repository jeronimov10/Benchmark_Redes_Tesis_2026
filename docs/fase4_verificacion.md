# Fase 4 — Verificación de configuración (ejecutada)

**Fecha de ejecución:** 2026-09-07
**Regla seguida:** todo lo que aparece abajo como "confirmado" proviene de una respuesta real de un endpoint en vivo, capturada en esta sesión. Lo que no pudo confirmarse en vivo queda marcado explícitamente como tal — no se completó nada con documentación.

Estado global: **la fase bloqueante queda parcialmente resuelta.** Hay dos `[VERIFICAR]` que siguen abiertos (T-2 y, en menor medida, A-2/A-3 requieren herramienta adicional). Según la regla de oro del documento (§10.8), esto se reporta y no se avanza a inventariar/recolectar en masa sobre esos puntos hasta resolverlos.

---

## Tempo

**Endpoint usado:** `https://rpc.tempo.xyz` (JSON-RPC). Confirmado con `eth_chainId` → `0x1079` = 4217. ✅

| Ítem | Resultado | Evidencia |
|---|---|---|
| Chain ID | Confirmado: 4217 | `eth_chainId` → `0x1079` |
| Inicio de mainnet | **Corrige al plan.** Bloque 1 tiene `timestamp = 0x696aa4c7` = 2026-01-16 20:51:19 UTC, no el 18 de marzo de 2026 que traía el plan como "valor conocido" | `eth_getBlockByNumber("0x1")` |
| Cadencia | Medida, no asumida: bloque actual `0x24a4b77` (38.423.415) en `2026-09-07T12:38:09Z`. Δt/Δbloques desde el bloque 1 = 20.188.010 s / 38.423.414 bloques ≈ **0,525 s/bloque** (el plan asumía ~600 ms) | dos `eth_getBlockByNumber` |
| **[T-1] Proponente en cabecera** | **Resuelto, mejor de lo esperado.** La cabecera no depende solo de `miner`; trae un objeto `consensusContext: {epoch, view, parentView, proposer}` con el identificador real del proponente BFT. `miner` es redundante/derivado. **C1 y C1b son computables directamente desde la cabecera**, sin necesitar el precompilado para la parte de producción de bloques | Cabecera del bloque `0x24a4b77` |
| **[T-2] Conjunto y pesos de validadores** | **NO resuelto.** El precompilado `ValidatorConfig`/`ValidatorConfigV2` existe (confirmado por `rustdocs.tempo.xyz/tempo_precompiles`), pero la documentación generada (rustdoc) no imprime el valor hexadecimal de la constante de dirección, y la búsqueda de código en el repo `tempoxyz/tempo` en GitHub requiere autenticación no disponible en este entorno (401 en `api.github.com/search/code`). **Sin la dirección exacta no se puede hacer el `eth_call` de prueba.** Queda pendiente: obtener la dirección desde el binario/crate fuente con acceso autenticado a GitHub, o desde soporte de Tempo. Mientras tanto, C1b en Tempo se reporta `no_computable` (a diferencia de C1, que sí es computable vía `consensusContext.proposer`) |
| **[T-3] Campos de comisión del recibo** | **Resuelto.** El recibo trae `feeToken` (dirección del TIP-20 usado como gas) y la transacción trae además `feePayer` distinto de `from` cuando el pagador de la comisión no es el remitente. Costo = `gasUsed × effectiveGasPrice`, denominado en `feeToken`. **A1 no necesita oráculo en Tempo**, confirmado con una transacción real | `eth_getTransactionReceipt` + `eth_getTransactionByHash` sobre `0x4e84fcb…` |
| **Hallazgo no buscado, relevante para D1** | La transacción de ejemplo capturada **ya es una transacción patrocinada real**: `from = 0xc2f5c823…`, `feePayer = 0x385193793…`. Esto contradice la expectativa del plan de que D1 en Tempo es puramente "100% degenerada por construcción" — existe variación real y medible en la sub-métrica de patrocinio de terceros | misma tx |
| **[T-4] Ocupación por carril** | No resuelto en esta pasada. La cabecera trae `mainBlockGeneralGasLimit` y `sharedGasLimit` como campos separados (además de `gasLimit`/`gasUsed` agregados), lo que sugiere que sí hay una partición de carriles a nivel de cabecera — pero falta confirmar cuál de esos carriles corresponde a "pagos" y si el `gasUsed` por carril se puede leer por separado. Requiere una segunda pasada dirigida | Cabecera del bloque `0x24a4b77` |
| **[T-5] Activo de pago** | Mecanismo confirmado, inventario no ejecutado (es tarea de recolección, no de verificación binaria): el topic de `Transfer(address,address,uint256)` estándar aparece en los logs (`0xddf252ad…`), así que `eth_getLogs` filtrando por ese topic es viable para construir el ranking de TIP-20 más usados | Logs de la tx de ejemplo |
| **[T-6] Actualizaciones de red** | No ejecutado en esta pasada (requiere fijar primero la ventana W_H) | — |
| Dos proveedores de nodo | **No cumplido todavía.** Solo se probó `rpc.tempo.xyz`. Falta un segundo proveedor independiente (Dwellir, QuickNode, 1RPC aparecen como candidatos) | — |

---

## Aptos

**Endpoint usado:** `https://api.mainnet.aptoslabs.com/v1`. ✅ (requiere `--ssl-no-revoke` en este entorno por un problema de verificación de revocación de certificados de schannel/Windows, no del servicio)

| Ítem | Resultado | Evidencia |
|---|---|---|
| Ledger vivo | `chain_id=1`, `ledger_version≈7.115B`, `block_height≈1.028B`, timestamp coherente con 2026-09-07 | `GET /v1` |
| Proponente | Confirmado directo en `block_metadata_transaction.proposer`, `epoch`, `round` | `GET /v1/blocks/by_height/1028130000?with_transactions=true` |
| **[A-1] Activo de pago** | No ejecutado el inventario (requiere el Indexer GraphQL, no una muestra de un bloque — el bloque muestreado solo traía swaps de DEX y operaciones de vault, cero transferencias simples de stablecoin). Pendiente para la fase de recolección | Bloque `1028130000` |
| **[A-2] Oráculo APT/USD legible en histórico** | **Hallazgo crítico, no anticipado por el plan.** Pyth (dirección `0x7e783b349d3e89cf5931af376ebeadbfab855b3fa239b7ada8f5a92fbea6b387`) **dejó de dar soporte a Aptos el 26 de agosto de 2026** — 12 días antes de la fecha de este análisis. El contrato y sus recursos (`state::LatestPriceInfo`, `state::StalePriceThreshold`) siguen presentes y son legibles, pero sin actualizador (keeper) activo el precio queda congelado desde esa fecha. **Cualquier ventana W_H que incluya fechas posteriores al 26-ago-2026 tendrá A1 de Aptos con precio de oráculo obsoleto.** Se recomienda: (a) fijar W_H antes de esa fecha si se quiere A1 "computada" en sentido estricto, o (b) marcar A1 de Aptos `parcialmente_derivada` con la fecha de congelamiento documentada explícitamente, tal como prevé el plan para el caso "no se puede leer histórico" — aquí el caso real es peor: se puede leer, pero el valor ya no refleja mercado | `docs.pyth.network/price-feeds/contract-addresses/aptos` + `GET /v1/accounts/0x7e783…/resources` |
| **[A-3] Límite de gas de bloque** | **No resuelto tal como está planteado.** No existe ya un recurso simple "límite de gas de bloque" legible como JSON plano. Lo que hay es `0x1::transaction_limits::TxnLimitsConfig` (V1), que define límites de ejecución/IO **por escalón de stake del validador**, no un techo único de bloque; y `0x1::execution_config::ExecutionConfig`, cuyo campo `config` es un blob BCS binario opaco (`0x0704…`) que requiere deserialización BCS para extraer los límites reales. El modelo de capacidad de Aptos cambió respecto de lo que el plan asumía; H_cfg para Aptos requiere decodificar ese blob, no leer un campo | `GET /v1/accounts/0x1/resource/0x1::transaction_limits::TxnLimitsConfig` y `.../0x1::execution_config::ExecutionConfig` |
| **[A-4] Transacciones patrocinadas** | Mecanismo confirmado por el esquema de la API (tipo de firma `fee_payer_signature`), pero la muestra de un bloque no trajo ningún caso positivo — normal con `n=3`, no es evidencia de ausencia | — |
| **[A-5] Referencia de conciliación** | No ejecutado (depende de A-1) | — |
| Segundo proveedor | No probado todavía | — |

---

## Canton

**Hallazgo estructural más importante de toda la fase 4:** los Scan endpoints "oficiales" de los Super Validators individuales (`sync.global`, `digitalasset.com`, `cumberland.io`, `fivenorth.io`, probados directamente) **rechazan el acceso público** — `403 Forbidden` (AWS ELB) o `403 RBAC: access denied` según el operador. Esto contradice la premisa del plan de que "cualquier Scan de un SV" es accesible por un tercero cualquiera. En la práctica, el acceso público de terceros ocurre a través de **proveedores intermediarios** (análogos a Infura/Alchemy en el mundo EVM) — se localizó y verificó `https://api.cantonnodes.com`, un espejo público de la Scan API operado por un tercero ("Canton Nodes"), que sí respondió con datos reales y coherentes con la fecha actual.

| Ítem | Resultado | Evidencia |
|---|---|---|
| Descubrimiento de SVs | Confirmado vía el espejo: 13 SV listados con sus `publicUrl` (Global-Synchronizer-Foundation, Digital-Asset-1/2, Cumberland-1/2, Proof-Group-1, Orb-1-LP-1, Tradeweb-Markets-1, C7-Technology, MPC-Holding, Five-North-1, Liberty-City-Ventures-1, SV-Nodeops) | `GET /v0/scans` vía `api.cantonnodes.com` |
| **[C-1] Disponibilidad de API de verdicts en mainnet** | **Confirmado, es real y público** (vía el espejo). `POST /v0/events` responde 200 con eventos que incluyen `verdict` (`update_id`, `record_time`, `finalization_time`, `verdict_result` ∈ {ACCEPTED, REJECTED, UNSPECIFIED}, `mediator_group`) según el propio OpenAPI servido en `/docs/openapi.yaml`. El esquema documenta explícitamente que una transacción "wholly private" solo deja el campo `verdict`, sin `update` — exactamente el mecanismo que el plan necesita para contar actividad no visible | `POST /v0/events` + `openapi.yaml` líneas 4470-4640 |
| **[C-2] Retención de verdicts** | **Mejor de lo esperado.** El espejo retiene historial completo desde el génesis del synchronizer global (`record_time = 2024-06-24T21:08:34Z`, evento `DsoBootstrap`) hasta el presente (`2026-09-07T00:00:00Z` confirmado con datos reales). No se observó truncamiento | `POST /v2/updates` con `after_record_time` en ambos extremos |
| **[C-3] Campos de tiempo del verdict** | **Resuelto a favor del plan.** El verdict expone **ambos** instantes: `record_time` (envío) y `finalization_time` (resolución). **B1 en Canton es homogénea con Tempo/Aptos**, no hace falta degradarla a "solo cadencia del sincronizador" como preveía el plan como escenario pesimista | Esquema `EventHistoryVerdict` en `openapi.yaml` |
| **[C-4] Tarifa de tráfico en USD** | **Confirmado, mejor de lo esperado.** El estado del DSO (`GET /v0/dso`) expone `amuletPrice` (USD por Canton Coin, ej. `0.107429` en el momento de la consulta) junto con `transferConfigUsd`, `trafficPrice` y `extraTrafficPrice`. El costo de tráfico está denominado en USD nativamente y es convertible sin oráculo externo — Canton no necesita el equivalente al problema que sí tiene Aptos con Pyth | `GET /v0/dso` |
| **[C-5] Latido para C3** | No ejecutado en esta pasada (requiere fijar W_H y medir periodicidad) | — |
| **[C-6] Stablecoin bajo estándar de token** | No confirmado todavía. La muestra de updates recientes inspeccionada solo mostró plantillas nativas de Amulet (`Amulet`, `LockedAmulet`, `TransferPreapproval`, `ValidatorLicense`, etc.); no apareció ningún template de una stablecoin tipo USDCx en esa muestra pequeña. No es evidencia de ausencia — requiere muestreo dirigido más amplio | `POST /v2/updates` (muestra puntual) |
| **[C-7] Concordancia entre dos SV distintos** | **No se pudo ejecutar tal como está diseñado.** Los Scans de SV individuales bloquean acceso directo (ver arriba), así que no hay dos fuentes *directas* de SV para comparar. La única fuente pública confirmada es el espejo de Canton Nodes. Esto es una limitación estructural a documentar en `limitaciones.md`, no un error de ejecución: el control 7.3 tal como está redactado asume que "dos Scans de SV" son ambos alcanzables por un tercero, y en la práctica no lo son | Intentos directos a `cumberland.io` y `fivenorth.io` |

---

## Consecuencias para continuar

1. **No se avanza a §7/§8 (recolección de 14 días) todavía.** Quedan abiertos: T-2 (dirección del precompilado de validadores en Tempo), T-4 (separación de carriles), segundo proveedor de nodo en Tempo y Aptos, decodificación BCS de `ExecutionConfig` en Aptos, y una fuente independiente real para C-7 en Canton.
2. **Dos hallazgos cambian el diseño del estudio antes de recolectar:**
   - Fijar W_H en Aptos **antes del 26-ago-2026**, o aceptar A1-Aptos como `parcialmente_derivada` con oráculo congelado — decisión que te corresponde a ti, no la tomo unilateralmente.
   - C1b es computable en Tempo y Aptos pero no en Tempo todavía (falta T-2); es la métrica primaria del bloque C según el propio plan (D3), así que bloquea el bloque C completo en Tempo hasta resolverse.
3. **Nada de lo anterior se completó con documentación:** cada fila "confirmado" tiene una llamada real respaldándola; cada fila "no resuelto" queda así, tal como exige la regla de oro del documento.

¿Sigo intentando cerrar T-2 (vía otra ruta de acceso al código fuente de Tempo) y una segunda fuente para C-7, o prefieres que congele la ventana W_H con lo ya confirmado y pase a construir el andamiaje de recolección (§8) dejando estos puntos como limitaciones documentadas desde ya?
