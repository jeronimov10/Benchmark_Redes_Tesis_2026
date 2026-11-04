# Monitor de redes y recomendación de liquidación (Tempo, Aptos, Canton, Polygon, Celo, Arbitrum)

Proyecto de grado. Aplicación web que monitorea seis redes casi en tiempo real y recomienda en cuál liquidar un pago en pesos colombianos (remesas, comercio, alto valor), usando el modelo de decisión de la tesis. **Recomienda; no mueve fondos ni ejecuta transferencias.**

## Arranque rápido

```bash
SOLO MAQUINA JERONIMO: cd C:\dev\Benchmark_Redes_Tesis_2026
docker compose up --build
```

Frontend en http://localhost:3000 y backend en http://localhost:8000. Es el único comando necesario (Docker con Compose; en Windows, con el repo fuera de OneDrive); detalles, puertos y solución de problemas en [Cómo correr el proyecto (Docker)](#cómo-correr-el-proyecto-docker).

Diagrama completo de arquitectura y funcionamiento (qué métricas son en vivo, cuáles no, cómo se calculan y cómo decide el modelo): [docs/arquitectura_y_funcionamiento.mmd](docs/arquitectura_y_funcionamiento.mmd). Se abre en <https://mermaid.live> o con la extensión Mermaid de VS Code.

## Problema y objetivos

Elegir una red para liquidar un pago depende de costo, tiempo, concentración, continuidad y primitivas de pago, y esas propiedades cambian. El sistema:

1. Mide cada red con consultas reproducibles a su registro público (JSON-RPC, REST, Scan API). Nunca se completa un valor con documentación o declaraciones (regla de oro, ver [CLAUDE.md](CLAUDE.md)).
2. Normaliza las mediciones a un modelo único y las guarda en SQLite.
3. Alimenta el modelo de la tesis (`backend/modelo/modelo.py`, sin modificar) con esas mediciones.
4. Expone el resultado por una API y lo muestra en el frontend, indicando de dónde viene cada valor y qué tan fresco es.

## Funcionalidades

- Seis redes en un mismo pipeline: Polygon, Celo, Arbitrum (Dilan) y Tempo, Aptos, Canton (Jerónimo).
- Métricas en vivo (sondeo cada ~20 s) sobre ventanas móviles; lo que no se puede calcular en vivo conserva su medición base y se marca como tal.
- Recomendación por bandas, certidumbre, compuertas y métrica determinante, con procedencia por métrica (`vivo` / `base`) y edad.
- Estados explícitos: cargando, ok, dato obsoleto, datos insuficientes, error.
- Página **Monitoreo**: salud de cada colector, valor/origen/edad de cada métrica y botón **Recalibrar** (mediciones base de Tempo/Aptos/Canton y relleno de la ventana reciente de Polygon/Celo/Arbitrum).
- Modo `medicion` que reproduce exactamente la tesis (solo mediciones base).

## Tecnología

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11, FastAPI, uvicorn, httpx, SQLite (stdlib), pycryptodome (keccak) |
| Modelo | `backend/modelo/modelo.py` (stdlib), ejecutado en un pool de procesos |
| Frontend | Next.js 16, React 19, next-intl (es/en), Tailwind 4, vitest, pnpm |
| Pruebas | pytest (backend), vitest (frontend) |

## Arquitectura (monorepo monolítico, MVC)

### Diagrama de arquitectura (flujo de datos)

```mermaid
flowchart LR
  subgraph Redes
    T[Tempo RPC] --- A[Aptos REST] --- C[Canton Scan] --- P[Polygon/Celo/Arbitrum RPC]
  end
  Redes --> COL[Colectores async<br/>retry + backoff]
  COL --> PRO[Procesadores<br/>muestras normalizadas]
  PRO --> DB[(SQLite)]
  DB --> MET[Métricas en vivo<br/>ventanas móviles]
  MET --> PERF[Perfil efectivo<br/>base + vivo]
  BASE[(Línea base<br/>perfiles.json + metrics.csv)] --> PERF
  PERF --> MOD[modelo.py<br/>pool de procesos]
  MOD --> API[FastAPI /api]
  API --> FE[Next.js]
```

Detalle en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Diagrama de contexto

```mermaid
flowchart TB
  U([Usuario<br/>describe un pago en COP]) --> FE[Frontend Next.js<br/>:3000]
  FE -->|/api/* proxy| BE[Backend FastAPI<br/>:8000]
  BE --> DB[(SQLite<br/>backend/data/redes.db)]
  BE --> MOD[[Modelo de la tesis<br/>backend/modelo/modelo.py]]
  BE -->|JSON-RPC| EVM[Polygon · Celo · Arbitrum · Tempo]
  BE -->|REST| APT[Aptos + Pyth on-chain]
  BE -->|Scan API| CAN[Canton]
  BE -->|eth_call| CL[Chainlink<br/>precios ETH · MATIC · CELO]
  BE -.->|subproceso, botón Recalibrar| BEN[backend/benchmark<br/>pipeline por lotes]
  BEN --> RES[(resultados/<br/>metrics.csv)]
  RES -->|siembra la línea base| DB
  PJ[(perfiles.json<br/>Dilan, 90 días)] -->|siembra la línea base| DB
```

### Diagrama de la base de datos (SQLite)

```mermaid
erDiagram
  redes { text id PK text nombre text responsable text endpoints }
  muestras_bloque { text red PK int numero PK real ts text productor real gas_usado real gas_limite int n_tx }
  muestras_tx { text red PK text hash PK int bloque real ts real fee_usd real ocupacion int estado_ok int patrocinada int memo int multi_transfer int tiene_transfer }
  muestras_finalidad { text red PK int bloque PK real tau_1 real tau_f real delta_s }
  lecturas_estado { int id PK text red text clave text valor_json real ts }
  metricas_vivo { int id PK text red text metrica real valor real sigma text estado int n real ventana_s real ts text nota }
  perfiles_base { text red PK text metrica PK real valor real sigma int cota_inferior text origen int version }
  salud_colector { text red PK text componente PK real ultimo_ok text error int fallos_consecutivos }
  trabajos_recalibracion { text id PK text estado real progreso text etapa text log_tail }
  recomendaciones { int id PK text entrada_json text modo text version_perfil text resultado_json }
  meta { text clave PK text valor }
  redes ||--o{ muestras_bloque : "red"
  redes ||--o{ muestras_tx : "red"
  redes ||--o{ muestras_finalidad : "red"
  redes ||--o{ lecturas_estado : "red"
  redes ||--o{ metricas_vivo : "red"
  redes ||--o{ perfiles_base : "red"
  redes ||--o{ salud_colector : "red"
```

`lecturas_estado` guarda lecturas puntuales (validadores, configuración, cursor de Canton, continuidad C3 acumulada, ranura de proxy). Las relaciones con `redes` son lógicas (la columna `red`), sin claves foráneas. Detalle del flujo en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Despliegue en Railway y pruebas con usuarios simulados

Guía paso a paso, endpoints, scripts y cómo ver los resultados en el front (página `/es/simulation`) en [docs/RAILWAY.md](docs/RAILWAY.md); diseño de las pruebas en `docs/diseno_pruebas_usuarios_simulados.html`.

## Estructura

```
backend/
  app/                 FastAPI (MVC): routes/ controllers/ models/ services/ pipelines/ db/ utils/
  modelo/              modelo de la tesis + perfiles medidos (sin modificar)
  benchmark/           pipeline por lotes del benchmark Tempo/Aptos/Canton (main.py, collect_*, compute_*)
  simulacion/          banco de usuarios simulados (12 perfiles, pruebas P1-P7; ver docs/RAILWAY.md)
  tests/               pytest
frontend/              Next.js (src/app, src/components, src/modelo, src/lib, src/engine)
resultados/            salidas del benchmark (metrics.csv, benchmark_final.csv, raw/)
docs/                  plan, arquitectura, pipeline, modelo, redes, API, desarrollo
```

## Redes y fuentes

| Red | Responsable | Fuente | Métricas en vivo |
|---|---|---|---|
| Tempo | Jerónimo | JSON-RPC `rpc.tempo.xyz` | 14 de 16 (todas menos A4, B2b) |
| Aptos | Jerónimo | REST `api.mainnet.aptoslabs.com` | 10 (B2, C3, D2, C5 solo base); sin clave de API el servicio limita a 40 000 unidades/300 s por IP |
| Canton | Jerónimo | Scan API `api.cantonnodes.com` | 13 (D1 solo base) |
| Polygon | Dilan | JSON-RPC público + checkpoints (`RootChainProxy`) en Ethereum | 13 (B3, D2, D3 solo base) |
| Celo | Dilan | JSON-RPC `forno.celo.org` + juegos de disputa (`DisputeGameFactory`) en Ethereum | 12 (B2b, B3, D2, D3 solo base) |
| Arbitrum | Dilan | JSON-RPC `arb1.arbitrum.io` + lotes (`SequencerInbox`) en Ethereum | 12 (B2b, B3, D2, D3 solo base) |

La tabla completa y las razones de cada métrica solo-base están en [docs/NETWORK_INTEGRATIONS.md](docs/NETWORK_INTEGRATIONS.md).

## Pipeline casi en tiempo real

Un colector asyncio por red sondea bloques/eventos, estado (validadores, configuración) y finalidad; las muestras van a SQLite; cada 30 s se recalculan las métricas sobre sus ventanas (15 min, 24 h, 72 h, 14 d) y se invalida la caché. Una métrica en vivo solo reemplaza a la base si es `valida` (n suficiente) y fresca. Ver [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md).

## Modelo de decisión

Metodología de la tesis (§5.4), sin cambios: interpolación de pesos entre tres escenarios, compuertas G1–G4, media geométrica por bloques, Monte Carlo con pesos Dirichlet y bandas. Ver [docs/DECISION_MODEL.md](docs/DECISION_MODEL.md).

## API

`GET /api/salud`, `/api/redes`, `/api/mediciones[/{red}]`, `/api/modelo`; `POST /api/modelo`; `POST|GET|DELETE /api/recalibracion`. Ver [docs/API.md](docs/API.md). Documentación interactiva en `http://localhost:8000/docs`.

## Variables de entorno

Todas opcionales (no se requieren claves). Lista completa en [.env.example](.env.example). Las más relevantes: `DB_PATH`, `RPC_POLYGON` (los RPC públicos de Polygon son inestables; usa un proveedor propio si hace falta), `OBSOLESCENCIA_S`, `VENTANA_*`, `BACKEND_URL` (frontend).

## Cómo correr el proyecto (Docker)

Requisito único: Docker con Compose. No se necesitan claves de API.

```bash
docker compose up --build
```

Ese comando construye las dos imágenes y levanta todo:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend (API y `/docs`) | http://localhost:8000 |

Probado: las dos imágenes compilan, el backend queda `healthy`, las seis redes responden `ok` y el frontend recomienda con datos en vivo. El backend crea su base SQLite en un volumen (`datos`), siembra la línea base y empieza a sondear las seis redes; el frontend espera a que el backend esté sano. Los datos en vivo se conservan entre reinicios.

Uso diario:

```bash
docker compose up -d --build     # en segundo plano
docker compose logs -f backend   # ver el sondeo
docker compose down              # detener (conserva los datos)
docker compose down -v           # detener y borrar la base de datos
```

Qué ver: `http://localhost:3000/es/start` (crea un usuario) → `/es/monitor` (estado de colectores y métricas en vivo/base; tras ~1 minuto ya hay datos) → `/es/transaction/new` (describe un pago y mira el resultado).

### Solución de problemas de Docker

**¿Quién necesita esto?** Solo quien esté en uno de los dos casos de abajo (carpeta dentro de OneDrive, o antivirus/proxy que intercepta HTTPS). Un tercero que clone el repositorio en una carpeta normal (por ejemplo `C:\dev\...` o `~/proyectos/...`), sin ese tipo de antivirus, ejecuta únicamente `docker compose up --build`: no necesita `scripts/` ni `certs/`. La CA de un antivirus es de cada máquina y no se versiona (`certs/*.crt` está en `.gitignore`).

**Recomendado en Windows:** clonar o copiar el repo fuera de OneDrive (`C:\dev\Benchmark_Redes_Tesis_2026`) y trabajar desde ahí.

Dos causas explican casi todos los fallos "a veces funciona, a veces no". Ambas dependen de la máquina, no del código.

**Máquina de Jerónimo (OneDrive + Avast):** el build se corre desde `C:\dev\Benchmark_Redes_Tesis_2026`, nunca desde la carpeta de OneDrive:

```powershell
cd C:\dev\Benchmark_Redes_Tesis_2026
docker compose up --build
```

Esa carpeta ya tiene la CA de Avast en `certs/` (archivo local, no versionado). Si `certs/` queda sin ese `.crt`, se regenera con `scripts\docker-up.ps1 -ConfiarEnInterceptor -SoloBuild`. Esto no aplica a otras máquinas.

**1. `invalid file request Dockerfile` / `failed to execute bake` (repo dentro de OneDrive, Windows).** BuildKit no puede leer los archivos "solo en la nube" de OneDrive aunque estén fijados localmente (`attrib +P` no basta). Construye desde una copia fuera de OneDrive; el script lo hace solo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1        # copia a %LOCALAPPDATA%\benchmark-redes-docker y hace compose up --build -d
powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1 -Down  # detener
```

Lo más estable es mover el repo fuera de OneDrive (entonces basta `docker compose up --build`).

**2. `CERTIFICATE_VERIFY_FAILED` en `pip install`, `pnpm install` o en los logs del backend (las seis redes "caídas").** Un antivirus o proxy corporativo (p. ej. Avast "Web/Mail Shield") intercepta el HTTPS y firma con su propia CA. Windows confía en ella, pero los contenedores no. Es intermitente porque el antivirus no siempre escanea. Dos soluciones:

- Desactiva el escaneo HTTPS del antivirus (Avast: Configuración → Protección → Escudos principales → Escudo web → desmarcar "Habilitar análisis HTTPS"), o
- Haz que las imágenes confíen en esa CA: copia su certificado raíz en PEM, con extensión `.crt`, a la carpeta [certs/](certs/) y reconstruye (`docker compose build --no-cache`). En Windows, `scripts\docker-up.ps1 -ConfiarEnInterceptor` exporta a `certs/` las CA de antivirus/proxy conocidas que encuentre en el almacén de Windows. Úsalo solo en una máquina propia: hace que los contenedores confíen en esa CA.

El backend detecta este caso: en vez de reintentar, registra "certificado TLS no confiable ... intercepta HTTPS" en el log y en `/api/salud`. No se desactiva la verificación TLS en ningún punto.

Si el puerto 3000 u 8000 está ocupado, cámbialo sin editar archivos: `FRONTEND_PORT=3100 BACKEND_PORT=8001 docker compose up --build` (PowerShell: `$env:FRONTEND_PORT="3100"; docker compose up --build`). Para usar otro RPC: `RPC_POLYGON=https://tu-proveedor docker compose up --build`. Sin internet: `COLECTORES_ACTIVOS=false docker compose up --build` (solo línea base).

### Sin Docker (desarrollo)

Requisitos: Python 3.11+, Node.js 22+ y pnpm (`npm install -g pnpm`). No hay claves que configurar.

```bash
pip install -r backend/requirements.txt          # dependencias del backend (idealmente en un venv)
cd frontend && pnpm install && cd ..             # dependencias del frontend

cd backend && python -m uvicorn app.main:app --port 8000   # terminal 1: API + colectores (crea backend/data/redes.db)
cd frontend && pnpm dev                                    # terminal 2: UI en http://localhost:3000 (/api/* se reenvía a BACKEND_URL)
```

Variables útiles (opcionales; ver [.env.example](.env.example)): `BACKEND_URL` (frontend, por defecto `http://127.0.0.1:8000`), `RPC_POLYGON` y demás `RPC_*`, `DB_PATH`, `COLECTORES_ACTIVOS=false` (solo línea base, sin internet). En PowerShell: `$env:RPC_POLYGON="https://..."; python -m uvicorn app.main:app --port 8000`.

Sin Docker el backend usa el almacén de certificados del sistema operativo, así que un antivirus que intercepta HTTPS no suele afectar (ver el punto 2 de la solución de problemas si aparece `CERTIFICATE_VERIFY_FAILED`).

## Pruebas

```bash
cd backend && python -m pytest tests        # 87 pruebas (incluye el banco de usuarios simulados)
cd frontend && pnpm test && pnpm exec tsc --noEmit && pnpm lint && pnpm build
python backend/benchmark/main.py            # benchmark por lotes con resultados/raw/ (sin red)
```

## Qué funciona y qué no

**Funciona (verificado en vivo el 2026-10-19):** los seis colectores contra las redes reales; 54 de 90 métricas en vivo; recomendación en modo `vivo` y `medicion`; casos de referencia de la tesis (±0,005); monitoreo en el frontend; Recalibrar (corrida real corta completada); 64 pruebas de backend y 19 de frontend.

**No funciona o es parcial:**

| Qué | Por qué |
|---|---|
| Aptos B2, D2, C3 | Bloques de ~20 ms, definición A-5 sin fijar, muestreo sin cobertura de huecos |
| P/C/A: B3, D2, D3 en vivo y B2b de Celo y Arbitrum | Definiciones de la tesis no reproducibles (lista de intercambios, referencia estricta) o ventanas de 90 días / 6,4 días; usan la base |
| Anclaje de P/C/A: ventana de 24 h | Los nodos públicos de Ethereum solo conservan ~10 000 bloques (~33 h) y los que aceptan consultas más antiguas devuelven vacío sin avisar; con un RPC de archivo propio (`RPC_ETHEREUM`) se puede ampliar con `VENTANA_ANCLAJE_S` |
| Recalibrar Aptos | El API anónimo cobra por tamaño de respuesta (un bloque ≈ 2 200 unidades de 40 000 por 5 min): 40 bloques ≈ 11 min; con `APTOS_API_KEY` no hay espera |
| B2 (72 h) y C3/C5 (14 d) en vivo | Solo cuentan cuando el backend lleva corriendo toda la ventana |
| Persistencia de usuarios | Solo `localStorage` del navegador; no hay cuentas ni backend de usuarios |
| RPC públicos | Pueden limitar o caer (Polygon ya cambió de proveedor) |

## Limitaciones conocidas

- **Aptos B2** no es medible por HTTP (bloques ~20 ms); **Aptos D2** necesita fijar la definición A-5; ambos quedan sin dato.
- **Polygon/Celo/Arbitrum**: A3, A4, B2 (y B2b en Polygon) se calculan en vivo; el anclaje en Ethereum se observa en ventana de 24 h (B2 = cadencia/2, como la línea base de la tesis). B3, D2, D3 y B2b de Celo/Arbitrum solo existen en su medición base de 90 días. El botón Recalibrar rellena la ventana reciente de estas redes (no modifica su línea base).
- Ventanas largas (B2 72 h, C3/C5 14 d) se llenan con el backend corriendo; mientras tanto se usa la base.
- El precio de APT en Pyth está congelado desde 2026-08-26; A1/A2 de Aptos lo usan y lo marcan.
- Canton B3 es la asignación gratuita por miembro (probablemente subestima) y se marca como cota inferior.
- Tempo/Aptos/Canton en base no tienen incertidumbre (`sigma=0`).
- Los RPC públicos tienen límites; Polygon requiere a veces cambiar de proveedor.
