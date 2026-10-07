# ReciclaTrace v0.1.3

Hotfix de arranque para Windows PowerShell 5.1.

## Corregido

- Evita `NativeCommandError` durante `docker compose down --remove-orphans` cuando Docker escribe mensajes normales de progreso en STDERR.
- La comprobación `docker info` usa el mismo wrapper compatible con PowerShell 5.1.
- Primero limpia los contenedores previos de ReciclaTrace y recién después selecciona puertos libres.
- Conserva el volumen PostgreSQL: el arranque no ejecuta `docker compose down -v`.
- Mantiene selección automática de puertos desde 3210 (frontend) y 8210 (backend).

## Motivo

Windows PowerShell 5.1 transforma STDERR redirigido de aplicaciones nativas en registros `NativeCommandError`. Docker Compose utiliza STDERR también para progreso normal, incluso cuando el comando está funcionando correctamente. El wrapper `Invoke-NativeQuiet` evita que ese comportamiento interrumpa el script y valida el código de salida real con `$LASTEXITCODE`.
