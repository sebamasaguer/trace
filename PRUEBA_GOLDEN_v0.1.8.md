# Golden ReciclaTrace v0.1.8 - controles por empresa y QR móvil

## Preparación

1. Verificá que tengas instalada v0.1.7 y acceso HTTPS del celular.
2. Crear o reutilizar empresa A y B, cada una con sus tres QR permanentes.
3. En el MISMO viaje registrar dos bolsas de A y una de B, por ejemplo amarillas.
4. Ingresar como usuario de planta.

## Caso 1: no mezclar clientes

1. Seleccionar viaje y después **Empresa A**. Debe verse el nombre claramente y la cantidad A=2.
2. Abrir escáner y leer el QR de **Empresa B**.
3. Esperado: error "EMPRESA INCORRECTA" con nombre de B. **No aparece campo de peso, no crea recepción ni pesaje**, y los contadores permanecen igual.
4. Escanear QR A, registrar peso (ej. 1.250 kg), confirmar. Debe quedar A=1/2, B=0/1.
5. Cambiar selección a B, escanear QR B y registrar peso. B debe quedar 1/1, A sin cambios.
6. Regresar a A y finalizar 2/2. Intento extra A debe ser rechazado.
7. Verificar que la reportería por empresa no mezcle kilogramos.

## Caso 2: móvil QR

1. En el teléfono ingresar con administrador y abrir Empresas y QR.
2. Comprobar que aparezcan tarjetas con **Ver / imprimir 3 QR** visibles sin desplazar horizontalmente.
3. Abrir una empresa y verificar amarillo, verde, azul; tocar **Imprimir o guardar como PDF**.
4. Comprobar que **Nueva empresa** sea visible y que al crear otra empresa se generen exactamente tres QR.

## Regresión

- Recolección ilimitada según bolsas efectivas; no límites fijos 4/3/2.
- Pesaje integrado con recepción (v0.1.7).
- Escáner fullscreen con una lectura por apertura.
- Reportería diaria, semanal, mensual y anual.
- Prueba backend: `python -m pytest backend/tests/test_v017_integrado.py -q` desde la raíz con dependencias disponibles.

No ejecutar `docker compose down -v`; elimina el volumen de PostgreSQL.
