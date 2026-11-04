#!/usr/bin/env bash
# Opera el banco de usuarios simulados desplegado en Railway.
# Uso: API_URL=https://<dominio> SIMULACION_TOKEN=<token> scripts/pruebas_railway.sh verificar|lote|estado|continuo on|continuo off|cancelar|descargar [destino]
set -euo pipefail

API_URL="${API_URL:?define API_URL, por ejemplo https://mi-servicio.up.railway.app}"
API_URL="${API_URL%/}"
AUTH=()
[ -n "${SIMULACION_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${SIMULACION_TOKEN}")
JSON=(-H "content-type: application/json")

cmd="${1:-}"
case "$cmd" in
  verificar)
    curl -fsS "$API_URL/api/integraciones"; echo ;;
  estado)
    curl -fsS "$API_URL/api/simulacion"; echo ;;
  lote)
    cuerpo="${LOTE_JSON:-{\}}"
    curl -fsS -X POST "${AUTH[@]}" "${JSON[@]}" -d "$cuerpo" "$API_URL/api/simulacion/lote"; echo
    echo "esperando a que termine el lote (Ctrl+C no lo cancela)..."
    while curl -fsS "$API_URL/api/simulacion" | grep -q '"ocupado":true'; do
      sleep "${SONDEO_S:-30}"
      curl -fsS "$API_URL/api/simulacion" | grep -o '"etapa":"[^"]*"' | head -1 || true
    done
    curl -fsS "$API_URL/api/simulacion" | grep -o '"estado":"[a-z_]*"' | head -1 ;;
  cancelar)
    curl -fsS -X DELETE "${AUTH[@]}" "$API_URL/api/simulacion/lote"; echo ;;
  continuo)
    case "${2:-}" in
      on)  curl -fsS -X POST "${AUTH[@]}" "$API_URL/api/simulacion/continuo"; echo ;;
      off) curl -fsS -X DELETE "${AUTH[@]}" "$API_URL/api/simulacion/continuo"; echo ;;
      *) echo "uso: continuo on|off" >&2; exit 2 ;;
    esac ;;
  descargar)
    destino="${2:-resultados/simulacion}"
    mkdir -p "$destino"
    curl -fsS -X POST "${AUTH[@]}" "$API_URL/api/simulacion/informe" >/dev/null
    for f in $(curl -fsS "$API_URL/api/simulacion/archivos" | grep -o '"nombre":"[^"]*"' | cut -d'"' -f4); do
      curl -fsS -o "$destino/$f" "$API_URL/api/simulacion/archivos/$f" && echo "descargado $destino/$f"
    done ;;
  *)
    echo "uso: $0 verificar|estado|lote|cancelar|continuo on|off|descargar [destino]" >&2; exit 2 ;;
esac
