# firmware/: estación ESP32 simulada en Wokwi

| Archivo | Qué es |
|---|---|
| `estacion_esp32/sketch.ino` | Firmware del ESP32: el detector de `Hackaton/iot_hackaitver/iot/detector.py` portado a C++ (mismos umbrales) + lectura de la báscula HX711 |
| `estacion_esp32/diagram.json` | Circuito para Wokwi: ESP32, MPU6050 (SDA 21, SCL 22) y HX711 con celda de 50 kg (DT 4, SCK 5) |
| `estacion_esp32/libraries.txt` | Librería que usa Wokwi: PubSubClient (MQTT) |
| `puente_mqtt.py` | Corre en la laptop: recibe los eventos por MQTT y los manda al backend |

## Por qué hay un puente

El ESP32 simulado en Wokwi (versión gratuita) sale a internet, pero no puede llegar a la laptop. Por eso publica
cada evento en un broker MQTT público (`broker.hivemq.com`) y `puente_mqtt.py` lo reenvía a `/api/evento`.
Con un ESP32 real en la misma red se pone `USAR_MQTT 0` y el firmware manda los eventos directo al backend.

```
ESP32 (Wokwi)  --MQTT-->  broker.hivemq.com  --MQTT-->  puente_mqtt.py  --HTTP-->  backend  -->  frontend
```

## Cómo correrlo

1. En la laptop: `python -m pip install paho-mqtt` (una vez), y con el backend encendido:
   `python firmware/puente_mqtt.py`
2. En wokwi.com: **New project → ESP32 (Arduino)**. Reemplaza `sketch.ino` y `diagram.json` con los de esta carpeta.
   En la pestaña **Library Manager** agrega **PubSubClient**.
3. Pulsa **Play**. En el monitor serie debe salir `Estación E1 lista` y cada 3 s la lectura de la báscula.

## Cómo simular una recepción

1. En el frontend, **Recepción**: escribe un bulto (por ejemplo `B-0003`, 8 kg) e inicia la recepción.
2. En Wokwi, clic en el **HX711** y pon el peso (8 kg).
3. Clic en el **MPU6050**: sube `accelZ` a 2 y regrésalo a 1 → evento de **presencia**.
4. En el frontend llegan los eventos con la etiqueta "ESP32 Wokwi" y sale el resultado.
6. Código de barras Code 128 en las etiquetas, junto al QR, para usar las pistolas lectoras USB que ya tienen los almacenes. El modo "Código o lector" de Recepción ya las acepta; solo falta imprimir el código en la etiqueta.

| Para simular | En Wokwi |
|---|---|
| Presencia | `accelZ` de 1 a 2 y de regreso a 1 |
| Golpe | `accelZ` a 4 y de regreso a 1 |
| Inclinación | `accelX` 0.7 y `accelZ` 0.7 por más de medio segundo |
| Peso | Carga del HX711 en kg |
| Peso bajo | Carga menor al peso esperado del bulto (más de 5 % abajo) |

La celda simulada llega a 50 kg: el bulto B-0001 (54 kg) se prueba con el simulador de Python;
para Wokwi usa B-0002 (30 kg), B-0003 (8 kg), B-0004 (2.4 kg), B-0005 (12 kg) o B-0006 (10 kg).

## Notas

- **Calibración:** si el monitor serie muestra un peso distinto al que pusiste en el HX711, ajusta
  `FACTOR_CALIBRACION` multiplicándolo por (peso mostrado ÷ peso puesto).
- **Red:** algunas redes escolares bloquean el puerto 1883 de MQTT. Si el puente no conecta, usa el hotspot.
- **Tópico:** el broker es público. Si aparecen eventos ajenos, cambia el tópico en `sketch.ino` y en `puente_mqtt.py`.
- **Origen:** el firmware envía `"origen": "simulado"` porque corre en un ESP32 simulado. En el ESP32 real se cambia a
  `"fisico"`. El campo extra `"dispositivo"` permite ver en pantalla qué equipo mandó cada evento.
- **Diferencia con detector.py:** se agregó un "rearme" (la aceleración debe volver al reposo antes del siguiente pico),
  porque en Wokwi el valor se queda fijo mientras no lo muevas. En el sensor real el pico dura milisegundos y no cambia nada.
