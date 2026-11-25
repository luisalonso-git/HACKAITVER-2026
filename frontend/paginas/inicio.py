import streamlit as st

import config

st.title("Kardex Vivo")
st.markdown(
    "Validación automática de compras, almacén, costos y órdenes de trabajo "
    "con evidencia física de sensores IoT."
)

if config.USAR_MOCK:
    st.warning("Modo simulado: los datos vienen de mock_api.py, no del backend.",
               icon=":material/science:")
else:
    st.success(f"Conectado al backend en {config.API_URL}", icon=":material/cloud_done:")

st.subheader("Pantallas")
c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.page_link("paginas/recepcion.py", label="Recepción", icon=":material/qr_code_scanner:")
    st.caption("El operador escanea el QR de la remisión y la estación valida QR, presencia y peso.")
with c2.container(border=True):
    st.page_link("paginas/ordenes.py", label="Órdenes de trabajo", icon=":material/assignment:")
    st.caption("Hallazgos convertidos en OT: revisar, asignar y cerrar con resolución.")
with c3.container(border=True):
    st.page_link("paginas/dashboard.py", label="Dashboard", icon=":material/monitoring:")
    st.caption("Calidad de datos antes y después, hallazgos e inventario en vivo.")

st.caption(f"Estación: {config.ESTACION}")
