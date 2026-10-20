# Redfacil (frontend)

Interfaz Next.js 16 (React 19, next-intl es/en, Tailwind 4) de la aplicación de recomendación de red de liquidación. **No contiene el modelo ni datos de redes:** todo viene del backend FastAPI (`../backend`), al que Next reenvía `/api/*` (variable `BACKEND_URL`, por defecto `http://127.0.0.1:8000`).

## Ejecutar

```bash
pnpm install
pnpm dev           # http://localhost:3000 (el backend debe estar en :8000)
pnpm test          # vitest
pnpm exec tsc --noEmit
pnpm lint
pnpm build
```

## Qué muestra

- `/[locale]/monitor`: salud de cada colector, valor, origen (vivo/base), edad y ventana de cada métrica, y el botón Recalibrar.
- `/[locale]/result/[id]`: recomendación por bandas, certidumbre, advertencias, banner de frescura de datos y detalle por red con procedencia por métrica.
- `/[locale]/standard`: umbrales, pesos y compuertas leídos de `GET /api/modelo`.
- Estados distintos para cargando, éxito, dato obsoleto (refresco fallido), vacío, datos insuficientes y error.

## Estructura

- `src/modelo/cliente.ts`: acceso a la API (caché por entrada con TTL de 30 s, refresco periódico, sondeo de `/api/mediciones` y `/api/recalibracion`). `tipos.ts`: forma de las respuestas.
- `src/lib/monitor.ts`: utilidades de presentación del monitoreo (edad, etiquetas, razones).
- `src/components/result/EstadoDatos.tsx`: aviso de frescura, etiqueta de procedencia y pantalla de datos insuficientes.
- `src/engine/`: solo tipos y constantes de presentación (ids de redes, bloques, TRM demostrativa); el motor de cálculo vive en el backend.
- `src/state/`: usuarios e historial de pagos del prototipo en `localStorage` (sin backend de usuarios).
- `messages/{es,en}.json`: textos; una prueba exige las mismas claves en ambos.

## Datos

La TRM (4000 COP/USDT) es demostrativa. El historial sembrado de cada usuario (`src/state/seed.ts`) es ficticio y está marcado como demo; las recomendaciones de esos pagos sí se calculan con el backend.
