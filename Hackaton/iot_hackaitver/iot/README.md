# iot/: simulador y detector (Fase 1)

Solo librería estándar de Python 3.8 o superior. No hay nada que instalar.

## Probar sin backend (ver el JSON)

```
python simulador.py --escenario normal --peso 12.5 --dry-run --rapido
```

## Probar con el backend de mentira

Terminal 1: `python mock_api.py --puerto 8000`
Terminal 2: `python simulador.py --escenario normal,golpe,peso_bajo --pausa 3`

Con el backend real, solo cambia la URL: `--api http://IP_DEL_BACKEND:8000`

## Escenarios

| Escenario | Qué emite |
|---|---|
| `normal` | presencia + peso correcto |
| `sin_presencia` | nada (el QR se escanea pero no llega ningún bulto) |
| `peso_bajo` | presencia + peso 20 % menor |
| `peso_alto` | presencia + peso 25 % mayor |
| `golpe` | presencia + golpe (3.8 g) + peso |
| `inclinado` | presencia + peso + inclinación (40°) |
| `ruidoso` | como normal, con 3 veces más ruido (muestra que el detector es robusto) |

Opciones útiles: `--peso` (peso esperado del bulto, sale de la base de datos) · `--semilla` (repetible) · `--velocidad 2` · `--rapido` · `--estacion E2`.

## Pruebas

```
python -m unittest -v
```

## Fase 2 (hardware): qué se porta

`detector.py` es una máquina de estados sin dependencias. Los umbrales están arriba del archivo y son los mismos que irán en el firmware del ESP32-C3. El ESP32 lee el MPU6050 a 100 Hz, ejecuta esa lógica y envía el mismo JSON con `"origen": "fisico"`. El peso seguirá simulado mientras no haya celda de carga, y debe declararse así.
