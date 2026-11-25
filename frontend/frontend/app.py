from pathlib import Path

import streamlit as st

from estilo import aplicar_estilo

RAIZ = Path(__file__).parent

st.set_page_config(page_title="Kardex Vivo", page_icon=str(RAIZ / "assets" / "icono.svg"), layout="wide",
                   initial_sidebar_state="expanded")
st.logo(str(RAIZ / "assets" / "logo.svg"), icon_image=str(RAIZ / "assets" / "icono.svg"), size="large")
aplicar_estilo()

paginas = {
    "Operación": [
        st.Page("paginas/inicio.py", title="Resumen", icon=":material/space_dashboard:", default=True),
        st.Page("paginas/recepcion.py", title="Recepción", icon=":material/qr_code_scanner:", url_path="recepcion"),
        st.Page("paginas/iot.py", title="Estación IoT", icon=":material/sensors:", url_path="iot"),
    ],
    "Control": [
        st.Page("paginas/ordenes.py", title="Órdenes de trabajo", icon=":material/assignment:", url_path="ordenes"),
        st.Page("paginas/dashboard.py", title="Calidad de datos", icon=":material/monitoring:", url_path="dashboard"),
    ],
}

st.navigation(paginas).run()
