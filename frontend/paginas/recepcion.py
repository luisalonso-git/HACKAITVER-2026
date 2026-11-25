import time

import streamlit as st

import api
import config
from componentes import aviso_origen, mostrar_checks, tabla_eventos
from utils import ESCENARIOS_SIMULADOR, codigo_valido

LLAVES_SESION = ["rec_id", "rec_codigo", "rec_inicio", "rec_bulto", "rec_final", "rec_simulado"]


def reiniciar():
    for llave in LLAVES_SESION:
        st.session_state.pop(llave, None)
    st.query_params.clear()


def peso_esperado(codigo):
    """Peso del bulto en la base (solo para alimentar al simulador; no se muestra al operador)."""
    try:
        for b in api.listar_bultos():
            if b["bulto_id"] == codigo:
                return b["peso_kg"]
    except api.ErrorAPI:
        pass
    return 10.0


def panel_simulador():
    with st.expander("Simular la llegada del bulto (demo sin hardware)", icon=":material/sensors:",
                     expanded=not st.session_state.get("rec_simulado")):
        st.caption("Ejecuta el simulador de la carpeta IoT en la estación "
                   f"{config.ESTACION}. Con el ESP32 conectado, este paso no hace falta.")
        escenario = st.selectbox("Escenario", list(ESCENARIOS_SIMULADOR),
                                 format_func=lambda e: ESCENARIOS_SIMULADOR[e], key="rec_escenario")
        if st.button("Enviar eventos del simulador", icon=":material/play_arrow:"):
            try:
                api.lanzar_simulador([escenario], peso_esperado(st.session_state.rec_codigo))
            except api.ErrorAPI as e:
                st.error(str(e))
            else:
                st.session_state.rec_simulado = escenario
                st.toast(f"Simulando: {escenario}")


@st.fragment(run_every=2)
def seguimiento():
    try:
        rec = api.obtener_recepcion(st.session_state.rec_id)
    except api.ErrorAPI as e:
        st.warning(f"Sin respuesta del backend, reintentando. {e}")
        return

    if rec["estado"] != "PENDIENTE":
        st.session_state.rec_final = rec
        st.rerun()

    transcurrido = time.time() - st.session_state.rec_inicio
    if transcurrido > config.TIEMPO_ESPERA_S:
        st.warning("Pasó el tiempo de espera sin resultado. Revisa la estación o cancela.")
    else:
        st.info("Coloca el bulto en la báscula. La estación está enviando sus lecturas.", icon=":material/scale:")
        st.progress(transcurrido / config.TIEMPO_ESPERA_S,
                    text=f"Ventana de recepción abierta ({int(transcurrido)} s)")
    mostrar_checks(rec["checks"])
    st.markdown("**Eventos recibidos de la estación**")
    tabla_eventos(rec.get("eventos", []))
    aviso_origen(rec.get("eventos", []))

    if st.button("Cancelar recepción"):
        reiniciar()
        st.rerun()


def mostrar_resultado(rec):
    if rec["estado"] == "OK":
        st.success("Recepción correcta. La entrada se registró en almacén automáticamente.",
                   icon=":material/check_circle:")
    else:
        st.error("Recepción sospechosa. Cada fallo abrió una orden de trabajo para revisión humana.",
                 icon=":material/error:")

    mostrar_checks(rec["checks"])

    c1, c2, c3 = st.columns(3)
    medido, esperado, dif = rec.get("peso_medido_kg"), rec.get("peso_esperado_kg"), rec.get("diferencia_pct")
    c1.metric("Peso medido", f"{medido:.2f} kg" if medido is not None else "Sin lectura")
    c2.metric("Peso esperado", f"{esperado:.2f} kg" if esperado is not None else "Bulto no registrado")
    c3.metric("Diferencia", f"{dif:+.1f} %" if dif is not None else "N/D")

    if rec["checks"].get("qr") == "FALLO":
        st.caption(rec.get("mensaje", ""))

    st.markdown("**Evidencia: eventos de la estación**")
    tabla_eventos(rec.get("eventos", []), vacio="No llegó ningún evento de la estación.")
    aviso_origen(rec.get("eventos", []))

    if rec.get("ots"):
        st.warning("Órdenes de trabajo creadas: " + ", ".join(rec["ots"]), icon=":material/assignment_late:")
        st.page_link("paginas/ordenes.py", label="Ver órdenes de trabajo", icon=":material/assignment:")

    if st.button("Nueva recepción", type="primary", width="stretch"):
        reiniciar()
        st.rerun()


# ---------------- Página ----------------
st.title("Recepción de material")
st.caption(f"Estación {config.ESTACION}. Recepción ciega: el peso esperado se muestra al terminar.")

en_curso = "rec_id" in st.session_state
codigo = st.text_input(
    "Código QR del bulto",
    value=st.session_state.get("rec_codigo", st.query_params.get("qr", "")),
    placeholder="B-0001",
    help="Se llena solo al escanear el QR con la cámara del celular.",
    disabled=en_curso,
).strip().upper()

if not codigo:
    st.info("Escanea el QR del bulto con la cámara del celular o escríbelo arriba (por ejemplo B-0001).",
            icon=":material/qr_code_2:")
    st.stop()

if not codigo_valido(codigo):
    st.error("Formato no válido. El QR debe ser B- seguido de 4 dígitos, por ejemplo B-0001.")
    st.stop()

if not en_curso:
    if st.button("Iniciar recepción", type="primary", width="stretch"):
        try:
            respuesta = api.escanear(codigo)
        except api.ErrorAPI as e:
            st.error(str(e))
            st.stop()
        st.session_state.rec_id = respuesta["recepcion_id"]
        st.session_state.rec_codigo = codigo
        st.session_state.rec_inicio = time.time()
        st.session_state.rec_bulto = respuesta.get("bulto")
        st.rerun()
    st.stop()

bulto = st.session_state.get("rec_bulto")
if bulto:
    c1, c2, c3 = st.columns(3)
    c1.metric("Orden de compra", bulto["oc"])
    c2.metric("SKU", bulto["sku"])
    c3.metric("Bulto", bulto["bulto_id"])
    st.markdown(f"**Material:** {bulto['descripcion']}")
else:
    st.caption("El código no aparece en la base de datos.")

if "rec_final" in st.session_state:
    mostrar_resultado(st.session_state.rec_final)
else:
    panel_simulador()
    seguimiento()
