import streamlit as st

import api
import config

st.title("Kardex Vivo")
st.markdown(
    "Validación automática de compras, almacén, costos y órdenes de trabajo "
    "con evidencia física de sensores IoT."
)

if api.backend_activo():
    st.success(f"Backend conectado en {config.API_URL}", icon=":material/cloud_done:")
else:
    st.error(
        f"No hay backend en {config.API_URL}. Abre otra terminal y corre "
        "`python backend_mock/servidor_mock.py` desde la carpeta del repositorio.",
        icon=":material/cloud_off:",
    )

if not config.RUTA_SIMULADOR.exists():
    st.warning(f"No se encontró el simulador IoT en {config.RUTA_SIMULADOR}.", icon=":material/sensors_off:")

st.subheader("Pantallas")
fila1 = st.columns(2)
fila2 = st.columns(2)
tarjetas = [
    (fila1[0], "paginas/recepcion.py", "Recepción", ":material/qr_code_scanner:",
     "El operador escanea el QR del bulto y la estación valida QR, presencia, peso y manipulación."),
    (fila1[1], "paginas/iot.py", "Estación IoT", ":material/sensors:",
     "Eventos del MPU6050 y la báscula en vivo, simulador con sus 7 escenarios y parámetros del detector."),
    (fila2[0], "paginas/ordenes.py", "Órdenes de trabajo", ":material/assignment:",
     "Cada fallo se convierte en una OT: revisar, confirmar o descartar con comentario."),
    (fila2[1], "paginas/dashboard.py", "Dashboard", ":material/monitoring:",
     "Calidad de datos antes y después, hallazgos, recepciones e inventario en vivo."),
]
for columna, ruta, titulo, icono, texto in tarjetas:
    with columna.container(border=True):
        st.page_link(ruta, label=titulo, icon=icono)
        st.caption(texto)

st.caption(f"Estación de esta pantalla: {config.ESTACION}")
