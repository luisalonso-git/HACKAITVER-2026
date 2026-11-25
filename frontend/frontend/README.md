# Kardex Vivo · Frontend (Streamlit)

Cinco pantallas: **Resumen**, **Recepción** (operador), **Estación IoT**, **Órdenes de trabajo** y **Calidad de datos**,
con tema oscuro tipo SaaS, gráficas interactivas (Plotly) con rangos de 1 h, 24 h, 7 d y 30 d, y diseño adaptable a celular.
Sigue el contrato del equipo: `Hackaton/CONTRATO.md` (secciones 1 a 5, más la 6 con lo que agrega el frontend).

## Arranque (dos terminales, desde la carpeta del repositorio)

Terminal 1, backend de integración (mientras no esté el de FastAPI):
```
python backend_mock/servidor_mock.py
```

Terminal 2, frontend:
```
cd frontend
python -m streamlit run app.py
```

Instalación, solo una vez (incluye Plotly para las gráficas): `python -m pip install -r frontend/requirements.txt`

## Qué cubre de la carpeta IoT

| Función de `Hackaton/iot_hackaitver/iot` | Dónde se ve en el frontend |
|---|---|
| `simulador.py`: 7 escenarios | Recepción (panel de demo) y Estación IoT (todos, en secuencia) |
| Opciones `--peso --estacion --velocidad --ruido --semilla --pausa` | Formulario de Estación IoT |
| Eventos `presencia`, `peso`, `golpe`, `inclinacion` | Recepción (en vivo), Estación IoT (contadores y tabla), evidencia de cada OT |
| Campo `origen` (simulado / físico), obligatorio mostrarlo | Avisos en Recepción y OT, contadores en Estación IoT, gráfica en Dashboard |
| `detector.py`: umbrales del ESP32 | Estación IoT, sección de parámetros del detector |
| Chequeo de manipulación (golpe o inclinación) | Cuarto chequeo en Recepción; OT de tipo inspección |

## Demo rápida

1. Recepción: escribe `B-0001`, pulsa **Iniciar recepción**.
2. Abre **Simular la llegada del bulto**, elige un escenario y pulsa **Enviar eventos del simulador**.
3. Mira llegar los eventos y llenarse los 4 chequeos; en unos 7 segundos sale el resultado.
4. Ve a Órdenes de trabajo para revisar y cerrar las OT. El Dashboard se actualiza solo.

| Escenario | Resultado esperado |
|---|---|
| normal, ruidoso | OK |
| peso_bajo, peso_alto | Peso falla, OT cantidad_distinta |
| golpe | Manipulación falla, OT inspección de prioridad alta |
| inclinado | Manipulación falla, OT inspección |
| sin_presencia | Presencia y peso fallan a los 20 s, dos OT |
| B-0001 escaneado dos veces | QR falla, OT duplicado |
| B-9999 | QR falla, OT dato_incompleto |

## Celular

Todos en la misma red (hotspot del equipo). Copia la `Network URL` de Streamlit en `FRONT_URL` de `config.py`
y corre `python generar_qr.py` (con el backend encendido). Al escanear el QR con la cámara se abre
la pantalla de recepción con el código cargado. Si no abre, permite Python en el firewall (red privada).

## Cambiar al backend real

En `config.py`, `API_URL = "http://IP-del-backend:8000"`. El backend debe responder como indica
`Hackaton/CONTRATO.md` (incluida la sección 6). Streamlit llama a la API desde Python, así que no hace falta CORS.

## Estructura

| Archivo | Qué hace |
|---|---|
| `app.py` | Menú y navegación |
| `config.py` | URL del backend, IP del frontend, estación, ruta del simulador |
| `api.py` | Única puerta hacia el backend y el simulador |
| `estilo.py` | Sistema visual: paleta, CSS, iconos, tarjetas, indicadores, encabezados |
| `graficas.py` | Gráficas Plotly con el tema: líneas, barras, dona, medidor y selector de rango |
| `componentes.py` | Chequeos, línea de eventos y avisos de origen que comparten las pantallas |
| `assets/` | Logo e icono |
| `utils.py` | Nombres del contrato (tipos de OT, eventos, escenarios) |
| `paginas/*.py` | Las pantallas |
| `generar_qr.py` | QR con URL para la cámara del celular |
