import pandas as pd
import streamlit as st

import api
from utils import ESTADOS_OT, PRIORIDADES_OT, TIPOS_OT

st.title("Órdenes de trabajo de validación")

if "aviso_ot" in st.session_state:
    st.success(st.session_state.pop("aviso_ot"))

try:
    ots = api.listar_ot()
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Abiertas", sum(o["estado"] == "ABIERTA" for o in ots))
c2.metric("En revisión", sum(o["estado"] == "EN_REVISION" for o in ots))
c3.metric("Prioridad alta sin cerrar",
          sum(o["prioridad"] == "ALTA" and o["estado"] != "CERRADA" for o in ots))

f1, f2, f3 = st.columns(3)
estados = f1.multiselect("Estado", ESTADOS_OT, default=["ABIERTA", "EN_REVISION"])
prioridades = f2.multiselect("Prioridad", PRIORIDADES_OT, default=PRIORIDADES_OT)
origenes = f3.multiselect("Origen", ["IOT", "CSV"], default=["IOT", "CSV"])

filtradas = [o for o in ots
             if o["estado"] in estados and o["prioridad"] in prioridades and o["origen"] in origenes]
if not filtradas:
    st.info("No hay órdenes con esos filtros.")
    st.stop()

tabla = pd.DataFrame([
    {
        "OT": o["ot_id"],
        "Prioridad": o["prioridad"],
        "Tipo": TIPOS_OT.get(o["tipo"], o["tipo"]),
        "Estado": o["estado"],
        "Origen": o["origen"],
        "Causa": o["causa"],
        "Creada": o["creada"][:16].replace("T", " "),
    }
    for o in filtradas
])
evento = st.dataframe(tabla, hide_index=True, width="stretch",
                      on_select="rerun", selection_mode="single-row", key="tabla_ot")

filas = evento.selection.rows
if not filas:
    st.caption("Selecciona una fila para ver el detalle y cambiar su estado.")
    st.stop()

ot = filtradas[filas[0]]
st.divider()
st.subheader(f"{ot['ot_id']} · {TIPOS_OT.get(ot['tipo'], ot['tipo'])}")

detalle, edicion = st.columns([3, 2])
with detalle:
    st.markdown(f"**Causa:** {ot['causa']}")
    st.markdown(f"**Prioridad:** {ot['prioridad']}  ·  **Origen:** {ot['origen']}  ·  "
                f"**Asignada a:** {ot.get('asignado_a') or 'Sin asignar'}")
    st.markdown("**Referencias**")
    st.json(ot.get("referencias") or {})
    st.markdown("**Evidencia**")
    st.json(ot.get("evidencia") or {})

with edicion:
    with st.form(f"form_{ot['ot_id']}"):
        nuevo_estado = st.selectbox("Estado", ESTADOS_OT, index=ESTADOS_OT.index(ot["estado"]))
        resolucion = st.text_area("Resolución", value=ot.get("resolucion") or "",
                                  placeholder="Qué se revisó y qué se corrigió")
        guardar = st.form_submit_button("Guardar cambios", type="primary", width="stretch")

    if guardar:
        if nuevo_estado == "CERRADA" and not resolucion.strip():
            st.error("Para cerrar la OT escribe la resolución.")
        else:
            try:
                api.actualizar_ot(ot["ot_id"], nuevo_estado, resolucion.strip() or None)
            except api.ErrorAPI as e:
                st.error(str(e))
            else:
                st.session_state.aviso_ot = f"{ot['ot_id']} actualizada a {nuevo_estado}."
                st.rerun()
