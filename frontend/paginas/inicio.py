import streamlit as st

import api
import config
import graficas
from componentes import estado_conexion
from estilo import encabezado, html, icono, kpis, seccion, tarjeta

activo = api.backend_activo()
encabezado(
    "Resumen de operación",
    "Compras, almacén y órdenes de trabajo validados con evidencia física de sensores IoT.",
    seccion="Kardex Vivo",
    pildoras=estado_conexion(activo, config.RUTA_SIMULADOR.exists(), config.ESTACION),
)

if not activo:
    st.error(f"No hay backend en {config.API_URL}. En otra terminal, desde la carpeta del repositorio: "
             "`python backend_mock/servidor_mock.py`", icon=":material/cloud_off:")
    st.stop()

try:
    calidad = api.obtener_calidad()
    ots = api.listar_ot()
    dia = api.obtener_series("24h")
    mes = api.obtener_series("30d")
except api.ErrorAPI as e:
    st.error(str(e))
    st.stop()

g = calidad["global"]
abiertas = [o for o in ots if o["estado"] != "cerrada"]
altas = sum(o["prioridad"] == "alta" for o in abiertas)
t = dia["totales"]
kpis([
    {"etiqueta": "Índice de calidad", "valor": f"{g['despues'] * 100:.1f}", "unidad": "%", "icono": "escudo",
     "acento": "cian", "pie": f"{(g['despues'] - g['antes']) * 100:+.1f} pts tras la limpieza", "tendencia": "+"},
    {"etiqueta": "Recepciones · 24 h", "valor": t["recepciones"], "icono": "caja", "acento": "azul",
     "pie": f"{(t['tasa_ok'] or 0) * 100:.0f} % correctas"},
    {"etiqueta": "OT abiertas", "valor": len(abiertas), "icono": "orden", "acento": "violeta",
     "pie": f"{altas} de prioridad alta", "tendencia": "-" if altas else None},
    {"etiqueta": "Eventos IoT · 24 h", "valor": t["eventos"], "icono": "sensor", "acento": "verde",
     "pie": "presencia, peso, golpe e inclinación"},
])

izq, der = st.columns([3, 2], gap="medium")
with izq:
    with tarjeta("actividad"):
        seccion("Recepciones de las últimas 24 h", "actividad", nota="por hora")
        graficas.barras_tiempo(dia["puntos"], [("recepciones_ok", "Correctas", "azul"),
                                               ("recepciones_sospechosas", "Sospechosas", "violeta")],
                               "24h", unidad="recepciones", alto=270, clave="res_rec")
with der:
    with tarjeta("tendencia"):
        seccion("Calidad de datos · 30 días", "tendencia", nota="histórico simulado")
        graficas.calidad_tiempo(mes["puntos"], "30d", alto=270, clave="res_cal")

seccion("Módulos", "capas")
modulos = [
    ("recepcion", "qr", "azul", "Recepción", "Escanea el QR del bulto y la estación valida QR, presencia, peso y manipulación."),
    ("iot", "sensor", "cian", "Estación IoT", "Eventos del MPU6050 y la báscula en vivo, simulador y umbrales del detector."),
    ("datos", "datos", "indigo", "Datos", "Hallazgos del motor de limpieza en compras, almacén y OT, con reporte para Excel."),
    ("ordenes", "orden", "violeta", "Órdenes de trabajo", "Cada fallo abre una OT con su evidencia. Una persona confirma o descarta."),
    ("dashboard", "medidor", "verde", "Calidad de datos", "Índice antes y después, hallazgos, recepciones e inventario por rango de tiempo."),
]
tarjetas = "".join(
    f'<a href="./{ruta}" target="_self"><div class="kv-nav-item" style="--kv-acento:var(--kv-{tono});'
    f'animation-delay:{i * 70}ms"><div class="kv-nav-icono">{icono(ic, 18)}</div><h4>{titulo}</h4>'
    f'<p>{texto}</p><div class="kv-ir">Abrir {icono("flecha", 14)}</div></div></a>'
    for i, (ruta, ic, tono, titulo, texto) in enumerate(modulos)
)
html(f'<div class="kv-nav">{tarjetas}</div>')
