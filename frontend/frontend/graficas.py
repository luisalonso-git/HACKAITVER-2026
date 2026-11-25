"""Gráficas con Plotly y el tema de Kardex Vivo: fondo transparente, tooltips, unidades y transiciones."""
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
except ImportError:  # se avisa en pantalla con el comando para instalarlo
    go = None

from estilo import PALETA

TEXTO = "#C9D1DE"
TENUE = "#8B95A7"
REJILLA = "rgba(148,163,184,0.08)"
LINEA = "rgba(148,163,184,0.18)"
FORMATO_X = {"1h": "%H:%M", "24h": "%H:%M", "7d": "%d/%m %Hh", "30d": "%d/%m"}
RANGOS = {"1 h": "1h", "24 h": "24h", "7 d": "7d", "30 d": "30d"}


def disponible():
    if go is None:
        st.warning("Falta Plotly para las gráficas. En la terminal: `python -m pip install plotly` "
                   "y vuelve a abrir la app.")
        return False
    return True


def rgba(hex_color, alfa):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _tema(fig, alto=300, unidad_y="", leyenda=True, hover="x unified", formato_x=None, rango_y=None):
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=8, t=30 if leyenda else 8, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=TEXTO),
        hovermode=hover,
        hoverlabel=dict(bgcolor="#141B2B", bordercolor="rgba(148,163,184,0.35)",
                        font=dict(family="Inter, system-ui, sans-serif", size=12, color="#E5E9F0")),
        showlegend=leyenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=TENUE)),
        transition=dict(duration=600, easing="cubic-in-out"),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor=LINEA, tickfont=dict(color=TENUE, size=11),
                     tickformat=formato_x, zeroline=False, showspikes=False)
    fig.update_yaxes(gridcolor=REJILLA, zeroline=False, tickfont=dict(color=TENUE, size=11),
                     title=dict(text=unidad_y, font=dict(size=11, color=TENUE)), range=rango_y)
    return fig


def mostrar(fig, clave):
    st.plotly_chart(fig, theme=None, key=clave,
                    config={"displayModeBar": False, "responsive": True, "scrollZoom": False})


# ---------------- Tipos de gráfica ----------------
def lineas_tiempo(puntos, series, rango, unidad="", alto=300, area=True, clave="lineas"):
    """series: lista de (campo, nombre, color, formato_tooltip)."""
    if not disponible():
        return
    x = pd.to_datetime([p["t"] for p in puntos])
    fig = go.Figure()
    for i, (campo, nombre, tono, fmt) in enumerate(series):
        c = PALETA.get(tono, tono)
        fig.add_trace(go.Scatter(
            x=x, y=[p[campo] for p in puntos], name=nombre, mode="lines",
            line=dict(color=c, width=2.2, shape="spline", smoothing=0.6),
            fill="tozeroy" if area and i == 0 else None,
            fillcolor=rgba(c, 0.12) if area and i == 0 else None,
            hovertemplate=f"%{{y:{fmt}}} {unidad}<extra>{nombre}</extra>",
        ))
    mostrar(_tema(fig, alto, unidad, leyenda=len(series) > 1, formato_x=FORMATO_X.get(rango)), clave)


def calidad_tiempo(puntos, rango, alto=300, clave="calidad"):
    if not disponible():
        return
    x = pd.to_datetime([p["t"] for p in puntos])
    y = [p["calidad"] * 100 for p in puntos]
    c = PALETA["cian"]
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines", name="Índice de calidad",
        line=dict(color=c, width=2.4, shape="spline", smoothing=0.7),
        fill="tozeroy", fillcolor=rgba(c, 0.10),
        hovertemplate="%{y:.1f} %<extra>Índice de calidad</extra>",
    ))
    minimo = max(0, min(y) - 5) if y else 0
    mostrar(_tema(fig, alto, "% registros válidos", leyenda=False, formato_x=FORMATO_X.get(rango),
                  rango_y=[minimo, 100]), clave)


def barras_tiempo(puntos, series, rango, unidad="", alto=300, apiladas=True, clave="barras_t"):
    if not disponible():
        return
    x = pd.to_datetime([p["t"] for p in puntos])
    fig = go.Figure()
    for campo, nombre, tono in series:
        fig.add_trace(go.Bar(
            x=x, y=[p[campo] for p in puntos], name=nombre,
            marker=dict(color=PALETA.get(tono, tono), line=dict(width=0), cornerradius=4),
            hovertemplate=f"%{{y}} {unidad}<extra>{nombre}</extra>",
        ))
    fig.update_layout(barmode="stack" if apiladas else "group")
    mostrar(_tema(fig, alto, unidad, formato_x=FORMATO_X.get(rango)), clave)


def barras_horizontales(etiquetas, valores, unidad="", tono="azul", alto=280, clave="barras_h"):
    if not disponible():
        return
    c = PALETA.get(tono, tono)
    orden = sorted(zip(valores, etiquetas))
    fig = go.Figure(go.Bar(
        x=[v for v, _ in orden], y=[e for _, e in orden], orientation="h",
        marker=dict(color=[rgba(c, 0.35 + 0.65 * (i + 1) / len(orden)) for i in range(len(orden))],
                    line=dict(width=0), cornerradius=4),
        text=[f"{v:g}" for v, _ in orden], textposition="outside", textfont=dict(color=TEXTO, size=11),
        hovertemplate=f"%{{x}} {unidad}<extra>%{{y}}</extra>", cliponaxis=False,
    ))
    _tema(fig, alto, "", leyenda=False, hover="closest")
    fig.update_xaxes(showgrid=True, gridcolor=REJILLA, title=dict(text=unidad, font=dict(size=11, color=TENUE)))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    mostrar(fig, clave)


def barras_agrupadas(categorias, grupos, unidad="", alto=300, rango_y=None, clave="barras_g"):
    """grupos: lista de (nombre, valores, color)."""
    if not disponible():
        return
    fig = go.Figure()
    for nombre, valores, tono in grupos:
        fig.add_trace(go.Bar(
            x=categorias, y=valores, name=nombre,
            marker=dict(color=PALETA.get(tono, tono), line=dict(width=0), cornerradius=4),
            hovertemplate=f"%{{y:.1f}} {unidad}<extra>{nombre}</extra>",
        ))
    fig.update_layout(barmode="group", bargroupgap=0.08)
    mostrar(_tema(fig, alto, unidad, hover="x unified", rango_y=rango_y), clave)


def dona(etiquetas, valores, tonos, centro="", subtitulo="", unidad="", alto=280, clave="dona"):
    if not disponible():
        return
    fig = go.Figure(go.Pie(
        labels=etiquetas, values=valores, hole=0.72, sort=False, direction="clockwise",
        marker=dict(colors=[PALETA.get(t, t) for t in tonos], line=dict(color="#0A0E17", width=3)),
        textinfo="none", hovertemplate=f"%{{label}}: %{{value}} {unidad} (%{{percent}})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{centro}</b>", x=0.5, y=0.55, showarrow=False,
                       font=dict(size=26, color="#E5E9F0", family="Inter, system-ui, sans-serif"))
    fig.add_annotation(text=subtitulo, x=0.5, y=0.40, showarrow=False, font=dict(size=11, color=TENUE))
    _tema(fig, alto, leyenda=True, hover="closest")
    fig.update_layout(legend=dict(orientation="h", y=-0.05, yanchor="top", x=0.5, xanchor="center"),
                      margin=dict(l=4, r=4, t=4, b=4))
    mostrar(fig, clave)


def medidor(valor, referencia, titulo="", unidad="%", alto=230, clave="medidor"):
    """Medidor semicircular (0-100) con la diferencia contra la referencia."""
    if not disponible():
        return
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=valor,
        number=dict(suffix=f" {unidad}", font=dict(size=34, color="#E5E9F0"), valueformat=".1f"),
        delta=dict(reference=referencia, valueformat=".1f", suffix=" pts",
                   increasing=dict(color=PALETA["verde"]), decreasing=dict(color=PALETA["rojo"])),
        title=dict(text=titulo, font=dict(size=12, color=TENUE)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, tickcolor="rgba(0,0,0,0)", tickfont=dict(color=TENUE, size=10)),
            bar=dict(color=PALETA["cian"], thickness=0.28),
            bgcolor="rgba(148,163,184,0.08)", borderwidth=0,
            steps=[dict(range=[0, referencia], color="rgba(76,141,255,0.10)")],
            threshold=dict(line=dict(color=PALETA["violeta"], width=3), thickness=0.85, value=referencia),
        ),
    ))
    fig.update_layout(height=alto, margin=dict(l=18, r=18, t=36, b=4), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif"))
    mostrar(fig, clave)


def selector_rango(clave, defecto="24 h"):
    """Control segmentado con los 4 rangos. Devuelve '1h', '24h', '7d' o '30d'."""
    eleccion = st.segmented_control("Rango", list(RANGOS), default=defecto, key=clave,
                                    label_visibility="collapsed")
    return RANGOS.get(eleccion or defecto)
