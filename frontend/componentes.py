"""Piezas visuales que comparten varias pantallas."""
import pandas as pd
import streamlit as st

from utils import CHEQUEOS, NOMBRE_ORIGEN, TIPOS_EVENTO, hora

ESTILO_CHECK = {
    "OK": ("Correcto", "green", ":material/check:"),
    "FALLO": ("Falló", "red", ":material/close:"),
    "PENDIENTE": ("Esperando", "gray", ":material/hourglass_empty:"),
}


def mostrar_checks(checks):
    columnas = st.columns(len(CHEQUEOS))
    for columna, (llave, nombre) in zip(columnas, CHEQUEOS):
        texto, color, icono = ESTILO_CHECK.get(checks.get(llave, "PENDIENTE"), ESTILO_CHECK["PENDIENTE"])
        with columna.container(border=True):
            st.markdown(f"**{nombre}**")
            st.badge(texto, color=color, icon=icono)


def tabla_eventos(eventos, mostrar_estacion=False, vacio="Todavía no llegan eventos de la estación."):
    if not eventos:
        st.caption(vacio)
        return
    filas = []
    for e in eventos:
        nombre, unidad = TIPOS_EVENTO.get(e.get("tipo"), (e.get("tipo"), ""))
        fila = {
            "Hora": hora(e.get("ts")),
            "Evento": nombre,
            "Magnitud": f"{e.get('magnitud')} {unidad}",
            "Origen": NOMBRE_ORIGEN.get(e.get("origen"), e.get("origen")),
        }
        if mostrar_estacion:
            fila = {"Estación": e.get("estacion"), **fila}
        filas.append(fila)
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


def aviso_origen(eventos):
    """El contrato pide mostrar siempre si los datos son simulados o físicos."""
    origenes = {e.get("origen") for e in eventos}
    if "simulado" in origenes:
        st.caption(":orange[Datos de sensor SIMULADOS (peso simulado: aún no hay celda de carga).]")
    if "fisico" in origenes:
        st.caption(":green[Incluye datos de sensor FÍSICO (ESP32 + MPU6050).]")
