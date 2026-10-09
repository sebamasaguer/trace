# ReciclaTrace v0.1.8 - Validación de empresa en planta + QR móvil

Base requerida: v0.1.7 Planta Integrada + Reportería.

## Pesaje protegido por empresa
- El operador selecciona empresa del manifiesto **antes** del escaneo. Sin selección, el lector queda deshabilitado.
- Al leer un QR ajeno se rechaza el pesaje y se identifica la empresa propietaria, sin crear movimiento alguno.
- La API POST /api/v1/trips/{trip_id}/weighings ahora exige `company_id` positivo (empresa activa), que compara con el QR, además del viaje y color.
- La idempotencia rechaza reutilizar un identificador con otro QR o peso. El mismo intento válido se puede reintentar sin duplicar.
- Al cambiar de empresa se descarta la lectura pendiente previa con confirmación; durante el guardado se bloquea el cambio.
- Los contadores y el manifiesto de planta se filtran por empresa activa; el máximo es dinámico según retiros del viaje, sin máximo predefinido.
- Se conserva la transacción atómica de recepción+pesaje (v0.1.7), la cámara fullscreen y la reportería diaria/semanal/mensual/anual.

## Empresas en móvil
- La tabla de escritorio sigue disponible en desktop.
- En ancho <=760 px se muestran tarjetas por empresa y un botón táctil visible "Ver / imprimir 3 QR".
- El botón "Nueva empresa" y "Crear y generar 3 QR" siguen disponibles.
- En la pantalla de etiquetas se agrega un botón móvil "Imprimir o guardar como PDF".
- No se regeneran ni modifican los 3 QR permanentes de empresas existentes.

## Compatibilidad
- No requiere migración de tablas; no toca PostgreSQL ni QR impresos.
- API breaking change: clientes externos que llamen a /weighings deben enviar `company_id` explícitamente. El frontend v0.1.8 ya lo envía.
- La actualización de versión no implica certificación Docker ni dispositivo; ejecutar pruebas en Windows/celular.
