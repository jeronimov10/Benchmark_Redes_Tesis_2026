# Desarrollo

## Requisitos

Python 3.11+, Node 22+ y pnpm 12 (`npm install -g pnpm` o `corepack enable`). Sin claves de API.

## Ejecutar

```bash
pip install -r backend/requirements.txt
cd backend && python -m uvicorn app.main:app --reload --port 8000     # API + colectores
cd frontend && pnpm install && pnpm dev                              # UI en :3000
```

Para ver la UI sin red: `COLECTORES_ACTIVOS=false` (usa solo la línea base). Para una base nueva, borra `backend/data/redes.db*`.

## Pruebas y validación

```bash
cd backend && python -m pytest tests
cd frontend && pnpm test && pnpm exec tsc --noEmit && pnpm lint && pnpm build
python backend/benchmark/main.py     # benchmark con resultados/raw/ (sin red); `--collect` vuelve a consultar las redes
```

Qué cubre cada archivo de `backend/tests/`:

| Archivo | Cubre |
|---|---|
| `test_decision.py` | Casos de referencia de la tesis (±0,005), perfil efectivo, obsolescencia, datos insuficientes, caché |
| `test_reproduce_benchmark.py` | Las métricas en vivo reproducen `resultados/metrics.csv` sobre las muestras crudas de Tempo, Aptos y Canton |
| `test_colectores.py` | Colectores con HTTP simulado, monitor sin solapamiento, continuidad |
| `test_cliente_http.py` | Reintentos, backoff, 429, timeouts, JSON malformado |
| `test_api.py` | Formas de respuesta, validación, salud, recalibración |
| `test_infra.py` | Migraciones, repositorios, poda, caché, línea base, validadores |

## Convenciones

- Código en español para dominio (`muestras`, `perfiles`), nombres técnicos en inglés cuando son estándar.
- Cada archivo lleva solo un comentario/docstring de cabecera que dice qué hace; no se comenta línea a línea.
- La lógica no va en controladores ni en `routes/`.
- `backend/modelo/` (`modelo.py`, `perfiles.json`, `casos_referencia.json`, `pruebas_modelo.py`) no se edita.

## Notas

- Los scripts de `backend/benchmark/` resuelven sus rutas relativas al directorio actual (`resultados/...`); ejecútalos desde la raíz del repositorio. `main.py` localiza sus scripts por su propia ubicación.
- Documentos históricos (`docs/plan_*.md`, `docs/matriz_requerimientos.md`, `docs/fase4_verificacion.md`) mencionan las rutas antiguas `scripts/` y `main.py`; ahora están en `backend/benchmark/`.
- En Windows, si el puerto 3000 está ocupado por otro proyecto, usa `pnpm exec next dev -p 3100`.
