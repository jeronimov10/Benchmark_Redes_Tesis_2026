# Despliegue en Railway y ejecución del banco de usuarios simulados

Solo el backend (FastAPI + colectores + banco `backend/simulacion/`) va a Railway. Un único servicio con un volumen: SQLite y los colectores exigen **una sola réplica**. El diseño de las pruebas está en `docs/diseno_pruebas_usuarios_simulados.html`.

## Qué se despliega

| Pieza | Archivo |
|---|---|
| Imagen (sin CAs extra ni `VOLUME`, puerto de `$PORT`) | `backend/Dockerfile.railway` |
| Build, healthcheck `/api/salud`, 1 réplica | `railway.toml` |
| Datos persistentes (`redes.db`, `simulacion.db`, `simulacion/`) | volumen en `/app/backend/data` |
| Operar las pruebas desde tu máquina | `scripts/pruebas_railway.sh` / `.ps1` |

## Paso a paso

1. **Sube el código a GitHub** (rama → PR → `main`). Railway despliega desde el repo.
2. En [railway.com](https://railway.com): **New Project → Deploy from GitHub repo** y elige este repositorio. Railway lee `railway.toml` (raíz del repo) y construye `backend/Dockerfile.railway`. Si el primer build falla antes de crear el volumen, no importa: se arregla en el paso 3.
3. **Volumen**: en el servicio, *Settings → Volumes → Add volume*, ruta de montaje `/app/backend/data`. Sin volumen, cada deploy borra la base y la línea base en vivo.
4. **Variables** (*Variables → New Variable*):

   | Variable | Valor | Para qué |
   |---|---|---|
   | `SIMULACION_TOKEN` | cadena aleatoria larga (`openssl rand -hex 24`) | protege POST/DELETE de `/api/simulacion`. Sin ella los endpoints quedan abiertos |
   | `SIM_PROCESOS` | `4` (según los vCPU del plan) | procesos del modelo del banco |
   | `CORS_ORIGINS` | `http://localhost:3000` | solo si luego conectas un frontend |
   | `RPC_POLYGON`, `RPC_CELO`, `RPC_ARBITRUM`, … | opcional | si un RPC público limita la IP de Railway (ver `.env.example`) |

   `APTOS_API_KEY` no se configura: Aptos corre anónimo (4 bloques/75 s, límite de 40 000 unidades/300 s por IP). Si ves `429` de Aptos, saca una clave gratuita en Aptos Build y agrégala.
5. **Dominio**: *Settings → Networking → Generate Domain*. Guarda la URL (`https://<servicio>.up.railway.app`).
6. Espera el deploy (el healthcheck llama a `/api/salud`) y comprueba:
   ```bash
   curl https://<dominio>/api/salud
   ```
7. **Verifica las integraciones externas desde Railway** (la IP de Railway puede estar limitada por algún proveedor, por eso se prueba desde allí):
   ```bash
   curl https://<dominio>/api/integraciones
   ```
   Debe devolver `"estado":"ok"` con 14/14 fuentes. Si `degradado`, mira `fallidas` y el `error` exacto de cada una. Una fuente `limitado` (HTTP 429) **no es una caída**: responde pero limita por IP, y su colector comparte esa cuota (pasa sobre todo con Canton, que tiene un límite estricto); espera ~30 s y repite, o confirma en `/api/salud` que la red está `ok`. El resultado se cachea 30 s (`desde_cache`) para no gastar cuota. Fuentes: Tempo, Polygon, Celo, Arbitrum, Ethereum (principal y respaldo), Aptos, Canton (`/v0/dso` y `/v0/events`), Pyth Hermes y los 4 precios en cadena.
8. **Apaga los colectores locales** (cierra `uvicorn`/Docker en tu PC). Dos recolecciones de Aptos desde la misma IP se estorban; en Railway la IP es solo de Railway, pero no dupliques el sondeo.
9. **Espera ~15 minutos** para que las métricas vivas sean válidas (`/api/mediciones` o `frescura.metricas_vivo` en `/api/salud`). Algunas ventanas (B2 de Tempo: 72 h; C3: 14 días) tardan más; el lote sobre la línea base no las necesita.

## Ejecutar las pruebas

Variables para los scripts:

```bash
export API_URL=https://<dominio>
export SIMULACION_TOKEN=<el mismo token>
```
```powershell
$env:API_URL = "https://<dominio>"; $env:SIMULACION_TOKEN = "<el mismo token>"
```

| Qué | Bash | PowerShell |
|---|---|---|
| Integraciones | `scripts/pruebas_railway.sh verificar` | `.\scripts\pruebas_railway.ps1 verificar` |
| **Lote P1–P6** (espera hasta terminar) | `scripts/pruebas_railway.sh lote` | `.\scripts\pruebas_railway.ps1 lote` |
| Estado | `scripts/pruebas_railway.sh estado` | `.\scripts\pruebas_railway.ps1 estado` |
| Panel continuo P7 | `scripts/pruebas_railway.sh continuo on` / `off` | `.\scripts\pruebas_railway.ps1 continuo on` / `off` |
| Cancelar lote | `scripts/pruebas_railway.sh cancelar` | `.\scripts\pruebas_railway.ps1 cancelar` |
| Descargar informe y CSV a `resultados/simulacion/` | `scripts/pruebas_railway.sh descargar` | `.\scripts\pruebas_railway.ps1 descargar` |

### Con `curl` directo

```bash
# Lanzar todas las pruebas (P1-P6, línea base y foto en vivo). Responde 202 {"id": ...}
curl -X POST https://<dominio>/api/simulacion/lote \
  -H "Authorization: Bearer $SIMULACION_TOKEN" -H "content-type: application/json" -d '{}'

# Seguir el avance (etapa, evaluaciones, ocupado)
curl https://<dominio>/api/simulacion

# Iniciar el panel continuo (15 min por ciclo; sobrevive a reinicios y redeploys)
curl -X POST https://<dominio>/api/simulacion/continuo -H "Authorization: Bearer $SIMULACION_TOKEN"

# Regenerar el informe desde la base y bajar un archivo
curl -X POST https://<dominio>/api/simulacion/informe -H "Authorization: Bearer $SIMULACION_TOKEN"
curl -O https://<dominio>/api/simulacion/archivos/informe.md
```

Cuerpo opcional del lote (`LOTE_JSON` en los scripts): `{"pruebas":["P1","P2","P3","P4","P5","P6"],"fuente":"base|vivo|ambas","semilla":2026,"replicas":10000,"tope":400,"panel_por_perfil":10,"niveles_replicas":[500,2000,10000,40000]}`. Por defecto `fuente=ambas`: corre todo sobre la línea base y sobre una foto del perfil en vivo (si no hay métricas vivas válidas, omite la foto y lo anota). Un lote a la vez: otro `POST` devuelve `409`.

## Tiempos y costo

- Lote completo con 10 000 réplicas: del orden de 1 h por fuente con `SIM_PROCESOS=4` (estimación del diseño, ~1,8 s por evaluación). Para una prueba de humo: `LOTE_JSON='{"fuente":"base","replicas":500,"tope":100,"panel_por_perfil":3,"niveles_replicas":[500,2000]}'` (≈ 1 min en local).
- Panel continuo: 120 evaluaciones cada 15 min (~6 h de CPU al día repartidas en `SIM_PROCESOS` procesos). Mínimo útil 3 días (B2 de Tempo necesita 72 h), ideal 14.
- Railway factura por uso (CPU, RAM, volumen). Detén el panel (`continuo off`) cuando termines.
- Un redeploy interrumpe un lote en curso (queda `interrumpido`); el panel continuo se reanuda solo.

## Salidas

`informe.md`, `personas.csv`, `contrafactuales.csv`, `sensibilidad.csv`, `convergencia.csv`, `serie_vivo.csv` y `manifiesto.json` (semilla, commit, versión de perfil, réplicas, TRM) se escriben en el volumen (`/app/backend/data/simulacion/`) y se descargan con `descargar`. Un ciclo del panel con menos de la mitad de las métricas vivas esperadas se guarda como inválido y no entra en los indicadores.

## Local (sin Railway)

```bash
cd backend
python -m simulacion lote --fuente base --replicas 500 --tope 100 --panel 3 --niveles 500 2000
python -m simulacion informe
python -m simulacion continuo         # Ctrl+C para detener; necesita los colectores corriendo (la API)
```
La salida va a `backend/data/simulacion/` (cambia con `--salida` o `SIM_DIR`).
