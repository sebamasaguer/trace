# GOLDEN v0.1.7 — ReciclaTrace (prueba PC + móvil)

## Preflight

1. Confirmar que Docker Desktop esté iniciado.
2. Instalar hotfix **sobre código local v0.1.6**; el instalador hace backup y no modifica PostgreSQL.
3. Iniciar `./INICIAR_DEMO_MOVIL.ps1` (en PowerShell `\.\INICIAR_DEMO_MOVIL.ps1`). Usar la **nueva** URL HTTPS `trycloudflare.com`.
4. Verificar `/health` por `http://localhost:8210/health` o puerto elegido, la versión esperada es `0.1.7-demo`.

## Escenario principal

- Con admin, elegir empresa Demo, imprimir o mostrar sus **3 QR permanentes**.
- Como recolector, crear viaje de prueba y escanear el amarillo 4 veces, verde 3, azul 2 (solo valores de muestra, sin cantidad máxima fija).
- Como planta, seleccionar viaje. **No debe existir la sección de recepción separada**.
- Escanear QR amarillo → escribir `2.400` kg → **Confirmar recepción y pesaje**. Repetir todas las bolsas; observar contador y total por color.
- Intentar un quinto pesaje amarillo: debe rechazarlo aunque haya bolsas verdes y azules pendientes.
- Probar con otro viaje que tenga 12 bolsas amarillas: permite 12, nunca un máximo universal de 4.
- Confirmar que dos lecturas repetidas de un mismo QR no se registran sin un nuevo clic de Confirmar peso.
- En **Reportes por empresa**, seleccionar empresa, probar Día / Semanal / Mensual / Anual. Verificar kilos y cantidades, CSV y la impresión/PDF.
- En **Trazabilidad**, verificar el manifiesto por viaje y la relación retiro vs. pesaje.
- Volver a cargar página y revisar que los datos persistan.

## Criterios de aceptación

- [ ] Menú móvil y cámara pantalla completa funcionan.
- [ ] Planta no tiene escaneo de recepción independiente.
- [ ] Confirmar peso crea una recepción y un pesaje en el backend.
- [ ] No se supera la cantidad recolectada por empresa + color + viaje.
- [ ] Misma confirmación reintentada no duplica la bolsa.
- [ ] Las fechas del reporte corresponden al huso de Salta.
- [ ] Descarga CSV con desglose de empresa y color.
- [ ] No se perdieron datos de la versión anterior.

**Regla de interpretación de reportes**: recolecciones y pesajes se atribuyen a sus respectivas fechas, por eso el recuento diario de retiros puede ser distinto del diario de pesajes sin significar un error de trazabilidad.
