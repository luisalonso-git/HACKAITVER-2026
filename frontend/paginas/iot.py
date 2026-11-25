import importlib.util
import sys

import pandas as pd
import streamlit as st

import api
import config
from componentes import tabla_eventos
from utils import ESCENARIOS_SIMULADOR, NOMBRE_ORIGEN, TIPOS_EVENTO, hora

st.title("Estación IoT")
st.caption("Eventos del acelerómetro (MPU6050) y de la báscula, simulados o físicos, según el contrato.")


@st.cache_resource
def cargar_detector():
    """Importa detector.py de la carpeta IoT para mostrar sus umbrales (los mismos del ESP32)."""
    ruta = config.RUTA_SIMULADOR.parent / "detector.py"
    if not ruta.exists():
        return None
    spec = importlib.util.spec_from_file_location("detector_iot", ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # necesario para @dataclass
    spec.loader.exec_module(modulo)
    return modulo


# ---------------- Simulador ----------------
st.subheader("Simulador de la estación")
try:
    bultos = api.listar_bultos()
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()

with st.form("form_simulador"):
    c1, c2 = st.columns(2)
    escenarios = c1.multiselect("Escenarios (se ejecutan en orden)", list(ESCENARIOS_SIMULADOR),
                                default=["normal"], format_func=lambda e: ESCENARIOS_SIMULADOR[e])
    estacion = c2.text_input("Estación", value=config.ESTACION)

    c3, c4 = st.columns(2)
    opciones_bulto = {b["bulto_id"]: b for b in bultos}
    bulto_id = c3.selectbox("Bulto (define el peso esperado)", list(opciones_bulto),
                            format_func=lambda b: f"{b} · {opciones_bulto[b]['descripcion']}")
    escanear_antes = c4.checkbox("Escanear el bulto antes de simular (recepción completa)", value=True,
                                 help="Crea la recepción como si el operador escaneara el QR. "
                                      "Solo con un escenario, porque la ventana dura 20 s.")

    c5, c6, c7, c8 = st.columns(4)
    velocidad = c5.select_slider("Velocidad", options=[0.5, 1.0, 2.0, 4.0], value=1.0,
                                 help="1.0 = tiempo real")
    usar_ruido = c6.checkbox("Ruido manual")
    ruido = c6.number_input("Ruido (g)", min_value=0.0, max_value=0.5, value=0.02, step=0.01)
    usar_semilla = c7.checkbox("Semilla fija")
    semilla = c7.number_input("Semilla", min_value=0, value=1, step=1)
    pausa = c8.number_input("Pausa entre escenarios (s)", min_value=0.0, value=3.0, step=1.0)

    enviar = st.form_submit_button("Ejecutar simulador", type="primary", icon=":material/play_arrow:")

if enviar:
    if not escenarios:
        st.error("Elige al menos un escenario.")
    elif escanear_antes and len(escenarios) > 1:
        st.error("Para una recepción completa elige un solo escenario, o desmarca el escaneo.")
    else:
        try:
            if escanear_antes:
                r = api.escanear(bulto_id, estacion)
                st.session_state.iot_recepcion = r["recepcion_id"]
            api.lanzar_simulador(escenarios, opciones_bulto[bulto_id]["peso_kg"], estacion, velocidad,
                                 ruido if usar_ruido else None, semilla if usar_semilla else None, pausa)
        except api.ErrorAPI as e:
            st.error(str(e))
        else:
            st.success(f"Simulador en marcha en {estacion}: {', '.join(escenarios)}.",
                       icon=":material/sensors:")


# ---------------- En vivo ----------------
@st.fragment(run_every=2)
def en_vivo():
    try:
        eventos = api.listar_eventos()
        recepciones = api.listar_recepciones()
    except api.ErrorAPI as e:
        st.error(str(e))
        return

    rid = st.session_state.get("iot_recepcion")
    if rid:
        rec = next((r for r in recepciones if r["id"] == rid), None)
        if rec:
            colores = {"OK": "green", "SOSPECHOSO": "red", "PENDIENTE": "gray"}
            st.markdown(f"**Recepción {rid} ({rec['codigo']}):** "
                        f":{colores[rec['estado']]}[{rec['estado']}]"
                        + (f" · OT: {', '.join(rec['ots'])}" if rec["ots"] else ""))

    st.subheader("Eventos en vivo")
    conteo = {t: sum(e["tipo"] == t for e in eventos) for t in TIPOS_EVENTO}
    columnas = st.columns(6)
    for col, (tipo, (nombre, _)) in zip(columnas, TIPOS_EVENTO.items()):
        col.metric(nombre, conteo[tipo])
    columnas[4].metric("Simulados", sum(e["origen"] == "simulado" for e in eventos))
    columnas[5].metric("Físicos", sum(e["origen"] == "fisico" for e in eventos))

    izq, der = st.columns([3, 2])
    with izq:
        st.markdown("**Últimos 15 eventos**")
        tabla_eventos(list(reversed(eventos))[:15], mostrar_estacion=True,
                      vacio="Todavía no hay eventos. Ejecuta el simulador o conecta el ESP32.")
    with der:
        st.markdown("**Recepciones recientes**")
        if recepciones:
            st.dataframe(pd.DataFrame([{
                "Id": r["id"], "Bulto": r["codigo"], "Estación": r["estacion"], "Estado": r["estado"],
                "OT": len(r["ots"]), "Cerrada": hora(r.get("cerrada_ts")),
            } for r in recepciones[:10]]), hide_index=True, width="stretch")
        else:
            st.caption("Sin recepciones todavía.")


en_vivo()

# ---------------- Detector ----------------
with st.expander("Parámetros del detector (los mismos que irán en el firmware del ESP32)",
                 icon=":material/tune:"):
    det = cargar_detector()
    if det is None:
        st.caption("No se encontró detector.py en la carpeta IoT.")
    else:
        st.dataframe(pd.DataFrame([
            {"Parámetro": "Umbral de presencia", "Valor": f"{det.UMBRAL_PRESENCIA_G} g",
             "Uso": "Pico mínimo para decir que se colocó un bulto"},
            {"Parámetro": "Umbral de golpe", "Valor": f"{det.UMBRAL_GOLPE_G} g",
             "Uso": "Manipulación brusca"},
            {"Parámetro": "Umbral de inclinación", "Valor": f"{det.UMBRAL_INCLINACION_DEG}°",
             "Uso": f"Sostenida {det.TIEMPO_INCLINACION_S} s, se rearma {det.HISTERESIS_DEG}° abajo"},
            {"Parámetro": "Anti-rebote", "Valor": f"{det.PAUSA_MIN_S} s", "Uso": "Pausa mínima entre eventos"},
            {"Parámetro": "Ventana de pico", "Valor": f"{det.VENTANA_PICO_S} s", "Uso": "Tiempo para medir el pico"},
            {"Parámetro": "Promedio de ángulo", "Valor": f"{det.VENTANA_PROMEDIO} muestras",
             "Uso": "Suaviza la inclinación"},
        ]), hide_index=True, width="stretch")
        st.caption("Origen: " + ", ".join(NOMBRE_ORIGEN[o] for o in ("simulado", "fisico"))
                   + ". El peso sigue simulado mientras no haya celda de carga.")
