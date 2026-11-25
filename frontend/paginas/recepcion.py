import time
from html import escape

import streamlit as st

import api
import documentos
import config
from componentes import aviso_origen, estado_conexion, linea_eventos, mostrar_checks
from estilo import banner, encabezado, html, kpis, pasos, pildora, seccion, tarjeta
from utils import ESCENARIOS_SIMULADOR, TIPOS_OT, codigo_valido

PASOS = ["Escanear QR", "Colocar bulto", "Validación", "Resultado"]
LLAVES_SESION = ["rec_id", "rec_codigo", "rec_inicio", "rec_bulto", "rec_final", "rec_simulado"]


def reiniciar():
    for llave in LLAVES_SESION:
        st.session_state.pop(llave, None)
    st.query_params.clear()


def peso_esperado(codigo):
    """Peso del bulto en la base: solo alimenta al simulador, no se muestra al operador."""
    try:
        for b in api.listar_bultos():
            if b["bulto_id"] == codigo:
                return b["peso_kg"]
    except api.ErrorAPI:
        pass
    return 10.0


def ficha_bulto(bulto, codigo):
    with tarjeta("bulto"):
        seccion("Bulto", "caja")
        if bulto:
            filas = [("Código", bulto["bulto_id"]), ("Orden de compra", bulto["oc"]), ("SKU", bulto["sku"])]
            html("".join(
                f'<div style="display:flex;justify-content:space-between;padding:.45rem 0;'
                f'border-bottom:1px solid var(--kv-borde)"><span class="kv-tenue">{k}</span>'
                f'<span class="kv-mono">{escape(str(v))}</span></div>' for k, v in filas)
                + f'<div style="margin-top:.7rem;font-weight:500">{escape(bulto["descripcion"])}</div>')
        else:
            html(f'<div class="kv-mono" style="font-size:1.1rem">{escape(codigo)}</div>'
                 '<div class="kv-tenue">No aparece en la base de datos.</div>')


def panel_simulador():
    with tarjeta("simulador"):
        seccion("Simular llegada", "sensor", nota="demo sin hardware")
        escenario = st.selectbox("Escenario", list(ESCENARIOS_SIMULADOR),
                                 format_func=lambda e: ESCENARIOS_SIMULADOR[e], key="rec_escenario",
                                 label_visibility="collapsed")
        if st.button("Enviar eventos", icon=":material/play_arrow:", width="stretch", type="primary"):
            try:
                api.lanzar_simulador([escenario], peso_esperado(st.session_state.rec_codigo))
            except api.ErrorAPI as e:
                st.error(str(e))
            else:
                st.session_state.rec_simulado = escenario
                st.toast(f"Simulador en marcha: {escenario}", icon=":material/sensors:")
        st.caption(f"Ejecuta el simulador IoT en la estación {config.ESTACION}. Con el ESP32 conectado no hace falta.")


@st.fragment(run_every=1.5)
def seguimiento():
    try:
        rec = api.obtener_recepcion(st.session_state.rec_id)
    except api.ErrorAPI as e:
        st.warning(f"Sin respuesta del backend, reintentando. {e}")
        return

    if rec["estado"] != "PENDIENTE":
        st.session_state.rec_final = rec
        st.rerun()

    eventos = rec.get("eventos", [])
    pasos(PASOS, 2 if eventos else 1)
    transcurrido = time.time() - st.session_state.rec_inicio
    if transcurrido > config.TIEMPO_ESPERA_S:
        banner("mal", "Sin resultado a tiempo", "Revisa la estación o cancela la recepción.", "reloj")
    elif eventos:
        banner("info", "Validando con los sensores", "Llegan lecturas de la estación; el resultado sale en segundos.")
    else:
        banner("info", "Coloca el bulto en la báscula", "La ventana de recepción está abierta y esperando lecturas.",
               "caja")
    st.progress(min(transcurrido / config.TIEMPO_ESPERA_S, 1.0))
    mostrar_checks(rec["checks"])
    with tarjeta("eventos_vivo"):
        seccion("Eventos de la estación", "actividad", nota=f"{len(eventos)} recibidos")
        linea_eventos(eventos)
        aviso_origen(eventos)
    if st.button("Cancelar recepción", icon=":material/close:"):
        reiniciar()
        st.rerun()


def mostrar_resultado(rec):
    pasos(PASOS, 4)
    if rec["estado"] == "OK":
        extra = (f" Además cerró sola la {rec['resuelve']}: la compra que los datos marcaban sin recepción ya llegó."
                 if rec.get("resuelve") else "")
        banner("ok", "Recepción correcta", "La entrada se registró en almacén automáticamente." + extra)
    else:
        fallos = sum(v == "FALLO" for v in rec["checks"].values())
        banner("mal", "Recepción sospechosa",
               ("1 chequeo falló. Se abrió una orden de trabajo" if fallos == 1 else
                f"{fallos} chequeos fallaron. Cada fallo abrió una orden de trabajo") + " para revisión humana.")
    mostrar_checks(rec["checks"])

    medido, esperado, dif = rec.get("peso_medido_kg"), rec.get("peso_esperado_kg"), rec.get("diferencia_pct")
    kpis([
        {"etiqueta": "Peso medido", "valor": f"{medido:.2f}" if medido is not None else "—", "unidad": "kg",
         "icono": "medidor", "acento": "azul", "pie": "lectura de la báscula"},
        {"etiqueta": "Peso esperado", "valor": f"{esperado:.2f}" if esperado is not None else "—", "unidad": "kg",
         "icono": "caja", "acento": "violeta", "pie": "según la orden de compra" if esperado else "bulto no registrado"},
        {"etiqueta": "Diferencia", "valor": f"{dif:+.1f}" if dif is not None else "—", "unidad": "%",
         "icono": "tendencia", "acento": "verde" if dif is not None and abs(dif) <= 5 else "rojo",
         "pie": "tolerancia ±5 %"},
    ])
    if rec["checks"].get("qr") == "FALLO":
        html(pildora(rec.get("mensaje", ""), "rojo"))

    with tarjeta("evidencia"):
        seccion("Evidencia", "actividad", nota="eventos usados en la validación")
        linea_eventos(rec.get("eventos", []), vacio="No llegó ningún evento de la estación.")
        aviso_origen(rec.get("eventos", []))

    if rec.get("ots"):
        try:
            detalle = {o["id"]: o for o in api.listar_ot()}
        except api.ErrorAPI:
            detalle = {}
        filas = "".join(
            f'<div style="display:flex;gap:.6rem;align-items:center;padding:.45rem 0;border-bottom:1px solid var(--kv-borde)">'
            f'<span class="kv-mono">{escape(i)}</span>'
            f'{pildora(TIPOS_OT.get(detalle.get(i, {}).get("tipo"), "OT"), "violeta")}'
            f'<span class="kv-tenue">{escape(detalle.get(i, {}).get("causa", ""))}</span></div>'
            for i in rec["ots"])
        with tarjeta("ots_creadas"):
            seccion("Órdenes de trabajo creadas", "orden")
            html(filas)
            if documentos.HAY_PDF:
                columnas = st.columns(min(3, len(rec["ots"])))
                for i, ot_id in enumerate(rec["ots"]):
                    if ot_id in detalle:
                        columnas[i % len(columnas)].download_button(
                            f"PDF {ot_id}", data=documentos.pdf_orden(detalle[ot_id]),
                            file_name=documentos.nombre_archivo(detalle[ot_id]), mime="application/pdf",
                            icon=":material/picture_as_pdf:", width="stretch", key=f"pdf_rec_{ot_id}")
            st.page_link("paginas/ordenes.py", label="Revisar en Órdenes de trabajo", icon=":material/arrow_forward:")

    if st.button("Nueva recepción", type="primary", width="stretch", icon=":material/qr_code_scanner:"):
        reiniciar()
        st.rerun()


# ---------------- Página ----------------
encabezado("Recepción de material",
           "Recepción ciega: el operador no ve el peso esperado hasta que la estación termina de validar.",
           seccion="Operación", pildoras=estado_conexion(True, config.RUTA_SIMULADOR.exists(), config.ESTACION))

en_curso = "rec_id" in st.session_state
principal, lateral = st.columns([2.1, 1], gap="large")

with principal:
    if not en_curso:
        pasos(PASOS, 0)
        with tarjeta("escaneo"):
            seccion("Escanear QR del bulto", "qr")
            codigo = st.text_input("Código del bulto", value=st.query_params.get("qr", ""), placeholder="B-0001",
                                   label_visibility="collapsed").strip().upper()
            st.caption("Con la cámara del celular el código se llena solo. También puedes escribirlo.")
            if codigo and not codigo_valido(codigo):
                st.error("Formato no válido: B- y 4 dígitos, por ejemplo B-0001.")
            elif st.button("Iniciar recepción", type="primary", width="stretch", disabled=not codigo,
                           icon=":material/arrow_forward:"):
                try:
                    respuesta = api.escanear(codigo)
                except api.ErrorAPI as e:
                    st.error(str(e))
                else:
                    st.session_state.rec_id = respuesta["recepcion_id"]
                    st.session_state.rec_codigo = codigo
                    st.session_state.rec_inicio = time.time()
                    st.session_state.rec_bulto = respuesta.get("bulto")
                    st.rerun()
    elif "rec_final" in st.session_state:
        mostrar_resultado(st.session_state.rec_final)
    else:
        seguimiento()

with lateral:
    if en_curso:
        ficha_bulto(st.session_state.get("rec_bulto"), st.session_state.rec_codigo)
        if "rec_final" not in st.session_state:
            panel_simulador()
    else:
        with tarjeta("ayuda"):
            seccion("Cómo funciona", "escudo")
            html('<div class="kv-tenue" style="line-height:1.65">'
                 '1. Escanea el QR del bulto.<br>2. Colócalo en la báscula de la estación.<br>'
                 '3. Los sensores validan QR, presencia, peso y manipulación.<br>'
                 '4. Si algo no cuadra, se abre una orden de trabajo.</div>')
