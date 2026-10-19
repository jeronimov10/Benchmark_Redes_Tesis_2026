# Modelo de decisión

Es el modelo de la tesis (§5.4), implementado en `backend/modelo/modelo.py` y usado sin modificaciones. Contrato de integración: `backend/modelo/INTEGRACION.md`.

## Qué resuelve

Dado un pago (monto COP, transfronterizo, espera tolerable, irrevocabilidad, TRM) devuelve en qué redes conviene liquidar, agrupadas en **bandas** de desempeño no distinguible, con certidumbre y la métrica que más separa la banda 1 de la 2.

## Cálculo

1. **Vector del caso**: monto y espera en escala logarítmica, transfronterizo 0/1, irrevocabilidad 0/0,5/1.
2. **Pesos interpolados** entre tres escenarios de referencia (remesas, comercio, alto valor) por distancia ponderada (γ = 1; 1,5; 1; 1,2), mezcla inversa de distancia (p = 2). Certidumbre κ = exp(−d_min/0,6)·√(1 − H/ln 3).
3. **Compuertas** G1 (latencia > 20 s en comercio), G2 (sin finalidad anclada: B2 nulo), G3 (D2 ≤ 0), G4 (capacidad < 1 salvo cota inferior). Una red que falla queda inadmisible con su motivo.
4. **Puntaje**: cada métrica a [0,1] por umbrales objetivo/inaceptable (escala log; C3 en nueves); media por bloque A–D; media geométrica ponderada (piso 0,05). Las métricas nulas se excluyen.
5. **Monte Carlo** (10 000 réplicas, semilla 42): ruido gaussiano por métrica (`sigma`) y pesos Dirichlet (κ = 50). Una red entra a una banda nueva solo si supera a todas las de la banda actual en ≥ 85 % de las réplicas.

## Entradas y qué las alimenta

`perfiles[red][métrica] = {valor, sigma, nota, cota_inferior?}`. El backend construye este perfil con `ServicioPerfiles.construir(modo)`:

- `medicion`: solo línea base (Polygon/Celo/Arbitrum de `perfiles.json`; Tempo/Aptos/Canton convertidos desde `resultados/metrics.csv`). Reproduce los casos de referencia de la tesis.
- `vivo` (por defecto): base sobrescrita por métricas en vivo válidas y frescas.

Conversiones de la línea base de Tempo/Aptos/Canton (`services/analytics/baseline.py`): A2 = p95/mediana; B3 × 48/18 (la tesis exige 18 TPS); C3 en porcentaje; **C1 del modelo = C1b** (HHI de peso de consenso, D3 del plan); `sigma = 0` con nota explícita; no computable → `null`; B2b ausente.

## Salida (`POST /api/modelo`, acción `recomendar`)

`estado` (`ok` | `datos_insuficientes` | `sin_redes_admisibles`), `resultado` (salida de `modelo.recomendar` sin cambios: composición, pesos, certidumbre, inadmisibles, bandas, determinante, advertencias), `nivel_certidumbre`, `detalle` por red (métricas con puntaje y procedencia, bloques, compuertas), `procedencia`, `frescura`, `version_perfil`, `modo`, `decidido_en`.

No se inventan puntajes ni probabilidades: todo sale del modelo. Con menos de dos redes con datos no se genera recomendación (`datos_insuficientes`). La **recomendación es la banda 1**; si tiene varias redes están empatadas.

## Frecuencia y frescura

El modelo se evalúa bajo demanda (tarda ~4 s la primera vez con 6 redes y 10 000 réplicas, <0,3 s desde caché). El resultado cambia solo si cambia `version_perfil`, es decir, cuando una métrica en vivo o la base cambia. Las métricas en vivo vencen a los 15 min y entonces se usa la base.

## Cómo extenderlo

No se edita `modelo.py`. Para cambiar datos se reemplaza el perfil (`perfiles.json` o recalibración). Para añadir una red, ver [CLAUDE.md](../CLAUDE.md#cómo-añadir-una-red).
