from html import escape

import pandas as pd
import streamlit as st

import api
import documentos
from componentes import aviso_origen, linea_eventos
from estilo import encabezado, html, kpis, pildora, seccion, tarjeta
from utils import ESTADOS_OT, NOMBRE_ESTADO, NOMBRE_ORIGEN, PRIORIDADES_OT, TIPOS_OT, hora, origen_de_ot

TONO_PRIORIDAD = {"alta": "rojo", "media": "ambar", "baja": "azul"}
TONO_ESTADO = {"abierta": "violeta", "en_revision": "cian", "cerrada": "verde"}

encabezado("Órdenes de trabajo", "Cada fallo de una recepción o de los datos abre una OT con su evidencia. "
           "Una persona la revisa y la confirma o la descarta.", seccion="Control")

if "aviso_ot" in st.session_state:
    st.toast(st.session_state.pop("aviso_ot"), icon=":material/check_circle:")

try:
    ots = api.listar_ot()
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()

abiertas = sum(o["estado"] == "abierta" for o in ots)
revision = sum(o["estado"] == "en_revision" for o in ots)
cerradas = sum(o["estado"] == "cerrada" for o in ots)
altas = sum(o["prioridad"] == "alta" and o["estado"] != "cerrada" for o in ots)
kpis([
    {"etiqueta": "Abiertas", "valor": abiertas, "icono": "orden", "acento": "violeta", "pie": "esperando revisión"},
    {"etiqueta": "En revisión", "valor": revision, "icono": "reloj", "acento": "cian", "pie": "alguien las atiende"},
    {"etiqueta": "Cerradas", "valor": cerradas, "icono": "check", "acento": "verde",
     "pie": f"{cerradas / len(ots) * 100:.0f} % del total" if ots else ""},
    {"etiqueta": "Prioridad alta sin cerrar", "valor": altas, "icono": "alerta", "acento": "rojo",
     "pie": "atender primero" if altas else "nada urgente", "tendencia": "-" if altas else "+"},
])

with tarjeta("filtros"):
    f1, f2, f3, f4 = st.columns(4)
    estados = f1.multiselect("Estado", ESTADOS_OT, default=["abierta", "en_revision"],
                             format_func=lambda e: NOMBRE_ESTADO[e])
    prioridades = f2.multiselect("Prioridad", PRIORIDADES_OT, default=PRIORIDADES_OT, format_func=str.capitalize)
    tipos = f3.multiselect("Tipo", list(TIPOS_OT), default=list(TIPOS_OT), format_func=lambda t: TIPOS_OT[t])
    origenes = f4.multiselect("Origen", ["simulado", "fisico", "datos", "escaneo"],
                              default=["simulado", "fisico", "datos", "escaneo"], format_func=lambda o: NOMBRE_ORIGEN[o])

filtradas = [o for o in ots if o["estado"] in estados and o["prioridad"] in prioridades
             and o["tipo"] in tipos and origen_de_ot(o) in origenes]
if not filtradas:
    st.info("No hay órdenes con esos filtros.", icon=":material/filter_alt_off:")
    st.stop()

orden_prioridad = {"alta": 0, "media": 1, "baja": 2}
filtradas.sort(key=lambda o: (o["estado"] == "cerrada", orden_prioridad.get(o["prioridad"], 3)))
tabla = pd.DataFrame([{
    "OT": o["id"],
    "Prioridad": o["prioridad"].upper(),
    "Tipo": TIPOS_OT.get(o["tipo"], o["tipo"]),
    "Estado": NOMBRE_ESTADO.get(o["estado"], o["estado"]),
    "Origen": NOMBRE_ORIGEN.get(origen_de_ot(o)),
    "Bulto": o.get("bulto_id") or "—",
    "Causa": o["causa"],
    "Creada": hora(o.get("creada_ts")),
} for o in filtradas])

cab_bandeja, boton_bandeja = st.columns([3, 1], vertical_alignment="bottom")
with cab_bandeja:
    seccion("Bandeja", "orden", nota=f"{len(filtradas)} órdenes · selecciona una para ver el detalle")
boton_bandeja.download_button("Exportar bandeja", data=documentos.csv_bandeja(filtradas), file_name="ordenes_de_trabajo.csv",
                              mime="text/csv", icon=":material/table_view:", width="stretch")
evento = st.dataframe(
    tabla, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(tabla)),
    on_select="rerun", selection_mode="single-row", key="tabla_ot",
    column_config={
        "OT": st.column_config.TextColumn(width="small"),
        "Prioridad": st.column_config.TextColumn(width="small"),
        "Causa": st.column_config.TextColumn(width="large"),
        "Creada": st.column_config.TextColumn(width="small"),
    },
)

filas = evento.selection.rows
if not filas:
    st.stop()

ot = filtradas[filas[0]]
detalle, edicion = st.columns([1.6, 1], gap="large")
with detalle:
    with tarjeta("detalle_ot"):
        html(f'<div style="display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin-bottom:.6rem">'
             f'<span class="kv-mono" style="font-size:1.15rem;font-weight:600">{escape(ot["id"])}</span>'
             f'{pildora(TIPOS_OT.get(ot["tipo"], ot["tipo"]), "violeta")}'
             f'{pildora("Prioridad " + ot["prioridad"], TONO_PRIORIDAD.get(ot["prioridad"], "azul"))}'
             f'{pildora(NOMBRE_ESTADO.get(ot["estado"], ot["estado"]), TONO_ESTADO.get(ot["estado"], "azul"))}</div>'
             f'<div style="font-size:.98rem;margin-bottom:.8rem">{escape(ot["causa"])}</div>'
             f'<div class="kv-tenue">Origen: {NOMBRE_ORIGEN.get(origen_de_ot(ot))} · Bulto: {escape(ot.get("bulto_id") or "N/A")}'
             f' · Estación: {escape(ot.get("estacion") or "N/A")} · Creada {hora(ot.get("creada_ts"))}'
             f'{" · Cerrada " + hora(ot["cerrada_ts"]) if ot.get("cerrada_ts") else ""}</div>')
        seccion("Evidencia", "actividad")
        evidencia = ot.get("evidencia") or []
        sensores = [e for e in evidencia if "magnitud" in e]
        registros = [e for e in evidencia if "magnitud" not in e]
        if sensores:
            linea_eventos(sensores)
            aviso_origen(sensores)
        for e in registros:
            fuente = e.get("fuente") or e.get("origen", "")
            fila = f" · línea {e['fila']}" if "fila" in e else ""
            html(f'<div class="kv-evento" style="--kv-color:var(--kv-violeta);padding-left:1.1rem">'
                 f'<span class="kv-tipo">{escape(str(fuente))}{fila}</span>'
                 f'<span class="kv-tenue" style="margin-left:.4rem">{escape(str(e.get("detalle") or e.get("codigo") or ""))}</span></div>')
        if not evidencia:
            html('<div class="kv-tenue">Sin eventos: la estación no reportó nada en la ventana de recepción.</div>')

with edicion:
    with tarjeta("descargar_ot"):
        seccion("Documento", "descarga")
        if documentos.HAY_PDF:
            st.download_button("Descargar orden de trabajo (PDF)", data=documentos.pdf_orden(ot),
                               file_name=documentos.nombre_archivo(ot), mime="application/pdf",
                               icon=":material/picture_as_pdf:", type="primary", width="stretch", key=f"pdf_{ot['id']}")
            st.caption("Incluye datos, causa, evidencia, resolución y espacio para firmas.")
        else:
            st.warning("Para el PDF instala reportlab: `python -m pip install reportlab`")
    with tarjeta("editar_ot"):
        seccion("Resolución", "check")
        with st.form(f"form_{ot['id']}", border=False):
            nuevo_estado = st.segmented_control("Estado", ESTADOS_OT, default=ot["estado"],
                                                format_func=lambda e: NOMBRE_ESTADO[e])
            comentario = st.text_area("Comentario", value=ot.get("comentario") or "", height=110,
                                      placeholder="Confirmado o descartado, y qué se corrigió")
            guardar = st.form_submit_button("Guardar cambios", type="primary", width="stretch",
                                            icon=":material/save:")
        if guardar:
            nuevo_estado = nuevo_estado or ot["estado"]
            if nuevo_estado == "cerrada" and not comentario.strip():
                st.error("Para cerrar la OT escribe un comentario.")
            else:
                try:
                    api.actualizar_ot(ot["id"], nuevo_estado, comentario.strip() or None)
                except api.ErrorAPI as e:
                    st.error(str(e))
                else:
                    st.session_state.aviso_ot = f"{ot['id']} actualizada a {NOMBRE_ESTADO[nuevo_estado]}"
                    st.rerun()
