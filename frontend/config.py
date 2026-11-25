# Configuración del frontend de Kardex Vivo.
from pathlib import Path

# Dirección del backend. Mientras no esté el de FastAPI, es el backend_mock
# (python backend_mock/servidor_mock.py). Si corre en otra laptop, pon su IP.
# Usa 127.0.0.1 y no "localhost": en Windows, "localhost" prueba IPv6 primero y cada consulta tarda ~2 s más.
API_URL = "http://127.0.0.1:8000"

# Dirección de ESTE frontend vista desde el celular (IP de tu laptop en el hotspot).
# Streamlit la muestra como "Network URL" al arrancar. Se usa para generar los QR.
FRONT_URL = "http://192.168.1.50:8501"

# Estación de recibo que atiende esta pantalla (igual que --estacion del simulador).
ESTACION = "E1"

# Segundos que la pantalla espera el resultado (la ventana del contrato es de 20 s).
TIEMPO_ESPERA_S = 30

# Simulador de la carpeta de IoT (se lanza desde la pantalla Estación IoT y desde Recepción).
RUTA_SIMULADOR = Path(__file__).resolve().parent.parent / "Hackaton" / "iot_hackaitver" / "iot" / "simulador.py"

# Minutos que tarda una persona en validar un registro a mano (supuesto para el dashboard).
MINUTOS_VALIDACION_MANUAL = 1.5
