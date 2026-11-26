# Configuración del frontend de VigiaIot.
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

FRONT_URL = "http://192.168.1.50:8501"

ESTACION = "E1"

TIEMPO_ESPERA_S = 30

RUTA_SIMULADOR = Path(__file__).resolve().parent.parent / "Hackaton" / "iot_hackaitver" / "iot" / "simulador.py"

MINUTOS_VALIDACION_MANUAL = 1.5
