# ReciclaTrace v0.1.5 — Hard Limits + Scanner Full Screen

## Objetivo

Cerrar dos riesgos funcionales detectados durante la prueba móvil real:

1. Planta y pesaje no pueden superar las cantidades habilitadas por el manifiesto.
2. La cámara deja de estar embebida dentro de la página y pasa a un escáner móvil de pantalla completa.

## Reglas duras de cantidad

- **Recepción en planta:** por cada `EMPRESA + COLOR`, `plant_count` nunca puede superar `pickup_count`.
- **Pesaje:** por cada `EMPRESA + COLOR`, `weighed_count` nunca puede superar las bolsas efectivamente recibidas en planta y, por definición, tampoco puede superar las recolectadas.
- Si el cupo está completo, la API responde HTTP `409` y no inserta ningún evento adicional.
- Se agregó bloqueo pesimista de PostgreSQL (`SELECT ... FOR UPDATE`) sobre la etiqueta `EMPRESA + COLOR` para impedir carreras cuando dos celulares intentan registrar al mismo tiempo.
- La idempotencia por `client_event_id` se conserva.

Ejemplo esperado:

```text
Recolector
Amarillo 4
Verde    3
Azul     2

Planta
Amarillo máximo 4
Verde    máximo 3
Azul     máximo 2

Pesaje
Amarillo máximo 4 pesajes
Verde    máximo 3 pesajes
Azul     máximo 2 pesajes
```

## Scanner móvil

- El video ya no aparece dentro de la tarjeta de la página.
- `Escanear QR` abre una cámara **full-screen**.
- Se prioriza la cámara trasera.
- El QR se detecta automáticamente.
- Una sesión de cámara acepta **una sola lectura** y se cierra después de detectar el QR.
- Se conserva ingreso manual como contingencia.

### Decisión sobre el botón "Capturar"

No se agrega un botón de captura dentro de la cámara. Es intencional.

Como los QR son permanentes por `EMPRESA + COLOR`, varias bolsas tienen exactamente el mismo código. Un lector continuo podría volver a leer la misma bolsa si permanece en cuadro. En v0.1.5, el botón `Escanear QR` abre la sesión, ZXing detecta un único QR y la cámara se cierra: **una apertura = una bolsa**.

Un botón adicional `Capturar` obligaría a congelar/extraer un frame y decodificar esa imagen, agregaría otro toque y puede empeorar la lectura con movimiento, autofocus o poca luz. Para este flujo, la detección automática de una sola lectura por sesión es más simple y robusta.

## UI de planta

- Indicador `Recibidas / Recolectadas`.
- Indicador `Pesadas / Recibidas`.
- Recepción se bloquea visualmente cuando llega al total del viaje.
- Pesaje se bloquea visualmente cuando no quedan bolsas recibidas pendientes.
- El backend sigue siendo la autoridad final por empresa y color.

## Compatibilidad

- Sin cambios de esquema de base de datos.
- Sin migración.
- Conserva los QR ya impresos.
- Conserva datos existentes.
- Compatible con el HTTPS móvil de v0.1.4.
