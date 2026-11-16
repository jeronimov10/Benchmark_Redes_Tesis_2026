# Modelo de decisión y banco de usuarios simulados

El modelo de la tesis (§5.4) está en `backend/modelo/modelo.py` y se usa **sin modificaciones**. Contrato de integración: `backend/modelo/INTEGRACION.md`. El banco de usuarios simulados (`backend/simulacion/`) lo evalúa desde afuera. Resultados: [../resultados/benchmark.md](../resultados/benchmark.md) y [../resultados/pruebas.md](../resultados/pruebas.md); límites: [../resultados/limitaciones.md](../resultados/limitaciones.md).

## Qué resuelve

Dado un pago (monto COP, transfronterizo, espera tolerable, irrevocabilidad, TRM) devuelve en qué redes conviene liquidar, agrupadas en **bandas** de desempeño no distinguible, con certidumbre y la métrica que más separa la banda 1 de la 2. No mueve dinero ni consulta ninguna red: es una función de decisión sobre perfiles ya medidos.

## Cálculo

1. **Vector del caso**: monto (COP 10 000 a 1 000 millones) y espera (1 s a 86 400 s) en escala logarítmica, transfronterizo 0/1, irrevocabilidad 0 / 0,5 / 1.
2. **Pesos interpolados** entre tres escenarios de referencia por distancia ponderada (γ = 1; 1,5; 1; 1,2) y mezcla inversa de distancia (p = 2). Certidumbre κ = exp(−d_min/0,6)·√(1 − H/ln 3).

   | Escenario | Posición (monto, transfr., espera, irrev.) | Pesos A / B / C / D |
   |---|---|---|
   | Remesas (USD 300, espera 1 h, irrev. baja) | 0,42; 1; 0,72; 0 | 0,45 / 0,15 / 0,15 / 0,25 |
   | Comercio (COP 48 906, espera 20 s, irrev. media) | 0,14; 0; 0,26; 0,5 | 0,35 / 0,35 / 0,15 / 0,15 |
   | Alto valor (COP 100 M, espera 10 min, irrev. alta) | 0,80; 0; 0,56; 1 | 0,10 / 0,30 / 0,40 / 0,20 |

3. **Compuertas** antes de puntuar: G1 (latencia > 20 s en comercio), G2 (sin finalidad anclada: B2 nulo), G3 (D2 ≤ 0), G4 (capacidad < 1 salvo cota inferior). Una red que falla queda **inadmisible** con su motivo, sin puntaje (no cero).
4. **Puntaje**: cada métrica a [0, 1] por umbrales objetivo/inaceptable en escala logarítmica (C3 en nueves); media por bloque A–D; media geométrica ponderada con piso 0,05. Las métricas nulas se excluyen del cálculo y se avisan.

   | Métrica | Objetivo (puntaje 1) | Inaceptable (puntaje 0) |
   |---|---|---|
   | A1 costo / ticket | 0,1 % | 1 % |
   | A2 p95/mediana | 1,5 | 10 |
   | A3 pendiente de congestión | 0,2 | 2 |
   | A4 anclaje | 0,001 | 0,10 |
   | B1 inclusión (s) | 3 | 20 |
   | B2, B2b firmeza (s) | 20 | 86 400 |
   | B3 margen de capacidad | 5 | 1 |
   | C1 HHI | 0,10 | 1,00 |
   | C2 operadores > 50 % | 15 | 1 |
   | C3 continuidad (nueves) | 99,999 % | 99,9 % |
   | C4 fallo | 0,1 % | 5 % |
   | C5 cambios | 0,5 | 5 |
   | D1 independiente del token nativo | 50 % | 1 % |
   | D2 referencia de conciliación | 20 % | 0,1 % |
   | D3 multi-transferencia | 10 % | 0,1 % |

5. **Monte Carlo** (10 000 réplicas, semilla 42): ruido gaussiano por métrica (`sigma`) y pesos Dirichlet (κ = 50). Una red entra a una banda nueva solo si supera a todas las de la banda actual en ≥ 85 % de las réplicas.

## Entradas y qué las alimenta

`perfiles[red][métrica] = {valor, sigma, nota, cota_inferior?}`. El backend construye este perfil con `ServicioPerfiles.construir(modo)`:

- `medicion`: solo línea base (Polygon, Celo y Arbitrum de `perfiles.json`; Tempo, Aptos y Canton convertidos desde `resultados/metrics.csv`). Reproduce los casos de referencia de la tesis.
- `vivo` (por defecto): base sobrescrita por métricas en vivo válidas y frescas.

Conversiones de la línea base de Tempo, Aptos y Canton (`services/analytics/baseline.py`): A2 = p95/mediana; B3 × 48/18 (la tesis exige 18 TPS); C3 en porcentaje; **C1 del modelo = C1b** (HHI de peso de consenso); `sigma = 0` con nota explícita; no computable → `null`; Canton B3 es `cota_inferior`; B2b ausente.

## Salida (`POST /api/modelo`, acción `recomendar`)

`estado` (`ok`, `datos_insuficientes` o `sin_redes_admisibles`), `resultado` (salida de `modelo.recomendar` sin cambios: composición, pesos, certidumbre, inadmisibles, bandas, determinante, advertencias), `nivel_certidumbre` (alta ≥ 0,75; media 0,45 a 0,75; baja < 0,45), `detalle` por red, `procedencia`, `frescura`, `version_perfil`, `modo` y `decidido_en`.

No se inventan puntajes ni probabilidades. Con menos de dos redes con datos no se genera recomendación. **La recomendación es la banda 1**; si tiene varias redes, están empatadas y no se debe mostrar una sola como ganadora. El determinante se muestra como «lo que más pesó», no como «la razón».

Frecuencia y frescura: el modelo se evalúa bajo demanda (unos 4 s la primera vez con seis redes y 10 000 réplicas, menos de 0,3 s desde caché). El resultado cambia solo si cambia `version_perfil`. Las métricas en vivo vencen a los 15 min y entonces se usa la base.

## Cómo extenderlo

No se edita `modelo.py`. Para cambiar datos se reemplaza el perfil (`perfiles.json` o recalibración). Para añadir una red, ver [ARCHITECTURE.md](ARCHITECTURE.md#cómo-añadir-una-red). Cualquier cambio de pesos, umbrales o fórmulas es una decisión de tesis.

---

# Banco de usuarios simulados

Las pruebas normales comprueban que el modelo reproduce la tesis, no que su recomendación sirva para lo que cada persona necesita. El banco crea usuarios simulados con necesidades declaradas, le pide una recomendación al modelo (sin modificarlo, en su propio pool de procesos) y compara lo recomendado con lo que necesitaban.

**Regla de oro**: lo único simulado es la demanda. Ninguna métrica de red se inventa; los contrafactuales solo quitan redes, métricas o incertidumbre, nunca agregan un valor que no se midió. El banco escribe solo en `simulacion.db` y en su directorio de salida; nunca en `redes.db` ni en `recomendaciones`.

## Los 12 perfiles

Cada usuario toma valores dentro de los rangos de su perfil con semilla fija, en escala logarítmica para monto y espera. Montos en USD convertidos con TRM 4 000. Los centros de los perfiles 1 a 3 vienen de los escenarios de la tesis; los rangos de los perfiles 4 a 12 son supuestos de diseño, ilustrativos.

| # | Perfil | Tipo | Monto | Transfr. | Espera | Irrev. |
|---|---|---|---|---|---|---|
| 1 | Remesa familiar | control | USD 200–500 | sí | 30 min–2 h | baja |
| 2 | Tendero con QR | control | COP 15 000–159 456 | no | 5–20 s | media |
| 3 | Tesorería de alto valor | control | COP 50–200 M | no | 5–20 min | alta |
| 4 | Microremesa | hueco | USD 20–100 | sí | 1–24 h | baja |
| 5 | Freelancer | hueco | USD 500–5 000 | sí | 1–24 h | media |
| 6 | E-commerce | hueco | COP 100 000–2 M | no | 1–10 min | media |
| 7 | Nómina de pyme | hueco | COP 1,5–8 M | no | 1–4 h | media |
| 8 | Proveedor B2B | hueco | COP 20–80 M | no | 10–60 min | alta |
| 9 | Importador | hueco | USD 20 000–250 000 | sí | 1–24 h | alta |
| 10 | Remesa urgente | hueco | USD 200–500 | sí | 5–60 s | media |
| 11 | Liquidación urgente | hueco | COP 50–500 M | no | 5–30 s | alta |
| 12 | Micropago de transporte | fuera de rango | COP 3 000–10 000 | no | 1–5 s | baja |

Los controles (1 a 3) confirman que el arnés se comporta en terreno conocido; el valor está en los otros nueve.

## Cuántos usuarios por perfil

Se estima, por perfil, qué parte de sus usuarios recibe la banda 1 más frecuente: se evalúan 50 usuarios, se calcula el intervalo de Wilson al 95 % y, si su semiancho es ≤ 5 puntos, el perfil se detiene; si no, se agregan 50 más hasta un tope de 400. Un perfil que llega al tope es un perfil sin respuesta clara.

## Ajuste a la necesidad

Para cada usuario se revisa si cada red cumple lo pedido, solo con umbrales que ya existen en el modelo:

| Criterio | Condición | Origen del umbral |
|---|---|---|
| Costo | A1 ≤ 1 % del ticket | Valor inaceptable de A1 |
| Espera, lectura preferencia | B1 ≤ espera_s | Espera declarada |
| Espera, lectura requisito | B2 ≤ espera_s | Espera declarada |
| Irrevocabilidad alta | B2b ≤ 86 400 s (o B2 si no hay B2b) | Valor inaceptable de B2b |

`INTEGRACION.md` define la espera como «tolerable hasta la confirmación» sin decir cuál, así que se reportan las dos lecturas; ninguna se impone al modelo. Cada usuario termina en un estado: **cumple** (todas las redes de la banda 1 satisfacen la necesidad), **parcial** (empate en banda 1 y solo algunas cumplen), **brecha** (ninguna de la banda 1 cumple pero otra red admisible sí; el error más importante), **sin solución** (ninguna red admisible cumple; problema de oferta) o **no evaluable** (falta el dato; se cuenta aparte y nunca se asume).

## Las siete pruebas

P1 a P6 corren en lote, sobre la línea base y sobre una foto de los datos en vivo; P7 es continua. Donde hace falta un grupo pequeño se usa un panel fijo de 120 usuarios (10 por perfil).

| Prueba | Pregunta | Qué hace | Alerta si |
|---|---|---|---|
| P1 Cobertura | ¿A qué perfiles cubre bien el modelo? | Banda 1 modal y su cuota, empates, certidumbre, determinante | Certidumbre baja en la mayoría o llega al tope de 400 |
| P2 Ajuste | ¿La recomendación cumple lo pedido? | Estado de ajuste por usuario en las dos lecturas de la espera | Cuota relevante de brecha |
| P3 Contrafactuales de medición | ¿El ganador depende de cómo se midió cada red? | Solo las 13 métricas comunes; sin sigma; solo P/C/A; solo T/A/C; Aptos en sombra | Muchos perfiles cambian de ganador |
| P4 Caída de una red | ¿Qué pasa si la recomendada falla? | Repite el panel quitando cada red | El ajuste empeora o no hay respaldo admisible |
| P5 Sensibilidad | ¿Es frágil ante cambios pequeños? | Monto ×2 y ÷2, espera ×4 y ÷4, irrevocabilidad ±1, transfronterizo invertido | Cambia de red con un ajuste que el usuario no notaría |
| P6 Convergencia | ¿Cuántas réplicas hacen falta? | 500, 2 000, 10 000 y 40 000 réplicas contra la de 40 000 | Las 10 000 de la tesis no coinciden con la referencia |
| P7 Panel continuo | ¿La recomendación cambia con la red en vivo? | Reevalúa los 120 usuarios cada 15 min con el perfil en vivo | Cambios en horas sin cambio sostenido de la red |

En P7 los usuarios no cambian entre ciclos, así que cualquier cambio de su recomendación solo puede venir de la red. Un ciclo con menos de la mitad de las métricas vivas esperadas se guarda marcado inválido y no entra en los indicadores. La causa probable de un cambio es la métrica con mayor cambio relativo entre los dos perfiles guardados: es una atribución indicativa. El panel se reanuda solo tras un reinicio (estado `continuo_activo` en `simulacion.db`); necesita al menos 3 días (B2 de Tempo usa 72 h) y lo ideal son 14.

## Ejecución

Desde `backend/`:

```bash
python -m simulacion lote --fuente base --replicas 500 --tope 100 --panel 3    # lote reducido
python -m simulacion lote --fuente ambas                                        # lote completo P1-P6 (10 000 réplicas)
python -m simulacion continuo                                                   # panel P7; Ctrl+C para detener (necesita los colectores)
python -m simulacion informe                                                    # informe.md y CSV desde simulacion.db
python -m simulacion publicar                                                   # resultados/pruebas.md y .html desde resultados/pruebas/datos/
```

La salida va a `backend/data/simulacion/` (o `--salida`). El código: `personas.py` (perfiles y generación), `fuentes.py` (línea base y perfil vivo, solo lectura), `evaluador.py` (llama a `modelo.recomendar` y calcula el ajuste), `experimentos.py` (P1–P6), `continuo.py` (P7), `almacen.py` (`simulacion.db`), `informe.py` (informe y CSV: `informe.md`, `personas.csv`, `contrafactuales.csv`, `sensibilidad.csv`, `convergencia.csv`, `serie_vivo.csv`, `manifiesto.json`), `publicar.py` (páginas finales).

## Límites que hay que declarar

- No representa el mercado: los perfiles no están ponderados por demanda real; los resultados se leen por perfil, nunca como porcentaje de la población.
- Los rangos de los perfiles 4 a 12 son supuestos.
- El banco hereda las mediciones: la línea base de Tempo, Aptos y Canton viene de una muestra reducida, Canton B3 es cota inferior y el precio de APT está congelado.
- El ajuste es una lectura externa: un mal ajuste es evidencia para discutir, no un defecto demostrado.
- La cuota «relevante» de alertas no se fija: se reportan las cifras.
- El banco no toma decisiones de tesis: si los resultados sugieren una nueva compuerta, se documenta como propuesta; `modelo.py` y `score_engine.py` no cambian por esta prueba.
