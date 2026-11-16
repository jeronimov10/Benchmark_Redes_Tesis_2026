# Levanta el proyecto con Docker en Windows (opciones: -ConfiarEnInterceptor -SoloCopiar -SoloBuild -Down -NoCache).
param([switch]$ConfiarEnInterceptor, [switch]$SoloCopiar, [switch]$SoloBuild, [switch]$Down, [switch]$NoCache)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$patron = "Avast|AVG |Kaspersky|ESET|Bitdefender|Zscaler|Netskope|Fortinet|Web Shield|Sophos|Forcepoint|Palo Alto|Norton|McAfee|Trend Micro|SSL Inspection"
$certs = Join-Path $repo "certs"
$exportadas = 0
$candidatas = @()
if ($ConfiarEnInterceptor) { $candidatas = Get-ChildItem Cert:\CurrentUser\Root, Cert:\LocalMachine\Root }
foreach ($c in ($candidatas | Where-Object { $_.Subject -match $patron } | Sort-Object Thumbprint -Unique)) {
    $pem = "-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($c.RawData, "InsertLineBreaks") + "`n-----END CERTIFICATE-----`n"
    [IO.File]::WriteAllText((Join-Path $certs ("ca-" + $c.Thumbprint.Substring(0, 12) + ".crt")), $pem)
    Write-Host "CA de interceptacion TLS exportada a certs/: $($c.Subject)"
    $exportadas++
}

$trabajo = $repo
if ($repo -match "OneDrive") {
    $trabajo = Join-Path $env:LOCALAPPDATA "benchmark-redes-docker"
    Write-Host "Repo en OneDrive: se construye desde $trabajo"
    $excluir = @(".git", "frontend\node_modules", "frontend\.next", "backend\data", "resultados\raw") | ForEach-Object { Join-Path $repo $_ }
    robocopy $repo $trabajo /MIR /XD $excluir /XF *.pdf *.xlsx *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy fallo con codigo $LASTEXITCODE" }
}

Write-Host "Copia lista en: $trabajo"
if ($SoloCopiar) { exit 0 }
Set-Location $trabajo
if ($Down) { docker compose down; exit $LASTEXITCODE }
if ($NoCache) { docker compose build --no-cache; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
if ($SoloBuild) { docker compose build; if ($LASTEXITCODE) { exit $LASTEXITCODE }; Write-Host "Imagenes listas. Para levantar: cd $trabajo; docker compose up -d"; exit 0 }
docker compose up --build -d
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Write-Host "Frontend: http://localhost:3000   Backend: http://localhost:8000/docs   (logs: docker compose logs -f backend)"
