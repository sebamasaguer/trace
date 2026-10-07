$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

Write-Host "ATENCION: se eliminaran los datos de demostracion y el volumen PostgreSQL." -ForegroundColor Yellow
$confirm = Read-Host "Escriba RESET para continuar"
if ($confirm -ne "RESET") { Write-Host "Cancelado."; exit 0 }

$previousPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    docker compose -f docker-compose.yml -f docker-compose.mobile.yml down -v --remove-orphans
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousPreference
}
if ($exitCode -ne 0) { throw "No se pudo resetear ReciclaTrace (codigo $exitCode)." }
Write-Host "Datos eliminados. Ejecute INICIAR_DEMO.ps1 o INICIAR_DEMO_MOVIL.ps1 para recrear el entorno." -ForegroundColor Green
