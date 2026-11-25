# Configuración del frontend de Kardex Vivo.
# Cambia estos valores según tu red y el avance del backend.

# True: usa datos simulados (no necesita el backend).
# False: se conecta a la API de FastAPI en API_URL.
USAR_MOCK = True

# Dirección del backend (FastAPI). Si corre en otra laptop, pon su IP.
API_URL = "http://localhost:8000"

# Dirección de ESTE frontend vista desde el celular (IP de tu laptop en el hotspot).
# Se usa para generar los QR. Streamlit la muestra como "Network URL" al arrancar.
FRONT_URL = "http://192.168.1.50:8501"

# Estación de recepción que atiende esta pantalla.
ESTACION = "EST01"

# Segundos que la pantalla espera la lectura de la báscula antes de avisar.
TIEMPO_ESPERA_S = 60

# Minutos que tarda una persona en validar un registro a mano (supuesto para el dashboard).
MINUTOS_VALIDACION_MANUAL = 1.5
