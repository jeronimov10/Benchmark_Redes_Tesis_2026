# Opera el banco de usuarios simulados desplegado en Railway.
# Uso: $env:API_URL="https://<dominio>"; $env:SIMULACION_TOKEN="<token>"; .\scripts\pruebas_railway.ps1 verificar|estado|lote|cancelar|continuo on|continuo off|descargar [destino]
param([Parameter(Position = 0)][string]$Comando, [Parameter(Position = 1)][string]$Arg)

$api = $env:API_URL
if (-not $api) { throw "define `$env:API_URL, por ejemplo https://mi-servicio.up.railway.app" }
$api = $api.TrimEnd("/")
$h = @{}
if ($env:SIMULACION_TOKEN) { $h["Authorization"] = "Bearer $($env:SIMULACION_TOKEN)" }

switch ($Comando) {
    "verificar" { Invoke-RestMethod "$api/api/integraciones" | ConvertTo-Json -Depth 8 }
    "estado" { Invoke-RestMethod "$api/api/simulacion" | ConvertTo-Json -Depth 8 }
    "lote" {
        $cuerpo = if ($env:LOTE_JSON) { $env:LOTE_JSON } else { "{}" }
        Invoke-RestMethod -Method Post -Uri "$api/api/simulacion/lote" -Headers $h -ContentType "application/json" -Body $cuerpo | ConvertTo-Json -Depth 8
        $sondeo = if ($env:SONDEO_S) { [int]$env:SONDEO_S } else { 30 }
        do {
            Start-Sleep -Seconds $sondeo
            $e = Invoke-RestMethod "$api/api/simulacion"
            Write-Host "$($e.lote.etapa) | evaluaciones: $($e.lote.evaluaciones)"
        } while ($e.ocupado)
        Write-Host "estado final: $($e.lote.estado)"
    }
    "cancelar" { Invoke-RestMethod -Method Delete -Uri "$api/api/simulacion/lote" -Headers $h | ConvertTo-Json }
    "continuo" {
        if ($Arg -eq "on") { Invoke-RestMethod -Method Post -Uri "$api/api/simulacion/continuo" -Headers $h | ConvertTo-Json }
        elseif ($Arg -eq "off") { Invoke-RestMethod -Method Delete -Uri "$api/api/simulacion/continuo" -Headers $h | ConvertTo-Json }
        else { throw "uso: continuo on|off" }
    }
    "descargar" {
        $destino = if ($Arg) { $Arg } else { "resultados/simulacion" }
        New-Item -ItemType Directory -Force $destino | Out-Null
        Invoke-RestMethod -Method Post -Uri "$api/api/simulacion/informe" -Headers $h | Out-Null
        foreach ($a in (Invoke-RestMethod "$api/api/simulacion/archivos").archivos) {
            Invoke-WebRequest "$api/api/simulacion/archivos/$($a.nombre)" -OutFile (Join-Path $destino $a.nombre)
            Write-Host "descargado $destino/$($a.nombre)"
        }
    }
    default { throw "uso: verificar|estado|lote|cancelar|continuo on|off|descargar [destino]" }
}
