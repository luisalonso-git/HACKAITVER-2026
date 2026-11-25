import importlib.util
import sys
from html import escape

import pandas as pd
import streamlit as st

import api
import config
import graficas
from componentes import estado_conexion, linea_eventos
from estilo import encabezado, html, kpis, pildora, seccion, tarjeta
from utils import ESCENARIOS_SIMULADOR, TIPOS_EVENTO, hora

COLOR_ESTADO = {"OK": "verde", "SOSPECHOSO": "rojo", "PENDIENTE": "cian"}


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


encabezado("Estación IoT", "Acelerómetro MPU6050 y báscula: eventos en vivo, simulador y parámetros del detector.",
           seccion="Operación",
           pildoras=estado_conexion(api.backend_activo(), config.RUTA_SIMULADOR.exists(), config.ESTACION))

try:
    bultos = api.listar_bultos()
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()


# ---------------- En vivo ----------------
@st.fragment(run_every=2)
def en_vivo():
    try:
        eventos = api.listar_eventos()
        recepciones = api.listar_recepciones()
    except api.ErrorAPI as e:
        st.error(str(e))
        return

    conteo = {t: sum(e["tipo"] == t for e in eventos) for t in TIPOS_EVENTO}
    simulados = sum(e["origen"] == "simulado" for e in eventos)
    fisicos = sum(e["origen"] == "fisico" for e in eventos)
    kpis([
        {"etiqueta": "Eventos de la sesión", "valor": len(eventos), "icono": "actividad", "acento": "azul",
         "pie": f"{conteo['presencia']} presencias · {conteo['peso']} pesos"},
        {"etiqueta": "Manipulación detectada", "valor": conteo["golpe"] + conteo["inclinacion"], "icono": "alerta",
         "acento": "ambar", "pie": f"{conteo['golpe']} golpes · {conteo['inclinacion']} inclinaciones"},
        {"etiqueta": "Origen", "valor": fisicos, "unidad": f"físicos / {simulados} simulados", "icono": "cpu",
         "acento": "verde", "pie": "el contrato exige mostrarlo"},
        {"etiqueta": "Recepciones de la sesión", "valor": len(recepciones), "icono": "caja", "acento": "violeta",
         "pie": f"{sum(r['estado'] == 'OK' for r in recepciones)} correctas"},
    ])

    izq, der = st.columns([1.35, 1], gap="medium")
    with izq:
        with tarjeta("stream"):
            seccion("Flujo de eventos", "sensor", nota="últimos 12 · se actualiza cada 2 s")
            linea_eventos(list(reversed(eventos)), mostrar_estacion=True, limite=12,
                          vacio="Sin eventos todavía. Ejecuta el simulador o conecta el ESP32.")
    with der:
        with tarjeta("recepciones"):
            seccion("Recepciones recientes", "caja")
            if not recepciones:
                html('<div class="kv-tenue">Sin recepciones en esta sesión.</div>')
            for r in recepciones[:7]:
                html(f'<div style="display:flex;align-items:center;gap:.6rem;padding:.5rem 0;'
                     f'border-bottom:1px solid var(--kv-borde)"><span class="kv-mono">{escape(r["codigo"])}</span>'
                     f'<span class="kv-tenue">{escape(r["estacion"])}</span>'
                     f'<span style="margin-left:auto">{pildora(r["estado"].capitalize(), COLOR_ESTADO[r["estado"]], vivo=r["estado"] == "PENDIENTE")}</span>'
                     f'<span class="kv-tenue kv-mono" style="width:62px;text-align:right">{hora(r.get("cerrada_ts") or r.get("ts"))}</span></div>')


en_vivo()

# ---------------- Histórico ----------------
with tarjeta("historico"):
    cab, sel = st.columns([2, 1.2])
    with cab:
        seccion("Eventos por tipo", "tendencia", nota="histórico simulado + sesión")
    with sel:
        rango = graficas.selector_rango("rango_iot")
    try:
        datos = api.obtener_series(rango)
    except api.ErrorAPI as e:
        st.info(f"El backend no ofrece series de tiempo: {e}")
    else:
        graficas.lineas_tiempo(datos["puntos"], [
            ("presencia", "Presencia", "cian", "d"),
            ("peso", "Peso", "azul", "d"),
            ("golpe", "Golpe", "rojo", "d"),
            ("inclinacion", "Inclinación", "ambar", "d"),
        ], rango, unidad="eventos", alto=300, area=False, clave="iot_series")

# ---------------- Simulador ----------------
with tarjeta("form_sim"):
    seccion("Simulador de la estación", "rayo", nota="simulador.py de la carpeta IoT")
    with st.form("form_simulador", border=False):
        c1, c2, c3 = st.columns([2, 1, 1.4])
        escenarios = c1.multiselect("Escenarios (en orden)", list(ESCENARIOS_SIMULADOR), default=["normal"],
                                    format_func=lambda e: ESCENARIOS_SIMULADOR[e])
        estacion = c2.text_input("Estación", value=config.ESTACION)
        opciones = {b["bulto_id"]: b for b in bultos}
        bulto_id = c3.selectbox("Bulto (peso esperado)", list(opciones),
                                format_func=lambda b: f"{b} · {opciones[b]['peso_kg']:.2f} kg")
        c4, c5, c6, c7 = st.columns(4)
        velocidad = c4.select_slider("Velocidad", options=[0.5, 1.0, 2.0, 4.0], value=1.0, help="1.0 = tiempo real")
        ruido = c5.number_input("Ruido (g)", min_value=0.0, max_value=0.5, value=0.0, step=0.01,
                                help="0 = el del escenario")
        semilla = c6.number_input("Semilla", min_value=0, value=0, step=1, help="0 = aleatoria")
        pausa = c7.number_input("Pausa (s)", min_value=0.0, value=3.0, step=1.0)
        escanear_antes = st.toggle("Escanear el bulto antes (recepción completa, un solo escenario)", value=True)
        enviar = st.form_submit_button("Ejecutar simulador", type="primary", icon=":material/play_arrow:")

    if enviar:
        if not escenarios:
            st.error("Elige al menos un escenario.")
        elif escanear_antes and len(escenarios) > 1:
            st.error("Para una recepción completa elige un solo escenario, o desactiva el escaneo.")
        else:
            try:
                if escanear_antes:
                    api.escanear(bulto_id, estacion)
                api.lanzar_simulador(escenarios, opciones[bulto_id]["peso_kg"], estacion, velocidad,
                                     ruido or None, semilla or None, pausa)
            except api.ErrorAPI as e:
                st.error(str(e))
            else:
                st.toast(f"Simulando en {estacion}: {', '.join(escenarios)}", icon=":material/sensors:")

# ---------------- Detector ----------------
det = cargar_detector()
with st.expander("Parámetros del detector · los mismos que irán en el firmware del ESP32", icon=":material/tune:"):
    if det is None:
        st.caption("No se encontró detector.py en la carpeta IoT.")
    else:
        st.dataframe(pd.DataFrame([
            {"Parámetro": "Umbral de presencia", "Valor": f"{det.UMBRAL_PRESENCIA_G} g", "Uso": "Pico mínimo al colocar un bulto"},
            {"Parámetro": "Umbral de golpe", "Valor": f"{det.UMBRAL_GOLPE_G} g", "Uso": "Manipulación brusca"},
            {"Parámetro": "Umbral de inclinación", "Valor": f"{det.UMBRAL_INCLINACION_DEG}°",
             "Uso": f"Sostenida {det.TIEMPO_INCLINACION_S} s, se rearma {det.HISTERESIS_DEG}° abajo"},
            {"Parámetro": "Anti-rebote", "Valor": f"{det.PAUSA_MIN_S} s", "Uso": "Pausa mínima entre eventos"},
            {"Parámetro": "Ventana de pico", "Valor": f"{det.VENTANA_PICO_S} s", "Uso": "Tiempo para medir el pico"},
            {"Parámetro": "Promedio de ángulo", "Valor": f"{det.VENTANA_PROMEDIO} muestras", "Uso": "Suaviza la inclinación"},
        ]), hide_index=True, width="stretch")
