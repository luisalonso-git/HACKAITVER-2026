import streamlit as st

st.set_page_config(page_title="Kardex Vivo", page_icon=":material/inventory_2:", layout="wide")

paginas = [
    st.Page("paginas/inicio.py", title="Inicio", icon=":material/home:", default=True),
    st.Page("paginas/recepcion.py", title="Recepción", icon=":material/qr_code_scanner:",
            url_path="recepcion"),
    st.Page("paginas/iot.py", title="Estación IoT", icon=":material/sensors:", url_path="iot"),
    st.Page("paginas/ordenes.py", title="Órdenes de trabajo", icon=":material/assignment:",
            url_path="ordenes"),
    st.Page("paginas/dashboard.py", title="Dashboard", icon=":material/monitoring:",
            url_path="dashboard"),
]

st.navigation(paginas).run()
