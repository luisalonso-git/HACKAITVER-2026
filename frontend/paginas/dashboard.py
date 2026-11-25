import pandas as pd
import streamlit as st

import api
import config
from utils import PRIORIDADES_OT, TIPOS_OT

NOMBRE_FUENTE = {"compras": "Compras", "almacen": "Almacén", "costos": "Costos",
                 "ot_operativas": "OT operativas"}

st.title("Calidad de datos")
st.caption("Se actualiza cada 5 segundos.")


@st.fragment(run_every=5)
def tablero():
    try:
        calidad = api.obtener_calidad()
        ots = api.listar_ot()
        inventario = api.obtener_inventario()
    except api.ErrorAPI as e:
        st.error(str(e))
        return

    g = calidad["global"]
    total = calidad["total_registros"]
    hallazgos = calidad["hallazgos"]
    horas = total * config.MINUTOS_VALIDACION_MANUAL / 60

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Índice de calidad", f"{g['despues'] * 100:.1f} %",
              delta=f"{(g['despues'] - g['antes']) * 100:+.1f} pts vs. antes", border=True)
    c2.metric("Registros analizados", f"{total:,}", border=True)
    c3.metric("Hallazgos detectados", sum(hallazgos.values()), border=True)
    c4.metric("Horas de validación manual evitadas", f"{horas:.1f} h", border=True,
              help=f"Estimado con {config.MINUTOS_VALIDACION_MANUAL} min por registro revisado a mano.")

    izq, der = st.columns(2)
    with izq:
        st.subheader("Calidad por fuente")
        df = pd.DataFrame(calidad["por_fuente"])
        df["fuente"] = df["fuente"].map(lambda f: NOMBRE_FUENTE.get(f, f))
        df = df.set_index("fuente")[["antes", "despues"]] * 100
        df.columns = ["Antes", "Después"]
        st.bar_chart(df, stack=False, y_label="% de registros válidos", x_label="",
                     color=["#B4B2A9", "#0F6E56"])
    with der:
        st.subheader("Hallazgos por tipo")
        dfh = pd.DataFrame(
            {"Hallazgos": {TIPOS_OT.get(t, t): n for t, n in hallazgos.items()}}
        ).sort_values("Hallazgos")
        st.bar_chart(dfh, horizontal=True, x_label="", y_label="", color="#0F6E56")

    izq2, der2 = st.columns(2)
    with izq2:
        st.subheader("OT sin cerrar por prioridad")
        abiertas = [o for o in ots if o["estado"] != "CERRADA"]
        dfp = pd.DataFrame(
            {"OT": {p: sum(o["prioridad"] == p for o in abiertas) for p in PRIORIDADES_OT}}
        )
        st.bar_chart(dfp, x_label="", y_label="", color="#993C1D")
    with der2:
        st.subheader("Inventario")
        dfi = pd.DataFrame(inventario).rename(columns={
            "articulo": "Artículo", "descripcion": "Descripción", "existencia": "Existencia"})
        st.dataframe(dfi, hide_index=True, width="stretch")


tablero()
