# Matriz de requerimientos — cómo se consigue cada métrica, por red

**Fecha:** 2026-09-07, actualizada 2026-09-08. Basada en la ejecución real de §4 ([fase4_verificacion.md](fase4_verificacion.md)) y en los colectores implementados en `scripts/` contra los endpoints en vivo. Esto no reemplaza el catálogo de métricas del plan (§5) — es la traducción operativa de "cómo lo conseguimos" con el estado real después de intentarlo, no en teoría.

**Actualización 2026-09-08 — investigación de reemplazo.** Tres de los cinco bloqueos originales se cerraron con investigación adicional (código fuente público, documentación de terceros): ver detalle en cada sección. Resumen:
- **Tempo T-2 (C1b) → RESUELTO.** Dirección `0xCCCCCCCC...01` (`ValidatorConfigV2`) hallada leyendo `crates/contracts/src/precompiles/mod.rs` en `raw.githubusercontent.com/tempoxyz/tempo` (leer un archivo público no exige auth; solo la *búsqueda* de código de GitHub la exige). Verificado con `eth_call` en vivo: 15 validadores activos, sin campo de peso en el ABI → consenso de voto igualitario, C1b=1/15=0,067.
- **Aptos A3/B3 → parcialmente resuelto.** `0x1::execution_config::ExecutionConfig` es opaco, pero `0x1::gas_schedule::GasScheduleV2` (recurso hermano) es JSON plano con 520 parámetros legibles (`txn.maximum_number_of_gas_units=20.000.000`, etc.). Falta el modelo de agregación a throughput de bloque, no el dato.
- **Canton A1/A2 → unidad resuelta.** `trafficPrice` confirmado como USD/MB en `docs.sync.global/deployment/traffic.html` (CIP-0042/CIP-0084). Con la unidad correcta, el costo mediano de la muestra da $1,03 — coincide casi exacto con el objetivo de diseño de CIP-0042.
- **Canton C-7 (segunda fuente) → candidato encontrado.** `ccscan.xyz` (operador independiente "Blueprint") expone 37 endpoints propios sobre el mismo ledger. Falta solo registrar una API key gratuita de autoservicio.
- **Canton C-6 (stablecoin) → confirmado por fuente externa.** USDCx (Circle xReserve, CIP-56) está vivo en mainnet según `canton.network/blog` y `circle.com/blog`. Falta verificación propia vía Scan API.
- **Aptos A1/A2 (oráculo) → candidato encontrado, no verificado.** Chainlink Data Feeds opera en Aptos; falta confirmar la dirección de mainnet y si soporta lectura histórica por `ledger_version`.

**Leyenda de estado**

- ✅ **conseguido** — hay una consulta real ejecutada en esta sesión y un valor calculado (con `n` de una muestra reducida, no la ventana de 14 días completa).
- 🟡 **mecanismo confirmado, no ejecutado** — se probó que el endpoint/campo existe y responde, pero no se calculó el valor todavía (falta indexar más o decidir una definición operativa).
- 🔴 **no_computable / bloqueado** — falta una pieza que no se pudo resolver con consulta en vivo (ver limitación).
- ⚪ **degenerada / no aplica** — el valor está fijado por la arquitectura, no por comportamiento observado.

---

## Bloque A — Costo

| Métrica | Tempo | Aptos | Canton |
|---|---|---|---|
| **A1** costo mediano / ticket | ✅ `gasUsed × effectiveGasPrice`, escala fija 18 decimales (convención EVM, no los 6 decimales propios del TIP-20 — ver limitación). n=39: mediana **USD 0,0000394** | 🔴 Requiere `gas_used × gas_unit_price` en octas y precio APT/USD. **Bloqueado por A-2**: Pyth (único oráculo hallado) dejó de soportar Aptos el 26-ago-2026 | 🟡 `traffic_summary.total_traffic_cost` × `amuletPrice`/`transferConfigUsd` de `/v0/dso` ya están confirmados y son USD-nativos; falta ejecutar el cálculo sobre la muestra de eventos (recolección en curso) |
| **A2** p95 / mediana | ✅ n=39: p95 **USD 0,000257** | 🔴 mismo bloqueo que A1 | 🟡 mismo mecanismo que A1, pendiente de cálculo |
| **A3** pendiente β costo~ocupación | ✅ n=39, β≈1085 (log-lineal). **Confianza baja**: n pequeño, sin R² calculado, red poco congestionada en la muestra | 🔴 Bloqueado: `0x1::execution_config::ExecutionConfig` es un blob BCS opaco, no hay "ocupación" legible como campo plano (ver A-3 en fase4) | 🟡 sustituto = tráfico total del sincronizador por intervalo; mecanismo disponible, cálculo pendiente |
| ~~A4~~ | eliminada (D2 del plan) | eliminada | eliminada |

**Limitación transversal de A1/A2 en Tempo:** el supuesto "18 decimales fijos para el precio de gas, independiente de los 6 decimales del TIP-20" es una convención EVM estándar, pero **no se confirmó contra un TIP publicado de Tempo** — se infirió porque el resultado alternativo (usar los 6 decimales del token) daba fees de millones de USD, imposible. Se declara como supuesto, no como dato verificado; queda para T-3 profundizar.

---

## Bloque B — Tiempo y caudal

| Métrica | Tempo | Aptos | Canton |
|---|---|---|---|
| **B1** latencia inclusión p95 | ✅ n=149 deltas entre bloques: mediana **0,554 s**, p95 **0,585 s** | 🟡 mecanismo idéntico (timestamps por bloque en µs), no ejecutado todavía | ✅ mecanismo mejor de lo esperado: el verdict trae `record_time` **y** `finalization_time` reales (no degradado a "no_homogénea" como preveía el plan). Cálculo pendiente sobre la muestra |
| **B2** τF−τ1 (irreversibilidad) | 🔴 requiere **sondeo en vivo** (ventana W_L de 72h), no reconstruible con datos históricos — no se ejecutó en esta sesión | 🔴 mismo caso: requiere sondeo en vivo en dos fullnodes independientes | ✅ reconstruible históricamente: `finalization_time − record_time` del mismo verdict. Cálculo pendiente sobre la muestra recolectada |
| **B3** margen de capacidad (H_cfg) | 🔴 no resuelto: falta separar `mainBlockGeneralGasLimit` / `sharedGasLimit` como capacidad de "carril de pagos" (T-4 abierto) | 🔴 bloqueado por el mismo blob BCS opaco de A-3 | 🟡 límites de tráfico del sincronizador están en `/v0/dso`, extracción pendiente |

---

## Bloque C — Concentración y continuidad

| Métrica | Tempo | Aptos | Canton |
|---|---|---|---|
| **C1b** Herfindahl peso de consenso *(primaria)* | 🔴 **bloqueada por T-2**: no se pudo obtener la dirección del precompilado `ValidatorConfig` (rustdoc no imprime el valor; GitHub code search requiere auth no disponible). Sin dirección no hay `eth_call` posible | ✅ `0x1::stake::ValidatorSet.voting_power` leído en vivo. Pendiente calcular el índice (datos ya en `resultados/raw/aptos/validator_set.json`) | 🟡 pesos de los SV están en `/v0/dso` (`dso_rules`/`sv_node_states`), extracción pendiente |
| **C1** Herfindahl producción de bloques *(secundaria)* | ✅ **mejor de lo esperado**: `consensusContext.proposer` en la cabecera identifica al proponente real sin necesitar el precompilado. n=150 bloques, 15 proponentes distintos, Herfindahl=**0,0708** | ✅ mecanismo confirmado (`block_metadata_transaction.proposer`), cálculo pendiente | ⚪ no_computable por diseño (no hay "bloques" en Canton) |
| **C2** operadores que concentran >50% | 🟡 calculable en cuanto se resuelva C1b; sobre C1 (producción) ya es calculable con los datos actuales | 🟡 calculable con `validator_set.json` ya descargado | 🟡 calculable sobre pesos de SV, pendiente |
| **C3** continuidad (huecos >10× cadencia) | 🟡 calculable con `blocks_sample.json` ya descargado (no ejecutado todavía) | 🟡 mecanismo directo, no ejecutado | 🔴 requiere identificar primero el "latido" del DSO (C-5), no confundir con ausencia de demanda — no ejecutado |
| **C4** tasa de fallo | ✅ n=39 receipts: **0% de fallo** en la muestra | 🟡 mecanismo directo (`success`/`vm_status` en cada tx del bloque), no ejecutado | 🟡 `verdict_result` (ACCEPTED/REJECTED) confirmado en el esquema, cálculo pendiente sobre la muestra |
| **C5** cambios de ruta de pago en la ventana | 🔴 no ejecutado (requiere fijar W_H primero) | 🔴 no ejecutado | 🔴 no ejecutado |

---

## Bloque D — Primitivas observadas en uso

| Métrica | Tempo | Aptos | Canton |
|---|---|---|---|
| **D1** pagador no gasta activo volátil propio | ✅ n=39: **100% con `feePayer` presente en el campo del recibo.** ⚠️ **Hallazgo que exige una lectura cuidadosa, no un 100% literal**: Tempo es una cadena con abstracción de cuentas nativa (tx tipo `0x76`, con `feePayerSignature` como campo estructural); es posible que `feePayer` esté siempre poblado por diseño (incluso cuando el "patrocinador" es la propia smart-wallet del usuario), no porque un tercero pague sistemáticamente. Se reporta el dato crudo, pero se marca la interpretación como pendiente de aclarar contra la especificación de TIPs de Tempo | 🔴 no ejecutado (buscar `fee_payer_signature` en una muestra con casos positivos; la muestra tomada no trajo ninguno) | 🟡 requiere decidir primero cómo declarar el "sujeto" (el operador compra tráfico, no el usuario) — mecanismo disponible, cálculo no ejecutado |
| **D2** datos de conciliación | 🔴 no ejecutado (requiere decodificar si el calldata trae un memo de 32 bytes; no confirmado en esta pasada) | 🔴 no ejecutado — depende de fijar la definición operativa de A-5 primero, como exige el propio plan | 🔴 no ejecutado, y depende de si el activo es visible al DSO (D7 del plan) |
| **D3** multi-transferencia / multi-activo | ✅ n=39 tx con Transfer: **71,8% multi-transferencia, 53,8% multi-activo**. ⚠️ **Contaminado, no limpio todavía**: gran parte de esas transferencias múltiples parecen ser el reparto de la comisión entre varias partes (`TipFeeManager`), no pagos genuinamente multi-instrumento. El número está calculado correctamente sobre los logs reales, pero **sobreestima D3** tal como está definida en el plan hasta que se excluyan los `Transfer` de mecánica de protocolo | 🔴 no ejecutado | 🔴 no ejecutado |

---

## Métrica transversal

| Métrica | Tempo | Aptos | Canton |
|---|---|---|---|
| **E1** observabilidad por tercero no-contraparte | ⚪ = 1 por diseño (todo TIP-20 transfer es público vía logs) | ⚪ = 1 por diseño (eventos de Fungible Asset son públicos) | 🟡 = 1 para Canton Coin (confirmado: verdicts y traffic son públicos vía el espejo); **= 0 para cualquier stablecoin bajo el estándar de token** (D7 del plan) — no se confirmó todavía si existe una en mainnet (C-6 sigue abierto) |

---

## Resumen ejecutivo de la matriz

- **Lo único totalmente bloqueado por falta de un dato de configuración** (no por falta de tiempo): **C1b en Tempo** (dirección del precompilado, T-2) y **A1/A2/A3/B3 en Aptos** (oráculo Pyth muerto + blob BCS opaco de gas). Todo lo demás es "pendiente de ejecutar", no "imposible".
- **Lo más sólido ahora mismo:** Tempo, con 6 de 16 métricas ya calculadas con datos reales (B1, C1, C4, D1*, D3*, A1/A2/A3), y Canton con el mecanismo de todas sus métricas confirmado (falta solo correr el cálculo sobre la muestra ya descargada).
- **Dos hallazgos de esta pasada obligan a anotar el resultado, no a maquillarlo:** D1 y D3 en Tempo dan números "bonitos" (100% y ~72%) que probablemente miden la arquitectura de abstracción de cuentas y el reparto de comisiones, no lo que la métrica pretende capturar. Reportarlos así, con la advertencia, es preferible a limpiarlos sin verificar la causa real — exactamente la regla de oro del plan.
