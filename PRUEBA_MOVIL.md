# ReciclaTrace v0.1.4 — Prueba móvil HTTPS

## Objetivo
Probar el flujo real con la cámara del celular sin depender de `localhost`, IP local ni CORS.

## Arranque
En PowerShell 5.1, dentro de la carpeta del proyecto:

```powershell
.\INICIAR_DEMO_MOVIL.ps1
```

El script levanta PostgreSQL, FastAPI, Next.js y un **Cloudflare Quick Tunnel** temporal. Al finalizar muestra una dirección del tipo:

```text
https://xxxxx.trycloudflare.com
```

Abrí **esa URL HTTPS en el celular**. No uses `localhost` y, para la cámara, no uses una dirección `http://192.168...`.

## Login móvil
- Recolector: `recolector` / `Recolector123!`
- Planta: `planta` / `Planta123!`
- Administrador: `admin` / `Admin123!`

## Golden móvil sugerido
1. Desde la PC, entrar como administrador y abrir `Empresas y QR`.
2. Imprimir o mostrar en otra pantalla los tres QR de una empresa.
3. En el celular, abrir la URL HTTPS e ingresar como `recolector`.
4. Crear/seleccionar un viaje y escanear el mismo QR amarillo 3 veces, verde 2 veces y azul 1 vez.
5. Cerrar sesión y entrar como `planta` (o usar un segundo celular).
6. Recibir 2 amarillas, 2 verdes y 1 azul; comprobar diferencia de 1 amarilla.
7. Escanear la tercera amarilla y comprobar diferencia 0.
8. Intentar una cuarta amarilla y verificar que el sistema la rechace.
9. Registrar pesos y verificar totalización/dashboard.

## Cámara
El hotfix solicita preferentemente la cámara trasera (`facingMode: environment`) y verifica que el navegador esté en contexto seguro HTTPS antes de intentar abrirla.

## Arquitectura móvil
El navegador consume siempre `/api/v1` en el mismo origen. Next.js actúa como reverse proxy hacia `backend:8100` dentro de Docker. El celular nunca necesita conocer el puerto interno del backend.

## QR permanentes
Desde v0.1.4 el contenido físico de cada QR es el **token firmado permanente** de la etiqueta. No contiene `localhost`, IP, puerto ni la URL temporal del túnel. Por lo tanto las tres etiquetas del cliente no cambian al reiniciar la demo.

## Seguridad de la demo
La URL `trycloudflare.com` es pública y temporal. Cerrá el túnel al terminar:

```powershell
.\DETENER_DEMO.ps1
```

No es el mecanismo de publicación recomendado para producción; se usa exclusivamente para la presentación/prueba móvil.
