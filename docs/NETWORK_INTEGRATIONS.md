# Integraciones por red

Fuente única de qué métrica es en vivo y cuál solo existe en la línea base. La tabla vive en código (`backend/app/services/network/registry.py`) y `GET /api/redes` la expone. Verificación en vivo hecha el 2026-10-19 contra las redes reales.

## Inventario

| Red | Responsable | Fuente | Estado inicial en el repo | Estado final | Verificación en vivo |
|---|---|---|---|---|---|
| Polygon PoS | Dilan | JSON-RPC (`polygon.publicnode.com`) | Solo perfil medido (`perfiles.json`); sin colector | Colector EVM + perfil | OK: bloques, pagos USDC, precio Chainlink MATIC/USD |
| Celo | Dilan | JSON-RPC `forno.celo.org` | Solo perfil medido | Colector EVM + perfil | OK |
| Arbitrum One | Dilan | JSON-RPC `arb1.arbitrum.io/rpc` | Solo perfil medido | Colector EVM + perfil | OK |
| Tempo | Jerónimo | JSON-RPC `rpc.tempo.xyz` | Scripts por lotes (muestra de minutos, sep. 2026) | Colector continuo + finalidad en vivo + perfil | OK |
| Aptos | Jerónimo | REST `api.mainnet.aptoslabs.com/v1` | Scripts por lotes | Colector por muestreo + perfil | OK |
| Canton | Jerónimo | Scan API `api.cantonnodes.com` | Scripts por lotes (cursor fijo en sep. 2026) | Colector con cursor persistido + perfil | OK |

Los seis colectores respondieron en la verificación y las métricas "vivas" de la tabla de abajo llegaron a `valida`. Lo verificado con **respuestas simuladas** (no en vivo): ramas de error (timeouts, 429, JSON malformado), `datos_insuficientes`, y el ciclo de vida de la recalibración en las pruebas. Además se ejecutó una recalibración real corta (50 bloques de Tempo, 20 de Aptos, 2 páginas de Canton) que terminó en `completado` y actualizó los perfiles base.

## Métricas en vivo vs. solo base

| Métrica | Tempo | Aptos | Canton | Polygon / Celo / Arbitrum |
|---|---|---|---|---|
| A1 costo mediano (USD) | vivo (token de comisión USD) | vivo (APT × Pyth on-chain, congelado) | vivo (bytes × `extraTrafficPrice` del DSO) | vivo (gas × Chainlink, transferencias USDC) |
| A2 p95/mediana | vivo | vivo | vivo | vivo |
| A3 pendiente costo~ocupación | vivo | vivo | vivo (tráfico por cubeta de 10 s) | base (la tesis exige ajuste con R² suficiente) |
| A4 anclaje L1 | n/a | n/a | n/a | base (requiere rastreador de anclaje verificado) |
| B1 latencia p95 | vivo | vivo | vivo (veredicto) | vivo |
| B2 finalidad | vivo continuo (ventana 72 h; mientras tanto base) | base: imposible por HTTP | vivo (mediana del veredicto) | base (anclaje en Ethereum) |
| B2b | n/a | n/a | n/a | base |
| B3 capacidad | vivo (config + mediana de gas) | vivo (`ExecutionConfig` BCS decodificado, 79/79 bytes) | vivo, cota inferior (asignación gratuita por miembro) | base (caudal sostenido 1 h, 90 d) |
| C1/C2 concentración | vivo (precompilado `ValidatorConfigV2`, voto igualitario) | vivo (`ValidatorSet`) | vivo (`svRewardWeight`) | vivo (productores en muestra) |
| C3 continuidad | vivo (ventana 14 d) | base: el muestreo no detecta huecos | vivo (latido `ReportActive`, 14 d) | vivo si la cobertura lo permite (Arbitrum probablemente no) |
| C4 tasa de fallo | vivo | vivo | vivo (veredictos rechazados) | vivo |
| C5 cambios | vivo (`tempo_forkSchedule`, 14 d) | base | vivo (choices DSO no rutinarias, 14 d) | vivo (ranura de implementación del proxy de USDC, 14 d) |
| D1 independiente del token nativo | vivo (feePayer) | vivo (fee payer) | base (declarado no aplica) | vivo (EIP-3009, EIP-7702, ERC-4337, feeCurrency) |
| D2 referencia de conciliación | vivo (evento `TransferWithMemo`) | base: definición A-5 sin fijar | vivo (`meta`) | base (definición estricta de la tesis no reproducible) |
| D3 multi-transferencia | vivo | vivo (n pequeño) | vivo | base |

"Vivo" significa que el cálculo se hace sobre una ventana móvil y entra al perfil solo si `n` alcanza el mínimo; si no, se muestra `insuficiente` y se usa la base. En la última verificación quedaron `valida`: Polygon/Celo/Arbitrum 7 de 9; Tempo 12 de 14; Aptos 10 de 10; Canton 11 de 13 (lo demás completaba ventana).

## Identificadores verificados en vivo

Ninguna dirección se acepta sin comprobación (regla de oro):

- USDC de cada red EVM: `symbol()=="USDC"`, `decimals()==6` y código desplegado.
- Feeds Chainlink: `description()` debe coincidir con el par esperado; `decimals()`; `updatedAt` < 1 h. Polygon usa el feed `MATIC / USD` (la migración MATIC→POL es 1:1).
- Pyth Aptos: el `price_identifier` devuelto debe coincidir con el feed ID resuelto por símbolo exacto en Hermes. La tabla está congelada desde 2026-08-26 y se marca `precio_congelado`.
- Topics y selectores (Transfer, TransferWithMemo, EIP-3009) se calculan con keccak256, no se copian.
- Layout BCS de `ExecutionConfig`: se exige consumir todos los bytes.

## Diferencias metodológicas a tener presentes

- Tempo/Aptos/Canton en base usan `sigma=0`; las métricas en vivo traen error estándar por bootstrap.
- **Canton B2**: en la línea base (`metrics.csv`) es el p95 del veredicto (igual a B1); en vivo se usa la **mediana** que define el plan para B2. Es una discrepancia del benchmark original, no de este sistema.
- Muestreo de Aptos (6 bloques por ciclo) y Arbitrum (40): ver [DATA_PIPELINE.md](DATA_PIPELINE.md).
- Los RPC públicos son inestables (Polygon cambió de proveedor durante la verificación). Configura `RPC_*`.
