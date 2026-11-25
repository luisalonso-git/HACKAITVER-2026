from html import escape

import pandas as pd
import requests
import streamlit as st

import api
import config
import graficas
from estilo import barra, encabezado, flujo, html, kpis, pildora, seccion, tarjeta
from utils import NOMBRE_ESTADO

ARCHIVOS = {"compras.csv": "Compras", "almacen.csv": "Almacén", "ordenes_trabajo.csv": "OT históricas"}
NOMBRE_FUENTE = {"compras": "Compras", "almacen": "Almacén", "ordenes_trabajo": "OT históricas"}
TONO_CATEGORIA = {"duplicado": "violeta", "dato_incompleto": "ambar", "cantidad_distinta": "rojo", "formato": "verde"}
NOMBRE_TIPO_HOJA = {
    "duplicado_exacto": "Duplicado exacto", "duplicado_distinto_id": "Duplicado con otro folio",
    "casi_duplicado": "Casi duplicado", "campo_vacio": "Campo vacío", "valor_invalido": "Valor inválido",
    "fecha_futura": "Fecha futura", "formato_inconsistente": "Formato inconsistente",
    "sin_recepcion": "Compra sin recepción", "diferencia_cantidad": "Diferencia de cantidad", "sku_huerfano": "SKU huérfano",
}

try:
    d = api.obtener_datos()
except api.ErrorAPI as e:
    encabezado("Datos", seccion="Control")
    st.error(f"El backend no ofrece el motor de limpieza: {e}")
    st.stop()

ev = d.get("evaluacion") or {}
encabezado("Datos de compras, almacén y OT",
           "Motor de limpieza sobre los archivos del equipo: corrige lo de formato y convierte el resto en órdenes de trabajo.",
           seccion="Control",
           pildoras=pildora(f"Fecha de referencia {d['fecha_referencia']}", "cian")
           + pildora("Motor de limpieza activo", "verde", vivo=True))

g = d["global"]
ots_datos = [h for h in d["hallazgos"] if h["accion"] == "ot"]
cerradas = sum(h["ot_estado"] == "cerrada" for h in ots_datos)
kpis([
    {"etiqueta": "Registros analizados", "valor": d["total_registros"], "icono": "datos", "acento": "azul",
     "pie": "compras · almacén · OT históricas"},
    {"etiqueta": "Índice de calidad", "valor": f"{g['despues'] * 100:.1f}", "unidad": "%", "icono": "escudo",
     "acento": "cian", "pie": f"antes {g['antes'] * 100:.1f} % · sube al cerrar OT", "tendencia": "+"},
    {"etiqueta": "Hallazgos", "valor": len(d["hallazgos"]), "icono": "alerta", "acento": "violeta",
     "pie": (f"{d['corregidos_automaticamente']} corregido solo" if d["corregidos_automaticamente"] == 1
             else f"{d['corregidos_automaticamente']} corregidos solos") + f" · {len(ots_datos)} OT ({cerradas} cerradas)"},
    {"etiqueta": "Hoja de respuestas", "valor": f"{ev.get('detectados_correctos', '—')}/{ev.get('sembrados', '—')}",
     "icono": "check", "acento": "verde",
     "pie": f"{(ev.get('deteccion') or 0) * 100:.0f} % detectado · sin falsas alarmas" if not ev.get("fuera_de_la_hoja")
     else f"{len(ev['fuera_de_la_hoja'])} señalados fuera de la hoja"},
    {"etiqueta": "Dinero involucrado", "valor": f"${d['impacto_mxn']:,.0f}", "unidad": "MXN", "icono": "dinero",
     "acento": "ambar", "pie": "diferencias y compras sin recibir"},
])

with tarjeta("flujo_datos"):
    seccion("Cómo procesa los datos", "capas")
    flujo([
        ("datos", "Fuentes CSV", "compras, almacén y OT del equipo"),
        ("filtro", "Normalización", "fechas, mayúsculas, espacios"),
        ("escudo", "Reglas", "vacíos, inválidos, duplicados, SKU"),
        ("cruce", "Cruce", "compra ↔ entrada, registro por registro"),
        ("orden", "Acción", "se corrige solo o abre una OT"),
    ])

izq, der = st.columns(2, gap="medium")
with izq:
    with tarjeta("calidad_fuente"):
        seccion("Calidad por archivo", "datos", nota="antes y ahora")
        fuentes = d["por_fuente"]
        graficas.barras_agrupadas(
            [NOMBRE_FUENTE.get(f["fuente"], f["fuente"]) for f in fuentes],
            [("Antes", [f["antes"] * 100 for f in fuentes], "#3B3566"),
             ("Ahora", [f["despues"] * 100 for f in fuentes], "azul")],
            unidad="%", alto=280, rango_y=[0, 100], clave="datos_fuentes")
with der:
    with tarjeta("reglas"):
        seccion("Hallazgos por regla", "alerta")
        nombres = {h["regla"]: h["regla_nombre"] for h in d["hallazgos"]}
        graficas.barras_horizontales([nombres.get(k, k) for k in d["por_regla"]], list(d["por_regla"].values()),
                                     unidad="registros", tono="azul", alto=280, clave="datos_reglas")

ev_col, pend_col = st.columns([1.3, 1], gap="medium")
with ev_col:
    with tarjeta("evaluacion"):
        seccion("Contra la hoja de respuestas", "check", nota="errores_sembrados.csv del equipo")
        filas = "".join(
            f'<div style="display:grid;grid-template-columns:1.4fr 2fr auto;gap:.8rem;align-items:center;padding:.38rem 0">'
            f'<span>{escape(NOMBRE_TIPO_HOJA.get(t, t))}</span>{barra(v["detectados"] / v["sembrados"])}'
            f'<span class="kv-mono kv-tenue">{v["detectados"]}/{v["sembrados"]}</span></div>'
            for t, v in (ev.get("por_tipo") or {}).items())
        html(filas or '<div class="kv-tenue">Sin hoja de respuestas.</div>')
with pend_col:
    with tarjeta("pendientes"):
        seccion("Compras sin recepción", "caja", nota="se reciben en la estación IoT")
        for p in d["pendientes"]:
            estado = pildora("Recibida", "verde") if p["recibido"] else pildora("Pendiente", "ambar", vivo=True)
            html(f'<div style="display:flex;align-items:center;gap:.6rem;padding:.5rem 0;border-bottom:1px solid var(--kv-borde)">'
                 f'<span class="kv-mono">{escape(p["id_compra"])}</span><span>{escape(p["descripcion"])} · {p["cantidad"]}</span>'
                 f'<span style="margin-left:auto">{estado}</span></div>')
            if not p["recibido"] and p.get("bulto_id"):
                st.caption(f"Escanea {p['bulto_id']} en Recepción: al validarse, su OT se cierra sola y el índice sube.")
        if not d["pendientes"]:
            html('<div class="kv-tenue">Todas las compras tienen entrada en almacén.</div>')

with tarjeta("tabla_hallazgos"):
    cab, f1, f2, f3 = st.columns([1.3, 1, 1, 1], vertical_alignment="bottom")
    with cab:
        seccion("Hallazgos", "filtro")
    archivos = f1.multiselect("Archivo", list(ARCHIVOS), default=list(ARCHIVOS), format_func=ARCHIVOS.get)
    categorias = sorted({h["categoria"] for h in d["hallazgos"]})
    elegidas = f2.multiselect("Categoría", categorias, default=categorias,
                              format_func=lambda c: c.replace("_", " ").capitalize())
    acciones = f3.multiselect("Acción", ["ot", "corregido"], default=["ot", "corregido"],
                              format_func=lambda a: "Orden de trabajo" if a == "ot" else "Corregido solo")
    vista = [h for h in d["hallazgos"] if h["archivo"] in archivos and h["categoria"] in elegidas and h["accion"] in acciones]
    st.dataframe(pd.DataFrame([{
        "Archivo": ARCHIVOS.get(h["archivo"], h["archivo"]), "Línea": h["linea"], "Folio": h["id"], "SKU": h["sku"],
        "Regla": h["regla_nombre"], "Detalle": h["detalle"],
        "Acción": "Corregido solo" if h["accion"] == "corregido" else "Orden de trabajo",
        "OT": h["ot_id"] or "—", "Estado OT": NOMBRE_ESTADO.get(h["ot_estado"], "—") if h["ot_estado"] else "—",
        "Impacto (MXN)": h["impacto_mxn"],
    } for h in vista]), hide_index=True, width="stretch", height=min(460, 38 + 35 * max(1, len(vista))),
        column_config={"Impacto (MXN)": st.column_config.NumberColumn(format="$%.2f"),
                       "Detalle": st.column_config.TextColumn(width="large")})

with tarjeta("descargas"):
    seccion("Descargas", "descarga")
    c1, c2 = st.columns([1, 1.4])
    try:
        reporte = requests.get(f"{config.API_URL}/api/datos/reporte", timeout=5).content
    except requests.RequestException:
        reporte = None
    c1.download_button("Reporte de errores para Excel", data=reporte or b"", file_name="reporte_errores_excel.csv",
                       mime="text/csv", icon=":material/table_view:", width="stretch", disabled=reporte is None,
                       type="primary")
    with c2:
        archivo = st.selectbox("Datos limpios", list(d["limpios"]), format_func=lambda a: f"{ARCHIVOS.get(a, a)} limpio",
                               label_visibility="collapsed")
        limpio = pd.DataFrame(d["limpios"][archivo])
        st.download_button(f"Descargar {archivo.replace('.csv', '_limpio.csv')}",
                           data=limpio.to_csv(index=False, sep=";").encode("utf-8-sig"),
                           file_name=archivo.replace(".csv", "_limpio.csv"), mime="text/csv",
                           icon=":material/download:", width="stretch")
    with st.expander("Ver datos limpios", icon=":material/visibility:"):
        st.dataframe(limpio, hide_index=True, width="stretch")
    st.caption("Datos del equipo (datos/fuentes). Motor: datos/motor_limpieza.py, construido sobre datos/equipo/limpieza.py.")
