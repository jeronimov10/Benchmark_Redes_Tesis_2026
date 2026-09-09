# Limitaciones — generado desde metrics.csv

Fecha: 2026-09-09T02:14:20.502771+00:00

Esta es una pasada de verificacion/implementacion con muestras reducidas, no la recoleccion completa de 14 dias (W_H) que especifica el plan. Cada entrada abajo es una metrica que NO se completo con un valor pleno, junto con la razon exacta.

## No computable

- **tempo.C3**: no ejecutado en esta pasada
- **tempo.C5**: requiere fijar W_H primero
- **tempo.D2**: no se decodifico el calldata en busca de memo en esta pasada
- **aptos.A1**: Pyth (unico oraculo APT/USD hallado) dejo de soportar Aptos el 2026-08-26; sin oraculo vivo no hay conversion octas->USD auditable en este momento
- **aptos.A2**: misma razon que A1
- **aptos.B2**: Se intento un sondeo corto (30s, scripts/poll_finality.py) y produjo 17 alturas nuevas pero solo 3 con delta valido, con signos mezclados (-0.09s, +0.03s, -0.56s). Hallazgo metodologico real: el tiempo de bloque de Aptos (~20ms) es mas rapido que el round-trip HTTP hacia la API publica, asi que un sondeo secuencial simple no puede resolver B2 aqui -- se necesitaria un nodo de baja latencia o streaming, no polling HTTP estandar.
- **aptos.A3**: NO es la elasticidad todavia -- 20.000.000 (txn.maximum_number_of_gas_units, de 0x1::gas_schedule::GasScheduleV2) es un techo de capacidad por transaccion, no la pendiente ln(costo)~ocupacion que pide A3. El dato de capacidad ya no esta bloqueado (ver B3), pero A3 en si requiere costo real por tx (bloqueado por el oraculo, ver A1/A2) regresado contra alguna nocion de ocupacion -- sigue sin poder calcularse hasta resolver A1/A2.
- **aptos.B3**: ya no bloqueado por falta de dato (ver A3), sino por falta de modelo: falta combinar GasScheduleV2 + TxnLimitsConfig + tiempo de bloque en un H_cfg comparable a los 48 TPS de referencia
- **aptos.C5**: requiere fijar W_H primero
- **aptos.D2**: depende de fijar primero la definicion operativa de A-5, como exige el propio plan
- **aptos.D3**: no ejecutado en esta pasada
- **canton.A3**: no ejecutado: requiere bucketizar traffic_summary por intervalo, pendiente
- **canton.B3**: limites de trafico del sincronizador no extraidos todavia de /v0/dso
- **canton.C1**: degenerada por diseno: Canton no tiene bloques
- **canton.C1b**: pesos de SV estan en /v0/dso (dso_rules/sv_node_states) pero no se extrajeron en esta pasada
- **canton.C2**: depende de C1b
- **canton.C3**: requiere identificar primero el latido del DSO (C-5), no ejecutado
- **canton.C5**: requiere fijar W_H primero
- **canton.D1**: requiere decidir primero como declarar el sujeto (el operador compra trafico, no el usuario), no ejecutado
- **canton.D2**: no ejecutado; depende de si el activo es visible al DSO
- **canton.D3**: no ejecutado en esta pasada

## Parcialmente derivada (valor obtenido, con supuesto o advertencia sin verificar)

- **tempo.A1** = 2.01522e-05: muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap; supuesto 18 decimales de precio de gas no confirmado contra TIP publicado
- **tempo.A2** = 0.0001785474: muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap
- **tempo.A3** = 2019.3640331462352: muestra reducida de verificacion, no la ventana W_H de 14 dias del plan; sin bootstrap; n muy pequeno para una regresion confiable, sin R2
- **tempo.B2** = 0.630202054977417: Mecanismo de sondeo en vivo (scripts/poll_finality.py) verificado y corrido 30s como demostracion (no las 72h de W_L que exige el plan). p95=0.81s. Confirma la advertencia del plan: tau_F es sub-segundo en Tempo, no discrimina frente al umbral t=60s/w=604800s -- el eje de irreversibilidad no separa a esta red en esta muestra.
- **tempo.B3** = 556.8040922656879: H_cfg = (gasLimit=500000000 / gasUsed_mediana=33587) / cadencia_mediana=0.557s, sobre 48 TPS de referencia. No separa carril de pagos de ocupacion global (T-4 sigue abierto) -- es capacidad agregada del bloque completo, un limite superior optimista.
- **tempo.D3** = 0.7681818181818182: probablemente sobreestimada: incluye Transfer logs del reparto de comision (TipFeeManager), no solo pagos multi-instrumento genuinos
- **canton.A1** = 0.8952600000000001: Unidad CONFIRMADA via docs.sync.global (Synchronizer Traffic Fees, CIP-0042/CIP-0084): trafficPrice=60 USD/MB, total_traffic_cost en bytes. Coincide con el objetivo de diseno de CIP-0042 (~1 USD por transferencia estandar de CC). Sigue parcial porque la ventana (~189s) cae en un burst periodico de ValidatorLicense_ReportActive, no en trafico de pagos tipico.
- **canton.A2** = 2.75022: misma confirmacion de unidad que A1; misma limitacion de ventana no representativa
- **canton.E1** = 0: USDCx esta confirmado vivo en mainnet por fuente externa (canton.network/blog, circle.com/blog, CIP-56), pero la busqueda propia de template_id tipo Holding/Token en 10.400 eventos reales sobre DOS ventanas distintas (una de burst de medianoche, otra de 8 min en horario habil) no encontro ninguno -- todos los templates visibles son nativos de Amulet/Splice. Esto es evidencia mas fuerte que antes de que, si USDCx circula, su actividad visible es muy escasa frente a la nativa, o bien nunca deja `update` visible (solo verdict) -- consistente con D7 del plan: si es privada, E1=0 para ese activo es precisamente el resultado esperado, no una falla de busqueda.
