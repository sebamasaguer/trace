# ReciclaTrace v0.1.6 — Mobile Navigation Drawer

## Corrección principal

En pantallas de hasta 760 px el sidebar de escritorio se oculta, pero la cabecera móvil de v0.1.5 no ofrecía navegación. El resultado era que, en el celular, se veían las tarjetas de la pantalla actual pero no había forma visible de cambiar de módulo.

## Cambios

- Botón hamburguesa siempre visible en la cabecera móvil.
- Menú lateral (drawer) a pantalla completa vertical, optimizado para tacto.
- Accesos a Resumen, Empresas y QR, Recolección, Planta y pesaje y Trazabilidad.
- Resalta la sección activa.
- Muestra usuario/sesión y permite cerrar sesión.
- Cierre por botón X, toque fuera del menú, selección de una opción o tecla Escape.
- Bloqueo del scroll del fondo mientras el menú está abierto.
- Cabecera móvil sticky para que el menú permanezca accesible al desplazarse.
- Compatible con el scanner full-screen de v0.1.5; el scanner conserva mayor z-index.
- Se actualiza el encabezado de INICIAR_DEMO_MOVIL.ps1 a v0.1.6.

## Alcance

No modifica backend, PostgreSQL, tablas, QR, reglas de recolección/recepción/pesaje ni datos existentes.
