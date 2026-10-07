$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

Write-Host "Deteniendo ReciclaTrace..." -ForegroundColor Yellow
$previousPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    docker compose -f docker-compose.yml -f docker-compose.mobile.yml down --remove-orphans
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousPreference
}
if ($exitCode -ne 0) { throw "No se pudieron detener los servicios (codigo $exitCode)." }
Write-Host "Servicios detenidos, incluido el tunel movil. Los datos PostgreSQL se conservan." -ForegroundColor Green
