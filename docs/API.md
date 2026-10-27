# API

Backend FastAPI en `http://localhost:8000`. El frontend la consume como `/api/*` (Next la reenvía a `BACKEND_URL`). Documentación interactiva en `/docs`. Errores: `{"error": "mensaje"}`; peticiones inválidas devuelven `400` con `{"error": "peticion invalida", "detalle": [...]}`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/salud` | Estado de base de datos, monitor y colectores por red |
| GET | `/api/redes` | Las seis redes: responsable, fuente, métricas en vivo y solo-base con su razón |
| GET | `/api/mediciones` | Instantánea de todas las redes (cacheada ≤ 30 s) |
| GET | `/api/mediciones/{red}` | Una red + series cortas de sus métricas vivas (`404` si no existe) |
| GET | `/api/modelo` | Descripción del modelo: redes, umbrales, escenarios, versión y frescura |
| POST | `/api/modelo` | `interpretar` o `recomendar` |
| POST | `/api/recalibracion` | Inicia la recalibración (`409` si hay una en curso, `422` red desconocida) |
| GET | `/api/recalibracion` | Estado del último trabajo y alcance |
| DELETE | `/api/recalibracion` | Cancela (`409` si no hay trabajo) |

## POST /api/modelo

Petición:

```json
{ "accion": "recomendar", "monto_cop": 1200000, "transfronterizo": true, "espera_s": 3600,
  "irrevocabilidad": "baja", "trm": 4000, "modo": "vivo" }
```

`accion`: `recomendar` (defecto) | `interpretar` (solo composición y certidumbre, sin Monte Carlo). `modo`: `vivo` (defecto) | `medicion`. Límites: `monto_cop` ∈ (0, 1e13], `espera_s` ∈ (0, 1e7], `trm` ∈ (0, 1e6].

Respuesta `recomendar`:

```json
{
  "estado": "ok",                       // "datos_insuficientes" | "sin_redes_admisibles"
  "motivo": null,
  "resultado": { "caso": {}, "composicion": {}, "pesos": {}, "certidumbre": 0.985,
                 "inadmisibles": { "aptos": [["G2", "…"]] },
                 "bandas": [ { "banda": 1, "redes": ["tempo"], "puntajes": { "tempo": { "mediana": 0.86, "p05": 0.8, "p95": 0.9 } },
                               "separacion_con_siguiente": 0.97 } ],
                 "determinante": { "metrica": "D3", "contribucion": 0.08 }, "advertencias": [] },
  "nivel_certidumbre": "alta",
  "detalle": { "tempo": { "metricas": [ { "id": "A1", "valor": 0.00003, "puntaje": 1, "procedencia": { "origen": "vivo", "edad_s": 12, "n": 55, "ventana_s": 86400 } } ],
                          "bloques": { "A": 0.9 }, "puntaje_central": 0.85, "compuertas_falladas": [] } },
  "procedencia": { "tempo": { "A1": { "origen": "vivo" } } },
  "frescura": { "metricas_vivo": 54, "metricas_total": 90, "edad_vivo_max_s": 46, "edad_vivo_min_s": 8 },
  "version_perfil": "3b1e2664946f", "modo": "vivo", "decidido_en": "2026-10-19T13:40:00+00:00",
  "medicion": "…", "trm": 4000, "redes_sin_datos": []
}
```

Con `datos_insuficientes`, `resultado` es `null`. `version_perfil` cambia cuando cambia cualquier entrada del perfil efectivo.

## GET /api/mediciones

```json
{ "generado_en": "…", "version_perfil": "…", "frescura": {}, "obsolescencia_s": 900,
  "redes": [ { "id": "tempo", "nombre": "Tempo", "responsable": "Jeronimo", "fuente": "…",
               "salud": { "estado": "ok|degradada|caida|sin_datos", "componentes": [ { "componente": "bloques", "edad_ok_s": 12, "fallos_consecutivos": 0, "error": null } ] },
               "muestras": { "muestras_bloque": 120 },
               "metricas": [ { "id": "B1", "valor": 0.585, "origen": "vivo|base|null", "edad_s": 9, "n": 261, "ventana_s": 900,
                               "vivo": { "estado": "valida|insuficiente|obsoleta|fallida|no_computable", "n": 261 },
                               "razon_solo_base": null, "estado_vivo_esperado": true } ] } ] }
```

## Recalibración

`POST` acepta `{ "redes": ["tempo", "polygon"], "bloques_tempo": 50, "bloques_aptos": 20, "paginas_canton": 2, "minutos_evm": 10 }` (todo opcional; `redes` vacío = las seis). Tempo/Aptos/Canton recalibran su línea base; Polygon/Celo/Arbitrum rellenan `minutos_evm` minutos (5 a 1440) de su ventana en vivo sin tocar su línea base. Respuesta: `{ "id", "redes", "no_disponible" }`. `GET` devuelve `{ "trabajo": { "estado": "en_curso|completado|fallido|cancelado|interrumpido", "progreso": 0-1, "etapa", "log_tail" }, "ocupado", "alcance": { "recalibra", "rellena", "no_disponible", "motivo_no_disponible", "nota_rellena", "no_resuelve" } }`.
