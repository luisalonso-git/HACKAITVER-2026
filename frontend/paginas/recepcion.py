import time

import streamlit as st

import api
import config
from utils import interpretar_qr

ESTILO_CHECK = {
    "OK": ("Correcto", "green", ":material/check:"),
    "FALLO": ("Falló", "red", ":material/close:"),
    "PENDIENTE": ("Esperando", "gray", ":material/hourglass_empty:"),
}
NOMBRE_CHECK = {"qr": "QR válido", "presencia": "Presencia", "peso": "Peso"}
LLAVES_SESION = ["recepcion_id", "recepcion_qr", "recepcion_inicio", "recepcion_desc", "recepcion_final"]


def reiniciar():
    for llave in LLAVES_SESION:
        st.session_state.pop(llave, None)
    st.query_params.clear()


def mostrar_checks(checks):
    columnas = st.columns(3)
    for columna, llave in zip(columnas, ["qr", "presencia", "peso"]):
        texto, color, icono = ESTILO_CHECK[checks.get(llave, "PENDIENTE")]
        with columna.container(border=True):
            st.markdown(f"**{NOMBRE_CHECK[llave]}**")
            st.badge(texto, color=color, icon=icono)


@st.fragment(run_every=2)
def seguimiento():
    """Consulta el estado cada 2 s hasta que el backend responda OK o SOSPECHOSO."""
    try:
        rec = api.obtener_recepcion(st.session_state.recepcion_id)
    except api.ErrorAPI as e:
        st.warning(f"Sin respuesta del servidor, reintentando. {e}")
        return

    if rec["estado"] != "PENDIENTE":
        st.session_state.recepcion_final = rec
        st.rerun()

    transcurrido = time.time() - st.session_state.recepcion_inicio
    if transcurrido > config.TIEMPO_ESPERA_S:
        st.warning("La báscula no envió lectura a tiempo. Revisa la estación o cancela la recepción.")
    else:
        st.info("Coloca el material en la báscula y espera la validación.", icon=":material/scale:")
        st.progress(transcurrido / config.TIEMPO_ESPERA_S,
                    text=f"Esperando lectura de la estación ({int(transcurrido)} s)")
    mostrar_checks(rec["checks"])

    if st.button("Cancelar recepción"):
        reiniciar()
        st.rerun()


def mostrar_resultado(rec):
    if rec["estado"] == "OK":
        st.success("Recepción correcta. La entrada se registró en almacén automáticamente.",
                   icon=":material/check_circle:")
    else:
        st.error("Recepción sospechosa. Se abrió una orden de trabajo para revisión.",
                 icon=":material/error:")

    mostrar_checks(rec["checks"])

    calculada = rec.get("cantidad_calculada") or 0
    esperada = rec.get("cantidad_esperada")
    c1, c2, c3 = st.columns(3)
    c1.metric("Peso medido", f"{(rec.get('peso_kg') or 0):.3f} kg")
    c2.metric("Cantidad calculada", calculada)
    c3.metric("Cantidad esperada", esperada if esperada else "Sin orden",
              delta=(calculada - esperada) if esperada else None)

    if rec.get("mensaje") and rec["checks"].get("qr") == "FALLO":
        st.caption(rec["mensaje"])
    if rec.get("ot_id"):
        st.warning(f"Orden de trabajo {rec['ot_id']} creada.", icon=":material/assignment_late:")
        st.page_link("paginas/ordenes.py", label="Ver órdenes de trabajo", icon=":material/assignment:")

    if st.button("Nueva recepción", type="primary", width="stretch"):
        reiniciar()
        st.rerun()


# ---------------- Página ----------------
st.title("Recepción de material")
st.caption(f"Estación {config.ESTACION}. Recepción ciega: la cantidad esperada se muestra al terminar.")
if config.USAR_MOCK:
    st.caption(":orange[Modo simulado]")

en_curso = "recepcion_id" in st.session_state
qr_url = st.query_params.get("qr", "")
qr = st.text_input(
    "Código QR de la remisión",
    value=st.session_state.get("recepcion_qr", qr_url),
    placeholder="KV-1042-1001-0001",
    help="Se llena solo al escanear el QR con la cámara del celular.",
    disabled=en_curso,
).strip().upper()

if not qr:
    st.info("Escanea el QR con la cámara del celular o escríbelo arriba.", icon=":material/qr_code_2:")
    st.stop()

datos = interpretar_qr(qr)
if datos is None:
    st.error("Formato no válido. Debe ser KV-orden-artículo-lote, por ejemplo KV-1042-1001-0001.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Orden de compra", datos["orden_compra"])
c2.metric("Artículo", datos["articulo"])
c3.metric("Lote", datos["lote"])

if not en_curso:
    if st.button("Iniciar recepción", type="primary", width="stretch"):
        try:
            respuesta = api.escanear_qr(qr)
        except api.ErrorAPI as e:
            st.error(str(e))
            st.stop()
        st.session_state.recepcion_id = respuesta["recepcion_id"]
        st.session_state.recepcion_qr = qr
        st.session_state.recepcion_inicio = time.time()
        st.session_state.recepcion_desc = respuesta.get("descripcion")
        st.rerun()
    st.stop()

if st.session_state.get("recepcion_desc"):
    st.markdown(f"**Material:** {st.session_state.recepcion_desc}")

if "recepcion_final" in st.session_state:
    mostrar_resultado(st.session_state.recepcion_final)
else:
    seguimiento()
