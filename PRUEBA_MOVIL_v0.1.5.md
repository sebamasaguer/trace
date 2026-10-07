# Golden Mobile — ReciclaTrace v0.1.5

Usar `INICIAR_DEMO_MOVIL.ps1` y abrir desde el celular la URL HTTPS `trycloudflare.com`.

## Caso de certificación

Recolectar para una misma empresa:

- Amarillo: 4 bolsas
- Verde: 3 bolsas
- Azul: 2 bolsas
- Total: 9 bolsas

### Recolección

Abrir `Escanear QR` una vez por bolsa. La cámara debe ocupar toda la pantalla, detectar un QR y cerrarse automáticamente.

Resultado:

```text
Amarillo 4
Verde    3
Azul     2
Total    9
```

### Planta

Confirmar exactamente las mismas cantidades.

Intentar una quinta lectura amarilla. Resultado esperado:

```text
HTTP 409 / mensaje de cupo completo
No se crea un nuevo evento
Amarillo permanece 4/4
```

Repetir el concepto para verde y azul.

### Pesaje

Registrar un peso por cada bolsa recibida.

Intentar un quinto pesaje amarillo. Resultado esperado:

```text
HTTP 409 / mensaje de cupo completo
No se crea un nuevo pesaje
Amarillo permanece 4 pesajes
```

### Criterio PASS

```text
[PASS] Cámara full-screen
[PASS] Una sesión de cámara = una lectura
[PASS] Planta amarillo <= 4
[PASS] Planta verde <= 3
[PASS] Planta azul <= 2
[PASS] Pesaje <= bolsas recibidas
[PASS] Sin incremento al recibir HTTP 409
[PASS] Dashboard/manifiesto mantienen totales correctos
```
