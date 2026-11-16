# Informe del banco de usuarios simulados

Generado automaticamente a partir de simulacion.db. Los resultados se leen por perfil; nunca como porcentaje de la poblacion. Los rangos de los perfiles 4 a 12 son supuestos de diseno. Un mal ajuste es evidencia para discutir, no un defecto demostrado.

## Notas de la corrida

- base: metricas comunes = 13 (A1, A2, B1, B2, B3, C1, C2, C3, C4, C5, D1, D2, D3)
- vivo: 60 de 74 metricas vivas esperadas
- vivo: metricas comunes = 13 (A1, A2, B1, B2, B3, C1, C2, C3, C4, C5, D1, D2, D3)

## P1. Cobertura

| fuente | perfil | n | banda 1 modal | cuota | semiancho | cert. baja | empates |
|---|---|---|---|---|---|---|---|
| base | 1 Remesa familiar | 50 | polygon | 1.0 | 0.036 | 0.0 | 0.0 |
| base | 2 Tendero con QR | 200 | polygon+tempo | 0.86 | 0.048 | 0.0 | 0.955 |
| base | 3 Tesoreria de alto valor | 50 | tempo | 1.0 | 0.036 | 0.0 | 0.0 |
| base | 4 Microremesa | 50 | polygon | 1.0 | 0.036 | 0.02 | 0.0 |
| base | 5 Freelancer | 50 | polygon | 1.0 | 0.036 | 1.0 | 0.0 |
| base | 6 E-commerce | 50 | polygon+tempo | 1.0 | 0.036 | 0.62 | 1.0 |
| base | 7 Nomina de pyme | 50 | polygon+tempo | 1.0 | 0.036 | 1.0 | 1.0 |
| base | 8 Proveedor B2B | 50 | tempo | 1.0 | 0.036 | 0.0 | 0.0 |
| base | 9 Importador | 50 | polygon+tempo | 1.0 | 0.036 | 1.0 | 1.0 |
| base | 10 Remesa urgente | 50 | polygon | 1.0 | 0.036 | 1.0 | 0.0 |
| base | 11 Liquidacion urgente | 50 | tempo | 1.0 | 0.036 | 0.76 | 0.0 |
| base | 12 Micropago de transporte | 400 | tempo | 0.507 | 0.049 | 1.0 | 0.492 |
| vivo | 1 Remesa familiar | 50 | polygon | 1.0 | 0.036 | 0.0 | 0.0 |
| vivo | 2 Tendero con QR | 350 | polygon | 0.663 | 0.049 | 0.0 | 0.337 |
| vivo | 3 Tesoreria de alto valor | 50 | tempo | 1.0 | 0.036 | 0.0 | 0.0 |
| vivo | 4 Microremesa | 50 | polygon | 1.0 | 0.036 | 0.02 | 0.0 |
| vivo | 5 Freelancer | 50 | polygon | 1.0 | 0.036 | 1.0 | 0.0 |
| vivo | 6 E-commerce | 50 | polygon+tempo | 1.0 | 0.036 | 0.62 | 1.0 |
| vivo | 7 Nomina de pyme | 50 | polygon+tempo | 1.0 | 0.036 | 1.0 | 1.0 |
| vivo | 8 Proveedor B2B | 50 | tempo | 1.0 | 0.036 | 0.0 | 0.0 |
| vivo | 9 Importador | 50 | polygon+tempo | 1.0 | 0.036 | 1.0 | 1.0 |
| vivo | 10 Remesa urgente | 400 | canton+polygon+tempo | 0.487 | 0.049 | 1.0 | 0.66 |
| vivo | 11 Liquidacion urgente | 50 | tempo | 1.0 | 0.036 | 0.76 | 0.0 |
| vivo | 12 Micropago de transporte | 400 | polygon+tempo | 0.61 | 0.048 | 1.0 | 0.61 |

- ALERTA P1: perfil 5 (Freelancer, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 6 (E-commerce, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 7 (Nomina de pyme, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 9 (Importador, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 10 (Remesa urgente, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 11 (Liquidacion urgente, base): certidumbre baja en la mayoria
- ALERTA P1: perfil 12 (Micropago de transporte, base): llego al tope de 400 usuarios
- ALERTA P1: perfil 5 (Freelancer, vivo): certidumbre baja en la mayoria
- ALERTA P1: perfil 6 (E-commerce, vivo): certidumbre baja en la mayoria
- ALERTA P1: perfil 7 (Nomina de pyme, vivo): certidumbre baja en la mayoria
- ALERTA P1: perfil 9 (Importador, vivo): certidumbre baja en la mayoria
- ALERTA P1: perfil 10 (Remesa urgente, vivo): llego al tope de 400 usuarios
- ALERTA P1: perfil 11 (Liquidacion urgente, vivo): certidumbre baja en la mayoria
- ALERTA P1: perfil 12 (Micropago de transporte, vivo): llego al tope de 400 usuarios


## P2. Ajuste a la necesidad

| fuente | perfil | lectura | cumple | parcial | brecha | sin_solucion | no_evaluable |
|---|---|---|---|---|---|---|---|
| base | 1 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 1 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 2 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 2 | requisito | 0.0 | 0.955 | 0.045 | 0.0 | 0.0 |
| base | 3 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 3 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 4 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 4 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 5 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 5 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 6 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 6 | requisito | 0.06 | 0.94 | 0.0 | 0.0 | 0.0 |
| base | 7 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 7 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 8 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 8 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 9 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 9 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 10 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 10 | requisito | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 |
| base | 11 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 11 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| base | 12 | preferencia | 0.87 | 0.13 | 0.0 | 0.0 | 0.0 |
| base | 12 | requisito | 0.507 | 0.492 | 0.0 | 0.0 | 0.0 |
| vivo | 1 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 1 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 2 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 2 | requisito | 0.0 | 0.337 | 0.663 | 0.0 | 0.0 |
| vivo | 3 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 3 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 4 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 4 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 5 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 5 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 6 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 6 | requisito | 0.14 | 0.86 | 0.0 | 0.0 | 0.0 |
| vivo | 7 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 7 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 8 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 8 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 9 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 9 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 10 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 10 | requisito | 0.0 | 0.66 | 0.34 | 0.0 | 0.0 |
| vivo | 11 | preferencia | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 11 | requisito | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vivo | 12 | preferencia | 0.72 | 0.28 | 0.0 | 0.0 | 0.0 |
| vivo | 12 | requisito | 0.39 | 0.61 | 0.0 | 0.0 | 0.0 |

- ALERTA P2: perfil 2 (Tendero con QR, base): brecha preferencia 0.0, requisito 0.045
- ALERTA P2: perfil 10 (Remesa urgente, base): brecha preferencia 0.0, requisito 1.0
- ALERTA P2: perfil 2 (Tendero con QR, vivo): brecha preferencia 0.0, requisito 0.663
- ALERTA P2: perfil 10 (Remesa urgente, vivo): brecha preferencia 0.0, requisito 0.34

## P3. Contrafactuales de medicion

Cuota de usuarios del panel cuya banda 1 cambia frente a la referencia.

| fuente | escenario | perfil | n | cuota de cambio |
|---|---|---|---|---|
| base | metricas_comunes | 1 | 10 | 1.0 |
| base | metricas_comunes | 2 | 10 | 1.0 |
| base | metricas_comunes | 3 | 10 | 0.0 |
| base | metricas_comunes | 4 | 10 | 1.0 |
| base | metricas_comunes | 5 | 10 | 1.0 |
| base | metricas_comunes | 6 | 10 | 1.0 |
| base | metricas_comunes | 7 | 10 | 1.0 |
| base | metricas_comunes | 8 | 10 | 0.0 |
| base | metricas_comunes | 9 | 10 | 1.0 |
| base | metricas_comunes | 10 | 10 | 1.0 |
| base | metricas_comunes | 11 | 10 | 0.0 |
| base | metricas_comunes | 12 | 10 | 0.4 |
| base | sin_sigma | 1 | 10 | 0.0 |
| base | sin_sigma | 2 | 10 | 0.2 |
| base | sin_sigma | 3 | 10 | 0.0 |
| base | sin_sigma | 4 | 10 | 0.0 |
| base | sin_sigma | 5 | 10 | 0.0 |
| base | sin_sigma | 6 | 10 | 0.0 |
| base | sin_sigma | 7 | 10 | 0.0 |
| base | sin_sigma | 8 | 10 | 0.0 |
| base | sin_sigma | 9 | 10 | 0.0 |
| base | sin_sigma | 10 | 10 | 0.0 |
| base | sin_sigma | 11 | 10 | 0.0 |
| base | sin_sigma | 12 | 10 | 0.0 |
| base | solo_pca | 1 | 10 | 0.0 |
| base | solo_pca | 2 | 10 | 0.9 |
| base | solo_pca | 3 | 10 | 1.0 |
| base | solo_pca | 4 | 10 | 0.0 |
| base | solo_pca | 5 | 10 | 0.0 |
| base | solo_pca | 6 | 10 | 1.0 |
| base | solo_pca | 7 | 10 | 1.0 |
| base | solo_pca | 8 | 10 | 1.0 |
| base | solo_pca | 9 | 10 | 1.0 |
| base | solo_pca | 10 | 10 | 0.0 |
| base | solo_pca | 11 | 10 | 1.0 |
| base | solo_pca | 12 | 10 | 1.0 |
| base | solo_tac | 1 | 10 | 1.0 |
| base | solo_tac | 2 | 10 | 1.0 |
| base | solo_tac | 3 | 10 | 0.0 |
| base | solo_tac | 4 | 10 | 1.0 |
| base | solo_tac | 5 | 10 | 1.0 |
| base | solo_tac | 6 | 10 | 1.0 |
| base | solo_tac | 7 | 10 | 1.0 |
| base | solo_tac | 8 | 10 | 0.0 |
| base | solo_tac | 9 | 10 | 1.0 |
| base | solo_tac | 10 | 10 | 1.0 |
| base | solo_tac | 11 | 10 | 0.0 |
| base | solo_tac | 12 | 10 | 0.4 |
| vivo | metricas_comunes | 1 | 10 | 1.0 |
| vivo | metricas_comunes | 2 | 10 | 1.0 |
| vivo | metricas_comunes | 3 | 10 | 0.0 |
| vivo | metricas_comunes | 4 | 10 | 1.0 |
| vivo | metricas_comunes | 5 | 10 | 1.0 |
| vivo | metricas_comunes | 6 | 10 | 0.6 |
| vivo | metricas_comunes | 7 | 10 | 1.0 |
| vivo | metricas_comunes | 8 | 10 | 0.0 |
| vivo | metricas_comunes | 9 | 10 | 1.0 |
| vivo | metricas_comunes | 10 | 10 | 1.0 |
| vivo | metricas_comunes | 11 | 10 | 0.0 |
| vivo | metricas_comunes | 12 | 10 | 0.9 |
| vivo | sin_sigma | 1 | 10 | 0.0 |
| vivo | sin_sigma | 2 | 10 | 0.0 |
| vivo | sin_sigma | 3 | 10 | 0.0 |
| vivo | sin_sigma | 4 | 10 | 0.0 |
| vivo | sin_sigma | 5 | 10 | 0.0 |
| vivo | sin_sigma | 6 | 10 | 0.0 |
| vivo | sin_sigma | 7 | 10 | 0.0 |
| vivo | sin_sigma | 8 | 10 | 0.0 |
| vivo | sin_sigma | 9 | 10 | 0.0 |
| vivo | sin_sigma | 10 | 10 | 0.0 |
| vivo | sin_sigma | 11 | 10 | 0.0 |
| vivo | sin_sigma | 12 | 10 | 0.0 |
| vivo | solo_pca | 1 | 10 | 0.0 |
| vivo | solo_pca | 2 | 10 | 0.2 |
| vivo | solo_pca | 3 | 10 | 1.0 |
| vivo | solo_pca | 4 | 10 | 0.0 |
| vivo | solo_pca | 5 | 10 | 0.0 |
| vivo | solo_pca | 6 | 10 | 1.0 |
| vivo | solo_pca | 7 | 10 | 1.0 |
| vivo | solo_pca | 8 | 10 | 1.0 |
| vivo | solo_pca | 9 | 10 | 1.0 |
| vivo | solo_pca | 10 | 10 | 0.5 |
| vivo | solo_pca | 11 | 10 | 1.0 |
| vivo | solo_pca | 12 | 10 | 1.0 |
| vivo | solo_tac | 1 | 10 | 1.0 |
| vivo | solo_tac | 2 | 10 | 1.0 |
| vivo | solo_tac | 3 | 10 | 0.0 |
| vivo | solo_tac | 4 | 10 | 1.0 |
| vivo | solo_tac | 5 | 10 | 1.0 |
| vivo | solo_tac | 6 | 10 | 1.0 |
| vivo | solo_tac | 7 | 10 | 1.0 |
| vivo | solo_tac | 8 | 10 | 0.0 |
| vivo | solo_tac | 9 | 10 | 1.0 |
| vivo | solo_tac | 10 | 10 | 1.0 |
| vivo | solo_tac | 11 | 10 | 0.0 |
| vivo | solo_tac | 12 | 10 | 0.9 |

- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 1 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 2 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 4 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 5 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 6 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 7 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 9 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 10 (base): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 1 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 2 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 4 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 5 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 6 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 7 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 9 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 10 (vivo): la comparacion dependeria de la cobertura de metricas.
- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil 12 (vivo): la comparacion dependeria de la cobertura de metricas.
- Aptos en sombra, perfil 1 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0527.
- Aptos en sombra, perfil 2 (base): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0172.
- Aptos en sombra, perfil 3 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0512.
- Aptos en sombra, perfil 4 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0475.
- Aptos en sombra, perfil 5 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0247.
- Aptos en sombra, perfil 6 (base): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.025.
- Aptos en sombra, perfil 7 (base): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0164.
- Aptos en sombra, perfil 8 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0457.
- Aptos en sombra, perfil 9 (base): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.015.
- Aptos en sombra, perfil 10 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0155.
- Aptos en sombra, perfil 11 (base): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0295.
- Aptos en sombra, perfil 12 (base): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0468.
- Aptos en sombra, perfil 1 (vivo): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0623.
- Aptos en sombra, perfil 2 (vivo): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.019.
- Aptos en sombra, perfil 3 (vivo): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0223.
- Aptos en sombra, perfil 4 (vivo): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.054.
- Aptos en sombra, perfil 5 (vivo): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.016.
- Aptos en sombra, perfil 6 (vivo): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0367.
- Aptos en sombra, perfil 7 (vivo): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0432.
- Aptos en sombra, perfil 8 (vivo): supera a la mejor otra red en 0.0 de los usuarios; diferencia media de puntaje central 0.0169.
- Aptos en sombra, perfil 9 (vivo): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0474.
- Aptos en sombra, perfil 10 (vivo): supera a la mejor otra red en 0.3 de los usuarios; diferencia media de puntaje central 0.003.
- Aptos en sombra, perfil 11 (vivo): supera a la mejor otra red en 0.3 de los usuarios; diferencia media de puntaje central 0.0012.
- Aptos en sombra, perfil 12 (vivo): supera a la mejor otra red en 1.0 de los usuarios; diferencia media de puntaje central -0.0724.

## P4. Caida de una red

| fuente | escenario | perfil | cuota de cambio | perdida de puntaje | empeora ajuste (req.) |
|---|---|---|---|---|---|
| base | sin_aptos | 1 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 2 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 3 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 4 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 5 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 6 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 7 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 8 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 9 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 10 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 11 | 0.0 | 0.0 | 0 |
| base | sin_aptos | 12 | 0.0 | 0.0 | 0 |
| base | sin_arbitrum | 1 | 0.0 | 0.0 | 0 |
| base | sin_arbitrum | 2 | 0.2 | 0.0 | 2 |
| base | sin_arbitrum | 3 | 0.0 | 0.0002 | 0 |
| base | sin_arbitrum | 4 | 0.0 | 0.0 | 0 |
| base | sin_arbitrum | 5 | 0.0 | -0.0007 | 0 |
| base | sin_arbitrum | 6 | 0.0 | 0.0 | 0 |
| base | sin_arbitrum | 7 | 0.0 | -0.0003 | 0 |
| base | sin_arbitrum | 8 | 0.0 | 0.0005 | 0 |
| base | sin_arbitrum | 9 | 0.0 | -0.0001 | 0 |
| base | sin_arbitrum | 10 | 0.0 | -0.0001 | 0 |
| base | sin_arbitrum | 11 | 0.0 | -0.0001 | 0 |
| base | sin_arbitrum | 12 | 0.1 | 0.0003 | 0 |
| base | sin_canton | 1 | 0.0 | 0.0 | 0 |
| base | sin_canton | 2 | 0.2 | 0.0 | 2 |
| base | sin_canton | 3 | 0.0 | -0.0007 | 0 |
| base | sin_canton | 4 | 0.0 | -0.0002 | 0 |
| base | sin_canton | 5 | 0.0 | -0.0003 | 0 |
| base | sin_canton | 6 | 0.0 | 0.0 | 0 |
| base | sin_canton | 7 | 0.0 | -0.0007 | 0 |
| base | sin_canton | 8 | 0.0 | -0.0001 | 0 |
| base | sin_canton | 9 | 0.0 | -0.0001 | 0 |
| base | sin_canton | 10 | 0.0 | 0.0 | 0 |
| base | sin_canton | 11 | 0.0 | -0.0011 | 0 |
| base | sin_canton | 12 | 0.0 | 0.0003 | 0 |
| base | sin_celo | 1 | 0.0 | 0.0 | 0 |
| base | sin_celo | 2 | 0.2 | 0.0 | 2 |
| base | sin_celo | 3 | 0.0 | 0.0002 | 0 |
| base | sin_celo | 4 | 0.0 | 0.0 | 0 |
| base | sin_celo | 5 | 0.0 | -0.0007 | 0 |
| base | sin_celo | 6 | 0.0 | 0.0 | 0 |
| base | sin_celo | 7 | 0.0 | -0.0003 | 0 |
| base | sin_celo | 8 | 0.0 | 0.0005 | 0 |
| base | sin_celo | 9 | 0.0 | -0.0001 | 0 |
| base | sin_celo | 10 | 0.0 | -0.0001 | 0 |
| base | sin_celo | 11 | 0.0 | -0.0001 | 0 |
| base | sin_celo | 12 | 0.1 | 0.0003 | 0 |
| base | sin_polygon | 1 | 1.0 | 0.0826 | 0 |
| base | sin_polygon | 2 | 1.0 | 0.0424 | 0 |
| base | sin_polygon | 3 | 0.0 | 0.0002 | 0 |
| base | sin_polygon | 4 | 1.0 | 0.0913 | 0 |
| base | sin_polygon | 5 | 1.0 | 0.0533 | 0 |
| base | sin_polygon | 6 | 1.0 | 0.0198 | 0 |
| base | sin_polygon | 7 | 1.0 | -0.0003 | 0 |
| base | sin_polygon | 8 | 0.0 | 0.0005 | 0 |
| base | sin_polygon | 9 | 1.0 | 0.0022 | 0 |
| base | sin_polygon | 10 | 1.0 | 0.0503 | 0 |
| base | sin_polygon | 11 | 0.0 | -0.0001 | 0 |
| base | sin_polygon | 12 | 0.4 | 0.0003 | 0 |
| base | sin_tempo | 1 | 0.0 | 0.0 | 0 |
| base | sin_tempo | 2 | 0.9 | 0.0 | 9 |
| base | sin_tempo | 3 | 1.0 | 0.1541 | 4 |
| base | sin_tempo | 4 | 0.0 | -0.0002 | 0 |
| base | sin_tempo | 5 | 0.0 | -0.0003 | 0 |
| base | sin_tempo | 6 | 1.0 | 0.0 | 10 |
| base | sin_tempo | 7 | 1.0 | 0.029 | 0 |
| base | sin_tempo | 8 | 1.0 | 0.1442 | 0 |
| base | sin_tempo | 9 | 1.0 | 0.0 | 0 |
| base | sin_tempo | 10 | 0.0 | 0.0 | 0 |
| base | sin_tempo | 11 | 1.0 | 0.1143 | 10 |
| base | sin_tempo | 12 | 1.0 | 0.0335 | 10 |
| vivo | sin_aptos | 1 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 2 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 3 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 4 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 5 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 6 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 7 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 8 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 9 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 10 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 11 | 0.0 | 0.0 | 0 |
| vivo | sin_aptos | 12 | 0.0 | 0.0 | 0 |
| vivo | sin_arbitrum | 1 | 0.0 | -0.0004 | 0 |
| vivo | sin_arbitrum | 2 | 0.0 | 0.0 | 0 |
| vivo | sin_arbitrum | 3 | 0.0 | 0.0004 | 0 |
| vivo | sin_arbitrum | 4 | 0.0 | 0.0 | 0 |
| vivo | sin_arbitrum | 5 | 0.0 | 0.0005 | 0 |
| vivo | sin_arbitrum | 6 | 0.0 | 0.0001 | 0 |
| vivo | sin_arbitrum | 7 | 0.0 | -0.0004 | 0 |
| vivo | sin_arbitrum | 8 | 0.0 | 0.0005 | 0 |
| vivo | sin_arbitrum | 9 | 0.0 | -0.0003 | 0 |
| vivo | sin_arbitrum | 10 | 0.1 | 0.0 | 0 |
| vivo | sin_arbitrum | 11 | 0.0 | -0.0004 | 0 |
| vivo | sin_arbitrum | 12 | 0.0 | 0.0 | 0 |
| vivo | sin_canton | 1 | 0.0 | 0.0003 | 0 |
| vivo | sin_canton | 2 | 0.0 | 0.0002 | 0 |
| vivo | sin_canton | 3 | 0.0 | -0.0007 | 0 |
| vivo | sin_canton | 4 | 0.0 | 0.0003 | 0 |
| vivo | sin_canton | 5 | 0.0 | 0.0005 | 0 |
| vivo | sin_canton | 6 | 0.0 | 0.0007 | 0 |
| vivo | sin_canton | 7 | 0.0 | -0.0008 | 0 |
| vivo | sin_canton | 8 | 0.0 | -0.0002 | 0 |
| vivo | sin_canton | 9 | 0.0 | -0.0003 | 0 |
| vivo | sin_canton | 10 | 0.6 | 0.0004 | 0 |
| vivo | sin_canton | 11 | 0.0 | -0.0015 | 0 |
| vivo | sin_canton | 12 | 0.0 | 0.0 | 0 |
| vivo | sin_celo | 1 | 0.0 | -0.0004 | 0 |
| vivo | sin_celo | 2 | 0.0 | 0.0 | 0 |
| vivo | sin_celo | 3 | 0.0 | 0.0004 | 0 |
| vivo | sin_celo | 4 | 0.0 | 0.0 | 0 |
| vivo | sin_celo | 5 | 0.0 | 0.0005 | 0 |
| vivo | sin_celo | 6 | 0.0 | 0.0001 | 0 |
| vivo | sin_celo | 7 | 0.0 | -0.0004 | 0 |
| vivo | sin_celo | 8 | 0.0 | 0.0005 | 0 |
| vivo | sin_celo | 9 | 0.0 | -0.0003 | 0 |
| vivo | sin_celo | 10 | 0.1 | 0.0 | 0 |
| vivo | sin_celo | 11 | 0.0 | -0.0004 | 0 |
| vivo | sin_celo | 12 | 0.0 | 0.0 | 0 |
| vivo | sin_polygon | 1 | 1.0 | 0.1077 | 0 |
| vivo | sin_polygon | 2 | 1.0 | 0.067 | 0 |
| vivo | sin_polygon | 3 | 0.0 | 0.0004 | 0 |
| vivo | sin_polygon | 4 | 1.0 | 0.129 | 0 |
| vivo | sin_polygon | 5 | 1.0 | 0.0623 | 0 |
| vivo | sin_polygon | 6 | 1.0 | 0.0356 | 0 |
| vivo | sin_polygon | 7 | 1.0 | -0.0004 | 0 |
| vivo | sin_polygon | 8 | 0.0 | 0.0005 | 0 |
| vivo | sin_polygon | 9 | 1.0 | -0.0003 | 0 |
| vivo | sin_polygon | 10 | 1.0 | 0.0677 | 0 |
| vivo | sin_polygon | 11 | 0.0 | -0.0004 | 0 |
| vivo | sin_polygon | 12 | 0.9 | 0.0 | 0 |
| vivo | sin_tempo | 1 | 0.0 | 0.0003 | 0 |
| vivo | sin_tempo | 2 | 0.2 | 0.0002 | 2 |
| vivo | sin_tempo | 3 | 1.0 | 0.2354 | 1 |
| vivo | sin_tempo | 4 | 0.0 | 0.0003 | 0 |
| vivo | sin_tempo | 5 | 0.0 | 0.0005 | 0 |
| vivo | sin_tempo | 6 | 1.0 | 0.0007 | 8 |
| vivo | sin_tempo | 7 | 1.0 | 0.047 | 0 |
| vivo | sin_tempo | 8 | 1.0 | 0.2209 | 0 |
| vivo | sin_tempo | 9 | 1.0 | 0.0055 | 0 |
| vivo | sin_tempo | 10 | 0.5 | 0.0004 | 5 |
| vivo | sin_tempo | 11 | 1.0 | 0.1769 | 10 |
| vivo | sin_tempo | 12 | 1.0 | 0.0426 | 10 |

- ALERTA P4: el perfil 2 (base) empeora su ajuste en 2 usuarios al caer arbitrum.
- ALERTA P4: el perfil 2 (base) empeora su ajuste en 2 usuarios al caer canton.
- ALERTA P4: el perfil 2 (base) empeora su ajuste en 2 usuarios al caer celo.
- ALERTA P4: el perfil 2 (base) empeora su ajuste en 9 usuarios al caer tempo.
- ALERTA P4: el perfil 3 (base) empeora su ajuste en 4 usuarios al caer tempo.
- ALERTA P4: el perfil 6 (base) empeora su ajuste en 10 usuarios al caer tempo.
- ALERTA P4: el perfil 11 (base) empeora su ajuste en 10 usuarios al caer tempo.
- ALERTA P4: el perfil 12 (base) empeora su ajuste en 10 usuarios al caer tempo.
- ALERTA P4: el perfil 2 (vivo) empeora su ajuste en 2 usuarios al caer tempo.
- ALERTA P4: el perfil 3 (vivo) empeora su ajuste en 1 usuarios al caer tempo.
- ALERTA P4: el perfil 6 (vivo) empeora su ajuste en 8 usuarios al caer tempo.
- ALERTA P4: el perfil 10 (vivo) empeora su ajuste en 5 usuarios al caer tempo.
- ALERTA P4: el perfil 11 (vivo) empeora su ajuste en 10 usuarios al caer tempo.
- ALERTA P4: el perfil 12 (vivo) empeora su ajuste en 10 usuarios al caer tempo.

## P5. Sensibilidad del usuario

Atributo que mas cambia la banda 1 por perfil.

| fuente | perfil | atributo mas sensible | cuota de cambio |
|---|---|---|---|
| base | 1 | transfronterizo_inverso | 1.0 |
| base | 2 | transfronterizo_inverso | 0.9 |
| base | 3 | transfronterizo_inverso | 1.0 |
| base | 4 | transfronterizo_inverso | 1.0 |
| base | 5 | transfronterizo_inverso | 1.0 |
| base | 6 | transfronterizo_inverso | 1.0 |
| base | 7 | transfronterizo_inverso | 1.0 |
| base | 8 | transfronterizo_inverso | 1.0 |
| base | 9 | transfronterizo_inverso | 1.0 |
| base | 10 | transfronterizo_inverso | 1.0 |
| base | 11 | transfronterizo_inverso | 1.0 |
| base | 12 | monto_x2 | 0.6 |
| vivo | 1 | transfronterizo_inverso | 1.0 |
| vivo | 2 | transfronterizo_inverso | 0.8 |
| vivo | 3 | transfronterizo_inverso | 1.0 |
| vivo | 4 | transfronterizo_inverso | 1.0 |
| vivo | 5 | transfronterizo_inverso | 1.0 |
| vivo | 6 | transfronterizo_inverso | 1.0 |
| vivo | 7 | transfronterizo_inverso | 1.0 |
| vivo | 8 | transfronterizo_inverso | 1.0 |
| vivo | 9 | transfronterizo_inverso | 1.0 |
| vivo | 10 | transfronterizo_inverso | 1.0 |
| vivo | 11 | transfronterizo_inverso | 1.0 |
| vivo | 12 | monto_div2 | 0.9 |

## P6. Convergencia de replicas

| fuente | replicas | referencia | banda 1 | orden completo |
|---|---|---|---|---|
| base | 500 | 40000 | 0.967 | 0.942 |
| base | 2000 | 40000 | 0.967 | 0.933 |
| base | 10000 | 40000 | 1.0 | 0.983 |
| base | 40000 | 40000 | 1.0 | 1.0 |
| vivo | 500 | 40000 | 0.942 | 0.817 |
| vivo | 2000 | 40000 | 0.983 | 0.942 |
| vivo | 10000 | 40000 | 1.0 | 0.967 |
| vivo | 40000 | 40000 | 1.0 | 1.0 |

- ALERTA P6: las 10000 replicas de la tesis no coinciden por completo con la referencia (1.0 en banda 1, 0.983 en orden completo, base).
- ALERTA P6: las 10000 replicas de la tesis no coinciden por completo con la referencia (1.0 en banda 1, 0.967 en orden completo, vivo).

## P7. Panel continuo

- Ciclos: 1142 (1142 validos, 0 invalidos por cobertura de metricas vivas).
- Evaluaciones de usuario en ciclos validos: 137040; cambios de banda 1 entre ciclos consecutivos: 1801.
- Usuarios con banda 1 distinta entre modo vivo y modo medicion: 35576 (0.26).
- La causa probable es una atribucion indicativa (mayor cambio relativo entre perfiles); ver serie_vivo.csv.
