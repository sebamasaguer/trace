# ReciclaTrace — MVP funcional para presentación (v0.1.5)

Plataforma full-stack de trazabilidad de reciclaje basada en **3 QR permanentes por empresa**: amarillo, verde y azul. Cada escaneo representa una bolsa y genera un evento auditable. El sistema controla retiro, manifiesto del camión, recepción en planta, conciliación y pesaje individual.

## Stack

- **Frontend:** Next.js 16 + React 19 + TypeScript + PWA-ready UI responsive.
- **Backend:** FastAPI + SQLAlchemy 2 + JWT.
- **Base de datos:** PostgreSQL 16.
- **QR:** tokens firmados y QR imprimibles.
- **Escaneo:** cámara full-screen con ZXing, una lectura por sesión + ingreso manual alternativo.
- **Infraestructura:** Docker Compose.
- **Móvil:** API same-origin vía reverse proxy Next.js + HTTPS temporal mediante Cloudflare Quick Tunnel.

## Inicio rápido

Requisito: Docker Desktop o Docker Engine con Compose.

```bash
docker compose up --build
```

Abrir:

- Frontend: http://localhost:3210
- API / Swagger: http://localhost:8210/docs
- Health: http://localhost:8210/health


## Prueba real desde celular (recomendada)

Para probar la cámara del teléfono, no uses `localhost` ni una IP HTTP de la LAN. Ejecutá:

```powershell
.\INICIAR_DEMO_MOVIL.ps1
```

El script mostrará una URL temporal HTTPS del tipo:

```text
https://xxxxx.trycloudflare.com
```

Abrí esa dirección en Chrome/Safari del celular. La URL es pública y temporal; al terminar ejecutá `./DETENER_DEMO.ps1`. Ver `PRUEBA_MOVIL.md` para el Golden Test móvil.

Desde v0.1.4 el navegador consume `/api/v1` por el mismo origen y Next.js reenvía internamente las llamadas a FastAPI. El celular no necesita conocer IP ni puerto del backend. Desde v0.1.5 el scanner móvil es full-screen y cada sesión acepta una sola lectura para evitar duplicados accidentales del mismo QR permanente.

Los QR impresos contienen un token firmado independiente de host/puerto. Los QR impresos en versiones anteriores, que incluían `/q/<token>`, siguen siendo aceptados por el backend.

### Usuarios demo

| Perfil | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin123!` |
| Recolector | `recolector` | `Recolector123!` |
| Planta | `planta` | `Planta123!` |

> El proyecto se entrega con claves de demostración. Para producción deben cambiarse el `SECRET_KEY`, contraseñas, políticas de CORS y credenciales de PostgreSQL.

## Guion recomendado para la presentación

1. Ingresar como `admin`.
2. Ir a **Empresas y QR**.
3. Crear una empresa. El backend crea automáticamente sus **3 QR permanentes**.
4. Abrir **Ver / imprimir** y mostrar las tres etiquetas por color.
5. Ir a **Recolección**, crear un viaje indicando camión y recolector.
6. Escanear varias veces un QR: cada lectura suma una bolsa al manifiesto.
7. Ir a **Planta y pesaje** y seleccionar el mismo viaje.
8. Volver a escanear las bolsas para confirmar recepción.
9. Escanear una bolsa en la sección de pesaje e ingresar sus kilos.
10. Ir a **Trazabilidad** y mostrar la conciliación retiro ↔ planta ↔ pesaje.

## Regla funcional central

El QR **no identifica una bolsa única**. Identifica:

`EMPRESA + COLOR / MATERIAL`

Por eso un cliente imprime copias ilimitadas de sus tres códigos. Cada lectura crea un evento independiente. Para evitar duplicados de red sin impedir escaneos repetidos legítimos, el frontend envía un `client_event_id` único por lectura.

## Colores iniciales

- Amarillo → Plásticos
- Verde → Vidrio
- Azul → Papel / Cartón

La arquitectura permite convertir estas categorías en parametrizables en una siguiente etapa.

## Controles implementados

- JWT y perfiles de administrador, recolector y planta.
- QR firmados para impedir modificación manual del contenido.
- Tres QR únicos por empresa y color.
- Escaneos repetidos válidos del mismo QR.
- Idempotencia por evento para evitar duplicación por reintentos de red.
- Manifiesto digital por viaje.
- Límite duro y concurrente: planta no puede recibir más bolsas de las declaradas para cada empresa+color.
- Límite duro y concurrente: no se pueden pesar más bolsas que las recibidas (ni, por lo tanto, más que las recolectadas).
- Scanner móvil full-screen: una apertura de cámara registra como máximo una bolsa.
- Conciliación automática de cantidades.
- Totalización de kilos por empresa y color.
- Dashboard operativo.
- Etiquetas listas para impresión.
- API documentada con OpenAPI/Swagger.

## Estructura

```text
recicla-trace/
├── backend/
│   └── app/
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── security.py
│       ├── qr_service.py
│       └── routers/
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
├── docker-compose.yml
├── docker-compose.mobile.yml
├── INICIAR_DEMO_MOVIL.ps1
└── PRUEBA_MOVIL.md
```

## Evolución a producción

Para pasar del MVP de presentación a producción se recomienda agregar: Alembic para migraciones versionadas; almacenamiento de auditoría append-only; refresh tokens o integración SSO; HTTPS/reverse proxy; observabilidad; copias de seguridad; modo offline con cola local; sincronización controlada; catálogo configurable de residuos; integración con balanza; geolocalización opcional de recorridos; certificados PDF y firma digital; multi-sucursal; métricas y alertas.

## Cambios v0.1.7 — Planta y reportes

- **Planta**: escanear QR → cargar peso → confirmar. En una misma confirmación se reciben y pesan las bolsas. La pantalla no tiene una etapa de recepción separada.
- **Reportes por empresa** (`/reports`): filtro empresa y día, semana (lunes a domingo), mes o año. Vista por colores y evolución temporal, exportación CSV e impresión/PDF.
- **Trazabilidad por viaje** (`/tracing`): comparación contra lo recolectado.
- Los reportes aplican hora oficial de Salta, UTC−3. Las cantidades recolectadas y pesadas se agrupan por su propia fecha de operación.
- Sin migración de base de datos. El histórico de recepciones de versiones anteriores permanece disponible.

Para iniciar desde el celular: `./INICIAR_DEMO_MOVIL.ps1` en PowerShell (`\.\INICIAR_DEMO_MOVIL.ps1`). El túnel público es exclusivamente para la demostración con datos de prueba.


## v0.1.8 - Control por empresa

Seleccionar una empresa al iniciar el pesaje; los QR de otras empresas se rechazan en la API. Las acciones QR se muestran como tarjetas en pantallas móviles. Ver `PRUEBA_GOLDEN_v0.1.8.md`.
