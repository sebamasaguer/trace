# ReciclaTrace v0.1.4 — Hotfix Mobile HTTPS

- API del navegador cambiada a origen relativo `/api/v1`.
- Reverse proxy de Next.js hacia `http://backend:8100/api/v1`.
- Eliminada la dependencia del navegador respecto de `localhost:8210`.
- Nuevo `docker-compose.mobile.yml` con Cloudflare Quick Tunnel para HTTPS temporal.
- Nuevo `INICIAR_DEMO_MOVIL.ps1`, compatible con Windows PowerShell 5.1.
- Escáner móvil solicita preferentemente la cámara trasera.
- Mensaje explícito cuando la cámara se intenta usar fuera de HTTPS.
- QR físicos desacoplados de host/puerto: ahora contienen el token firmado permanente.
- Backend identificado como `0.1.4-demo`.
- Frontend identificado como `0.1.4`.
