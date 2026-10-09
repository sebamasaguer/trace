$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RECICLATRACE - DEMO MOVIL HTTPS v0.1.7" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker no esta disponible en PATH. Inicie Docker Desktop y vuelva a ejecutar."
}

function Invoke-NativeQuiet {
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Command *> $null
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    return $exitCode
}

function Invoke-NativeText {
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $result = (& $Command 2>&1 | Out-String)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    return @{ ExitCode = $exitCode; Text = $result }
}

$dockerInfoExit = Invoke-NativeQuiet { docker info }
if ($dockerInfoExit -ne 0) {
    throw "Docker Desktop no esta iniciado o no responde."
}

$ComposeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.mobile.yml")

Write-Host "[1/6] Limpiando intento anterior (sin borrar PostgreSQL)..." -ForegroundColor Yellow
$downExit = Invoke-NativeQuiet { docker compose @ComposeFiles down --remove-orphans }
if ($downExit -ne 0) {
    throw "No se pudo limpiar el intento anterior (codigo $downExit)."
}

function Test-TcpPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    }
    catch { return $false }
    finally {
        if ($null -ne $listener) { try { $listener.Stop() } catch {} }
    }
}

function Get-AvailablePort {
    param(
        [Parameter(Mandatory = $true)][int]$Preferred,
        [int[]]$Exclude = @()
    )
    for ($port = $Preferred; $port -le ($Preferred + 99); $port++) {
        if ($Exclude -contains $port) { continue }
        if (Test-TcpPortAvailable -Port $port) { return $port }
    }
    throw "No se encontro un puerto TCP libre entre $Preferred y $($Preferred + 99)."
}

$FrontendPort = Get-AvailablePort -Preferred 3210
$BackendPort = Get-AvailablePort -Preferred 8210 -Exclude @($FrontendPort)
$env:RECICLA_FRONTEND_PORT = [string]$FrontendPort
$env:RECICLA_BACKEND_PORT = [string]$BackendPort

Write-Host "[2/6] Puertos locales seleccionados:" -ForegroundColor DarkCyan
Write-Host "  Frontend: $FrontendPort -> contenedor 3100" -ForegroundColor DarkCyan
Write-Host "  Backend : $BackendPort -> contenedor 8100" -ForegroundColor DarkCyan

Write-Host "[3/6] Construyendo ReciclaTrace + tunel HTTPS temporal..." -ForegroundColor Yellow
docker compose @ComposeFiles up --build -d
if ($LASTEXITCODE -ne 0) { throw "Fallo docker compose up para demo movil." }

Write-Host "[4/6] Esperando backend..." -ForegroundColor Yellow
$healthUrl = "http://localhost:$BackendPort/health"
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.status -eq "ok") { $ok = $true; break }
    }
    catch {}
    Start-Sleep -Seconds 2
}
if (-not $ok) {
    docker compose @ComposeFiles ps
    docker compose @ComposeFiles logs backend --tail 80
    throw "El backend no respondio en $healthUrl"
}

Write-Host "[5/6] Esperando URL HTTPS para el celular..." -ForegroundColor Yellow
$MobileUrl = $null
for ($i = 0; $i -lt 45; $i++) {
    $logResult = Invoke-NativeText { docker compose @ComposeFiles logs tunnel --no-color --tail 120 }
    if ($logResult.Text -match 'https://[a-zA-Z0-9-]+\.trycloudflare\.com') {
        $MobileUrl = $Matches[0]
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $MobileUrl) {
    Write-Host ""
    docker compose @ComposeFiles logs tunnel --tail 100
    throw "El tunel HTTPS no entrego una URL en el tiempo esperado. Verifique acceso a Internet y vuelva a intentar."
}

$localUrl = "http://localhost:$FrontendPort"
$docsUrl = "http://localhost:$BackendPort/docs"

Write-Host "[6/6] DEMO MOVIL LISTA." -ForegroundColor Green
Write-Host "" 
Write-Host "URL PARA EL CELULAR (HTTPS):" -ForegroundColor Cyan
Write-Host "  $MobileUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Local PC : $localUrl" -ForegroundColor Green
Write-Host "API Docs : $docsUrl" -ForegroundColor Green
Write-Host "Health   : $healthUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Usuarios de prueba:" -ForegroundColor Cyan
Write-Host "  admin       / Admin123!" -ForegroundColor Green
Write-Host "  recolector  / Recolector123!" -ForegroundColor Green
Write-Host "  planta      / Planta123!" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANTE: la URL trycloudflare es temporal y publica. Al terminar ejecute .\DETENER_DEMO.ps1." -ForegroundColor Yellow
Write-Host "La camara debe abrirse desde la URL HTTPS, no desde una IP http:// de la red local." -ForegroundColor Yellow

if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
    try {
        Set-Clipboard -Value $MobileUrl
        Write-Host "La URL movil fue copiada al portapapeles." -ForegroundColor DarkCyan
    }
    catch {}
}

Start-Process $localUrl
