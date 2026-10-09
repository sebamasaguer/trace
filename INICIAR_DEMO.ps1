$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RECICLATRACE - INICIO DE DEMO v0.1.7" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker no esta disponible en PATH. Inicie Docker Desktop y vuelva a ejecutar."
}

# Windows PowerShell 5.1 convierte STDERR de programas nativos redirigido
# en NativeCommandError cuando ErrorActionPreference=Stop. Docker escribe
# mensajes normales de progreso en STDERR, por lo que las llamadas silenciosas
# se ejecutan temporalmente con Continue y luego se valida LASTEXITCODE.
function Invoke-NativeQuiet {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

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

$dockerInfoExit = Invoke-NativeQuiet { docker info }
if ($dockerInfoExit -ne 0) {
    throw "Docker Desktop no esta iniciado o no responde."
}

# Limpia solamente los contenedores del proyecto ReciclaTrace.
# NO usa -v: el volumen PostgreSQL y los datos se conservan.
Write-Host "[1/4] Limpiando intento anterior del proyecto..." -ForegroundColor Yellow
$downExit = Invoke-NativeQuiet { docker compose down --remove-orphans }
if ($downExit -ne 0) {
    throw "No se pudo limpiar el intento anterior de ReciclaTrace (docker compose down, codigo $downExit)."
}

function Test-TcpPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch {}
        }
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

# Se eligen los puertos DESPUES de limpiar los contenedores anteriores,
# para no descartar un puerto que estaba ocupado solamente por ReciclaTrace.
$FrontendPort = Get-AvailablePort -Preferred 3210
$BackendPort = Get-AvailablePort -Preferred 8210 -Exclude @($FrontendPort)

$env:RECICLA_FRONTEND_PORT = [string]$FrontendPort
$env:RECICLA_BACKEND_PORT = [string]$BackendPort

Write-Host "Puertos seleccionados:" -ForegroundColor DarkCyan
Write-Host "  Frontend host : $FrontendPort -> contenedor 3100" -ForegroundColor DarkCyan
Write-Host "  Backend host  : $BackendPort -> contenedor 8100" -ForegroundColor DarkCyan

Write-Host "[2/4] Construyendo e iniciando servicios..." -ForegroundColor Yellow
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw "Fallo docker compose up." }

Write-Host "[3/4] Esperando backend..." -ForegroundColor Yellow
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
    docker compose ps
    Write-Host ""
    docker compose logs backend --tail 80
    throw "El backend no respondio en $healthUrl"
}

$frontendUrl = "http://localhost:$FrontendPort"
$docsUrl = "http://localhost:$BackendPort/docs"

Write-Host "[4/4] Sistema listo." -ForegroundColor Green
Write-Host "Frontend : $frontendUrl" -ForegroundColor Green
Write-Host "API Docs : $docsUrl" -ForegroundColor Green
Write-Host "Health   : $healthUrl" -ForegroundColor Green
Write-Host "Usuario  : admin" -ForegroundColor Green
Write-Host "Clave    : Admin123!" -ForegroundColor Green
Write-Host ""
Write-Host "Nota: los puertos del HOST se eligen automaticamente si 3210/8210 estan ocupados." -ForegroundColor DarkGray
Write-Host "Para probar la camara desde celular use .\INICIAR_DEMO_MOVIL.ps1" -ForegroundColor DarkGray

Start-Process $frontendUrl
