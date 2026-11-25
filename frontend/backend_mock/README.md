# backend_mock: backend de integración

Implementa `Hackaton/CONTRATO.md` completo (secciones 1 a 6) solo con la librería estándar de Python,
para que frontend, simulador IoT y reglas funcionen juntos mientras se termina el backend en FastAPI.

```
python servidor_mock.py            # puerto 8000
python servidor_mock.py --silencio 4 --ventana 20
```

`GET /api/series?rango=1h|24h|7d|30d` alimenta las gráficas: incluye 30 días de historial SIMULADO
(marcado como tal) más la actividad real de la sesión.

Los datos viven en memoria: al reiniciar el servidor se borran recepciones, eventos y OT.

Para la persona 1: las funciones `evaluar()` (chequeos, prioridad y OT) y `calidad()` son la referencia
de lo que espera el frontend. Las OT de los CSV (`sembrar_ot_datos`) y `CALIDAD_CSV` son de ejemplo
hasta que la persona 2 conecte la limpieza real.

Es compatible con el simulador sin cambios:
```
cd Hackaton/iot_hackaitver/iot
python simulador.py --escenario golpe --peso 3.0
```
