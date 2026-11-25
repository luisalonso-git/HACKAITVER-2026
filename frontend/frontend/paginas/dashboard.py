import pandas as pd
import streamlit as st

import api
import config
import graficas
from estilo import encabezado, kpis, pildora, seccion, tarjeta
from utils import PRIORIDADES_OT, TIPOS_OT

NOMBRE_FUENTE = {"compras": "Compras", "almacen": "Almacén", "costos": "Costos",
                 "ot_operativas": "OT operativas", "recepciones": "Recepciones"}
NOMBRE_RANGO = {"1h": "última hora", "24h": "últimas 24 h", "7d": "últimos 7 días", "30d": "últimos 30 días"}

cabeza, control = st.columns([2.2, 1], vertical_alignment="bottom")
with cabeza:
    encabezado("Calidad de datos", "Índice de calidad, recepciones validadas y órdenes de trabajo en el tiempo.",
               seccion="Control", pildoras=pildora("En vivo · cada 10 s", "verde", vivo=True))
with control:
    rango = graficas.selector_rango("rango_dashboard")


@st.fragment(run_every=10)
def tablero(rango):
    try:
        calidad = api.obtener_calidad()
        ots = api.listar_ot()
        inventario = api.obtener_inventario()
        serie = api.obtener_series(rango)
    except api.ErrorAPI as e:
        st.error(str(e))
        return

    g = calidad["global"]
    t = serie["totales"]
    puntos = serie["puntos"]
    total = calidad["total_registros"]
    horas = total * config.MINUTOS_VALIDACION_MANUAL / 60
    abiertas = [o for o in ots if o["estado"] != "cerrada"]

    kpis([
        {"etiqueta": "Índice de calidad", "valor": f"{g['despues'] * 100:.1f}", "unidad": "%", "icono": "escudo",
         "acento": "cian", "pie": f"{(g['despues'] - g['antes']) * 100:+.1f} pts vs. datos crudos", "tendencia": "+"},
        {"etiqueta": f"Recepciones · {NOMBRE_RANGO[rango]}", "valor": t["recepciones"], "icono": "caja",
         "acento": "azul", "pie": f"{(t['tasa_ok'] or 0) * 100:.0f} % correctas"},
        {"etiqueta": f"OT · {NOMBRE_RANGO[rango]}", "valor": t["ot_creadas"], "unidad": "creadas", "icono": "orden",
         "acento": "violeta", "pie": f"{t['ot_cerradas']} cerradas · {len(abiertas)} abiertas hoy"},
        {"etiqueta": "Validación manual evitada", "valor": f"{horas:.1f}", "unidad": "h", "icono": "reloj",
         "acento": "verde", "pie": f"{total:,} registros × {config.MINUTOS_VALIDACION_MANUAL} min"},
    ])

    a, b = st.columns([1, 2], gap="medium")
    with a:
        with tarjeta("medidor"):
            seccion("Índice actual", "medidor", nota="referencia: datos crudos")
            graficas.medidor(g["despues"] * 100, g["antes"] * 100, alto=250, clave="d_medidor")
    with b:
        with tarjeta("calidad_t"):
            seccion("Índice de calidad en el tiempo", "tendencia", nota=NOMBRE_RANGO[rango])
            graficas.calidad_tiempo(puntos, rango, alto=250, clave="d_calidad")

    c, d = st.columns(2, gap="medium")
    with c:
        with tarjeta("rec_t"):
            seccion("Recepciones validadas", "caja", nota="correctas vs. sospechosas")
            graficas.barras_tiempo(puntos, [("recepciones_ok", "Correctas", "azul"),
                                            ("recepciones_sospechosas", "Sospechosas", "violeta")],
                                   rango, unidad="recepciones", alto=280, clave="d_rec")
    with d:
        with tarjeta("ot_t"):
            seccion("Órdenes de trabajo", "orden", nota="creadas vs. cerradas")
            graficas.lineas_tiempo(puntos, [("ot_creadas", "Creadas", "violeta", "d"),
                                            ("ot_cerradas", "Cerradas", "verde", "d")],
                                   rango, unidad="OT", alto=280, clave="d_ot")

    e, f = st.columns(2, gap="medium")
    with e:
        with tarjeta("fuentes"):
            seccion("Calidad por fuente", "datos", nota="antes y después de la limpieza")
            fuentes = [x for x in calidad["por_fuente"] if x.get("antes") is not None]
            graficas.barras_agrupadas(
                [NOMBRE_FUENTE.get(x["fuente"], x["fuente"]) for x in fuentes],
                [("Antes", [x["antes"] * 100 for x in fuentes], "#3A4357"),
                 ("Después", [x["despues"] * 100 for x in fuentes], "cian")],
                unidad="%", alto=280, rango_y=[50, 100], clave="d_fuentes")
    with f:
        with tarjeta("hallazgos"):
            seccion("Hallazgos por tipo", "alerta", nota="datos + recepciones")
            h = calidad["hallazgos"]
            graficas.barras_horizontales([TIPOS_OT.get(k, k) for k in h], list(h.values()),
                                         unidad="hallazgos", tono="violeta", alto=280, clave="d_hallazgos")

    g1, g2 = st.columns([1, 1.6], gap="medium")
    with g1:
        with tarjeta("prioridad"):
            seccion("OT sin cerrar", "alerta", nota="por prioridad")
            graficas.dona([p.capitalize() for p in PRIORIDADES_OT],
                          [sum(o["prioridad"] == p for o in abiertas) for p in PRIORIDADES_OT],
                          ["rojo", "ambar", "azul"], centro=str(len(abiertas)), subtitulo="abiertas",
                          unidad="OT", alto=280, clave="d_dona")
    with g2:
        with tarjeta("inventario"):
            seccion("Inventario", "caja", nota="se actualiza con cada recepción correcta")
            df = pd.DataFrame(inventario)
            maximo = int(df["existencia"].max()) if not df.empty else 1
            st.dataframe(
                df.rename(columns={"sku": "SKU", "descripcion": "Descripción", "existencia": "Existencia"}),
                hide_index=True, width="stretch", height=260,
                column_config={"Existencia": st.column_config.ProgressColumn(
                    "Existencia", format="%d", min_value=0, max_value=maximo)},
            )

    st.caption("Historial de 30 días simulado para la demo; la actividad de esta sesión se suma en vivo.")


tablero(rango)
