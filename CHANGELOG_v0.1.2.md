# ReciclaTrace v0.1.2 - Puertos robustos

## Motivo
La v0.1.1 construia correctamente, pero Docker no pudo publicar el backend porque el puerto host `8100` ya estaba ocupado.

## Cambio principal
- Frontend preferido: `3210` (contenedor interno `3100`).
- Backend preferido: `8210` (contenedor interno `8100`).
- `INICIAR_DEMO.ps1` verifica ambos puertos antes de iniciar.
- Si un puerto preferido esta ocupado, selecciona automaticamente el siguiente puerto libre dentro de un rango de 100 puertos.
- Los puertos seleccionados se inyectan en Docker Compose y en el build del frontend.
- El script limpia un intento anterior con `docker compose down --remove-orphans` sin borrar el volumen de PostgreSQL.
- Se elimino la dependencia de un puerto API fijo en `frontend/lib/api.ts` al acceder desde otro dispositivo de la red.

## Validacion previa observada
En la ejecucion anterior, Next.js compilo correctamente, TypeScript finalizo correctamente y se generaron las 9 paginas; el unico bloqueo posterior fue la asignacion del puerto host 8100.
