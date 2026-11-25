import pandas as pd
import streamlit as st

import api
from componentes import aviso_origen
from utils import (ESTADOS_OT, NOMBRE_ESTADO, NOMBRE_ORIGEN, PRIORIDADES_OT, TIPOS_EVENTO, TIPOS_OT,
                   hora, origen_de_ot)

st.title("Órdenes de trabajo")
st.caption("Cada fallo de una recepción o de los datos abre una OT. Una persona la confirma o la descarta.")

if "aviso_ot" in st.session_state:
    st.success(st.session_state.pop("aviso_ot"))

try:
    ots = api.listar_ot()
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Abiertas", sum(o["estado"] == "abierta" for o in ots))
c2.metric("En revisión", sum(o["estado"] == "en_revision" for o in ots))
c3.metric("Cerradas", sum(o["estado"] == "cerrada" for o in ots))
c4.metric("Prioridad alta sin cerrar", sum(o["prioridad"] == "alta" and o["estado"] != "cerrada" for o in ots))

f1, f2, f3, f4 = st.columns(4)
estados = f1.multiselect("Estado", ESTADOS_OT, default=["abierta", "en_revision"],
                         format_func=lambda e: NOMBRE_ESTADO[e])
prioridades = f2.multiselect("Prioridad", PRIORIDADES_OT, default=PRIORIDADES_OT, format_func=str.capitalize)
tipos = f3.multiselect("Tipo", list(TIPOS_OT), default=list(TIPOS_OT), format_func=lambda t: TIPOS_OT[t])
origenes = f4.multiselect("Origen", ["simulado", "fisico", "datos", "escaneo"],
                          default=["simulado", "fisico", "datos", "escaneo"],
                          format_func=lambda o: NOMBRE_ORIGEN[o])

filtradas = [o for o in ots
             if o["estado"] in estados and o["prioridad"] in prioridades
             and o["tipo"] in tipos and origen_de_ot(o) in origenes]
if not filtradas:
    st.info("No hay órdenes con esos filtros.")
    st.stop()

tabla = pd.DataFrame([{
    "OT": o["id"],
    "Prioridad": o["prioridad"].capitalize(),
    "Tipo": TIPOS_OT.get(o["tipo"], o["tipo"]),
    "Estado": NOMBRE_ESTADO.get(o["estado"], o["estado"]),
    "Origen": NOMBRE_ORIGEN.get(origen_de_ot(o)),
    "Bulto": o.get("bulto_id") or "",
    "Estación": o.get("estacion") or "",
    "Causa": o["causa"],
    "Creada": hora(o.get("creada_ts")),
} for o in filtradas])
evento = st.dataframe(tabla, hide_index=True, width="stretch",
                      on_select="rerun", selection_mode="single-row", key="tabla_ot")

filas = evento.selection.rows
if not filas:
    st.caption("Selecciona una fila para ver la evidencia y cambiar su estado.")
    st.stop()

ot = filtradas[filas[0]]
st.divider()
st.subheader(f"{ot['id']} · {TIPOS_OT.get(ot['tipo'], ot['tipo'])}")

detalle, edicion = st.columns([3, 2])
with detalle:
    st.markdown(f"**Causa:** {ot['causa']}")
    st.markdown(f"**Prioridad:** {ot['prioridad'].capitalize()}  ·  **Origen:** "
                f"{NOMBRE_ORIGEN.get(origen_de_ot(ot))}  ·  **Bulto:** {ot.get('bulto_id') or 'N/A'}  ·  "
                f"**Estación:** {ot.get('estacion') or 'N/A'}")
    st.markdown("**Evidencia**")
    evidencia = ot.get("evidencia") or []
    if evidencia:
        filas_ev = []
        for e in evidencia:
            nombre, unidad = TIPOS_EVENTO.get(e.get("tipo"), (e.get("tipo", "").capitalize(), ""))
            valor = (f"{e['magnitud']} {unidad}" if "magnitud" in e
                     else e.get("detalle") or e.get("codigo") or "")
            filas_ev.append({
                "Tipo": nombre,
                "Valor": valor,
                "Fuente": e.get("fuente") or (f"Fila {e['fila']}" if "fila" in e else ""),
                "Origen": NOMBRE_ORIGEN.get(e.get("origen"), e.get("origen")),
                "Hora": hora(e.get("ts")),
            })
        st.dataframe(pd.DataFrame(filas_ev), hide_index=True, width="stretch")
        aviso_origen(evidencia)
    else:
        st.caption("Sin eventos: la estación no reportó nada en la ventana de recepción.")
    if ot.get("cerrada_ts"):
        st.caption(f"Cerrada a las {hora(ot['cerrada_ts'])}")

with edicion:
    with st.form(f"form_{ot['id']}"):
        nuevo_estado = st.selectbox("Estado", ESTADOS_OT, index=ESTADOS_OT.index(ot["estado"]),
                                    format_func=lambda e: NOMBRE_ESTADO[e])
        comentario = st.text_area("Comentario", value=ot.get("comentario") or "",
                                  placeholder="Confirmado o descartado, y qué se corrigió")
        guardar = st.form_submit_button("Guardar cambios", type="primary", width="stretch")

    if guardar:
        if nuevo_estado == "cerrada" and not comentario.strip():
            st.error("Para cerrar la OT escribe un comentario.")
        else:
            try:
                api.actualizar_ot(ot["id"], nuevo_estado, comentario.strip() or None)
            except api.ErrorAPI as e:
                st.error(str(e))
            else:
                st.session_state.aviso_ot = f"{ot['id']} actualizada a {NOMBRE_ESTADO[nuevo_estado]}."
                st.rerun()
