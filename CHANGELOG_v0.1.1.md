# ReciclaTrace v0.1.1 — puertos y build frontend

Cambios respecto del MVP inicial:

- Frontend: puerto `3100`.
- Backend/API: puerto `8100`.
- Docker Compose, Dockerfiles, CORS, URL pública, frontend API URL, scripts PowerShell y documentación actualizados.
- Corregido el `useEffect(load, [])` de `frontend/app/companies/page.tsx` para que el callback de React no retorne una `Promise`, resolviendo el error de type-check observado durante `next build`.
- Eliminado `tsconfig.tsbuildinfo` del paquete para forzar una comprobación TypeScript limpia al reconstruir.

Accesos de demo:

- Aplicación: http://localhost:3100
- Swagger: http://localhost:8100/docs
- Health: http://localhost:8100/health

> Sustituida por v0.1.2 para resolver automaticamente colisiones de puertos del host.
