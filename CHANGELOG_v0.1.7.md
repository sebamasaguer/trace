# ReciclaTrace v0.1.7 — Planta unificada + reportería por empresa

## Cambios funcionales

1. **Planta**: desaparece la pantalla/acción de recepción por separado. Se selecciona un viaje, se escanea el QR de una bolsa, se ingresa su peso y **Confirmar recepción y pesaje** registra ambos movimientos en **una sola transacción**.
2. **Control dinámico**: ninguna cantidad fija. Cada empresa + color + viaje admite como máximo tantos pesajes como escaneos de retiro realmente registrados. El décimo pesaje solo se admite si hay al menos 10 bolsas recolectadas. Bloqueo pesimista del QR para controlar solicitudes concurrentes.
3. **Histórico**: los registros previos de recepción separada se conservan. Si una bolsa ya fue registrada por el circuito antiguo, su próximo pesaje no genera una nueva recepción duplicada.
4. **Reportes por empresa**: día, semana (lunes–domingo), mes y año, con fecha de referencia, desglose por color/material, kilos, series temporales, exportación CSV e impresión/PDF desde el navegador.
5. **Trazabilidad**: se conserva la vista de manifiestos por viaje en su propio menú. El panel principal y el manifiesto de recolección muestran las bolsas **pesadas**, no un paso de recepción independiente.
6. **Fechas**: reportería y KPIs del tablero usan huso horario Salta (UTC−3). El conteo de retiros utiliza la fecha del retiro y el de pesos la fecha de pesaje.

## Compatibilidad

- Mismos tres QR permanentes por empresa (amarillo, verde y azul).
- **Sin migración SQL ni eliminación de tablas**; se conservan las tablas `scan_events` y `weighings`.
- Backend conserva `/trips/{id}/weighings`. El viejo POST `/trips/{id}/scan` con `stage="plant"` responde 409, indicando que el pesaje integra recepción.
- El histórico de `ScanStage.plant` se utiliza para registros de auditoría y compatibilidad. En v0.1.7 lo genera automáticamente el endpoint de pesaje cuando corresponde.
- No modificar QR, empresa, camión ni recorrido existente.

## Validación realizada

`pytest -q backend/tests/test_v017_integrado.py`: **3 PASS** contra SQLite efímero; contempla conteos variables, rechazo de excesos, misma operación repetida, compatibilidad histórica, cuatro períodos y zona horaria. Sintaxis TS/TSX validada en 15 archivos.

**Pendiente en equipo Windows**: compilación Next.js dentro de Docker, controles de sesión en celular y Golden con PostgreSQL real. La compilación final no pudo ejecutarse en este entorno por falta de resolución DNS hacia npmjs.org.

**Nota**: antes de usar Cloudflare Quick Tunnel con información real, sustituir las credenciales y secretos demostrativos y revisar permisos de exposición pública.
