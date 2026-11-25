"""Sistema visual de Kardex Vivo: paleta, CSS global, iconos y piezas HTML reutilizables.

Todas las pantallas usan estas funciones para verse igual. Para cambiar un color,
cámbialo en PALETA y en el bloque :root del CSS.
"""
from html import escape

import streamlit as st

PALETA = {
    "fondo": "#080718",
    "superficie": "#120F2E",
    "superficie2": "#1A1640",
    "borde": "rgba(167, 139, 250, 0.16)",
    "texto": "#ECEAFB",
    "tenue": "#9A95BD",
    "azul": "#8B5CF6",      # acento principal: violeta
    "cian": "#C4B5FD",      # lavanda
    "violeta": "#E879F9",   # orquídea
    "indigo": "#6366F1",
    "verde": "#34D399",
    "ambar": "#FBBF24",
    "rojo": "#F87171",
}

# Iconos de trazo (estilo Lucide), 24x24
_ICONOS = {
    "actividad": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "alerta": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
              '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "reloj": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "caja": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
            '<polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "datos": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>'
             '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    "orden": '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
             '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    "tendencia": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "rayo": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "escudo": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    "qr": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/>'
          '<path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/>',
    "sensor": '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49"/><path d="M7.76 16.24a6 6 0 0 1 0-8.49"/>'
              '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M4.93 19.07a10 10 0 0 1 0-14.14"/>',
    "dinero": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "medidor": '<path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "capas": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "flecha": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "filtro": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "descarga": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "cruce": '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/>'
             '<line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>'
           '<line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>'
           '<line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>',
}

COLOR_ESTADO = {"OK": "verde", "FALLO": "rojo", "PENDIENTE": "tenue", "SOSPECHOSO": "rojo"}


def icono(nombre, tamano=18, color="currentColor", grosor=1.8):
    trazo = _ICONOS.get(nombre, _ICONOS["actividad"])
    return (f'<svg width="{tamano}" height="{tamano}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{grosor}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{trazo}</svg>')


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --kv-fondo: #080718; --kv-sup: #120F2E; --kv-sup2: #1A1640;
  --kv-borde: rgba(167,139,250,.16); --kv-borde2: rgba(167,139,250,.30);
  --kv-texto: #ECEAFB; --kv-tenue: #9A95BD;
  --kv-azul: #8B5CF6; --kv-cian: #C4B5FD; --kv-violeta: #E879F9; --kv-indigo: #6366F1;
  --kv-verde: #34D399; --kv-ambar: #FBBF24; --kv-rojo: #F87171;
  --kv-radio: 14px;
  --kv-sombra: inset 0 1px 0 rgba(255,255,255,.05), 0 1px 2px rgba(0,0,0,.4), 0 22px 48px -28px rgba(124,58,237,.55);
  --kv-vidrio: linear-gradient(160deg, rgba(43,35,102,.55), rgba(18,15,46,.62));
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}
.stApp {
  background:
    radial-gradient(900px 520px at 8% -12%, rgba(124,58,237,.28), transparent 62%),
    radial-gradient(820px 460px at 100% 0%, rgba(99,102,241,.20), transparent 60%),
    radial-gradient(1200px 380px at 50% 112%, rgba(139,92,246,.22), transparent 70%),
    var(--kv-fondo);
  background-attachment: fixed;
}
.stApp::before { content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image: linear-gradient(rgba(167,139,250,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(167,139,250,.035) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at 50% 0%, #000 30%, transparent 75%); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"], footer, #MainMenu { display: none !important; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }
@media (max-width: 640px) { .block-container { padding: 1.2rem .9rem 2.5rem; } }

/* Barra lateral */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(22,18,56,.92) 0%, rgba(10,8,28,.95) 100%); backdrop-filter: blur(18px);
  border-right: 1px solid var(--kv-borde);
}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {
  border-radius: 10px; transition: background .18s ease, color .18s ease;
}
[data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNavLink"]:hover { background: rgba(139,92,246,.12); }
[data-testid="stSidebarNavLink"][aria-current="page"], [data-testid="stSidebarNav"] a[aria-current="page"] {
  background: linear-gradient(90deg, rgba(139,92,246,.28), rgba(99,102,241,.10)) !important;
  box-shadow: inset 0 0 0 1px rgba(167,139,250,.35), 0 8px 22px -12px rgba(139,92,246,.8);
}
[data-testid="stSidebarNavSeparator"], [data-testid="stSidebarNavItems"] header { color: var(--kv-tenue); }

/* Títulos */
h1, h2, h3 { letter-spacing: -.02em; color: var(--kv-texto); }
h3 { font-size: 1.02rem !important; font-weight: 600 !important; }

/* Refresco automático sin parpadeo: Streamlit atenúa lo que se está recalculando */
[data-stale="true"], .stale-element, [data-testid="stElementContainer"][data-stale] { opacity: 1 !important; transition: none !important; }

/* Animaciones */
@keyframes kv-entrar { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes kv-pulso { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
@keyframes kv-anillo { 0% { box-shadow: 0 0 0 0 rgba(196,181,253,.45); } 100% { box-shadow: 0 0 0 10px rgba(196,181,253,0); } }
@keyframes kv-brillo { from { background-position: -200% 0; } to { background-position: 200% 0; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

/* Contenedores con key que empieza en "tarjeta" */
[class*="st-key-tarjeta"] {
  background: var(--kv-vidrio); backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%);
  border: 1px solid var(--kv-borde); border-radius: var(--kv-radio);
  padding: 1.1rem 1.2rem 1.2rem; box-shadow: var(--kv-sombra);
  animation: kv-entrar .45s ease both;
}

/* Métricas nativas */
[data-testid="stMetric"] {
  background: var(--kv-vidrio); backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%);
  border: 1px solid var(--kv-borde); border-radius: 12px; padding: .8rem 1rem;
}
[data-testid="stMetricLabel"] p { color: var(--kv-tenue) !important; font-size: .78rem !important; }
[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -.02em; }

/* Botones */
.stButton > button, .stFormSubmitButton > button, [data-testid="stBaseButton-secondary"] {
  border-radius: 10px !important; border: 1px solid var(--kv-borde2) !important;
  background: rgba(30,25,72,.55) !important; color: var(--kv-texto) !important;
  transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: rgba(139,92,246,.55) !important; transform: translateY(-1px);
  box-shadow: 0 6px 18px -10px rgba(139,92,246,.7);
}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #C084FC 100%) !important;
  border: 0 !important; color: #fff !important; font-weight: 600 !important;
  box-shadow: 0 8px 22px -10px rgba(139,92,246,.9) !important;
}

/* Entradas */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  border-radius: 10px !important; background: rgba(14,12,36,.75) !important;
  border-color: var(--kv-borde2) !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {
  border-color: var(--kv-azul) !important; box-shadow: 0 0 0 3px rgba(139,92,246,.18) !important;
}
input { font-family: 'JetBrains Mono', ui-monospace, monospace !important; }

/* Expander, tablas, gráficas */
[data-testid="stExpander"] details {
  border: 1px solid var(--kv-borde) !important; border-radius: 12px !important;
  background: rgba(24,20,56,.45);
}
[data-testid="stDataFrame"] { border: 1px solid var(--kv-borde); border-radius: 12px; overflow: hidden; }
[data-testid="stPlotlyChart"] { animation: kv-entrar .6s ease both; }
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stProgress"] > div > div > div > div { background: linear-gradient(90deg, var(--kv-azul), var(--kv-cian)); }
hr { border-color: var(--kv-borde) !important; }

/* ---------- Piezas propias ---------- */
[class^="kv-"], [class^="kv-"] *, [class*=" kv-"] { box-sizing: border-box; }
.kv-encabezado { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem;
  flex-wrap:wrap; margin-bottom:1.4rem; animation: kv-entrar .4s ease both; }
.kv-encabezado .kv-eyebrow { color: var(--kv-cian); font-size:.72rem; font-weight:600;
  letter-spacing:.14em; text-transform:uppercase; margin-bottom:.35rem; }
.kv-encabezado h1 { font-size: clamp(1.45rem, 2.4vw, 1.9rem); font-weight:600; margin:0; padding:0; }
.kv-encabezado p { color: var(--kv-tenue); margin:.3rem 0 0; font-size:.92rem; max-width: 640px; }
.kv-pildoras { display:flex; gap:.45rem; flex-wrap:wrap; }

.kv-pildora { display:inline-flex; align-items:center; gap:.4rem; padding:.28rem .65rem;
  border-radius:999px; font-size:.74rem; font-weight:500; border:1px solid var(--kv-borde2);
  background: rgba(30,25,72,.6); color: var(--kv-texto); white-space:nowrap; }
.kv-punto { width:7px; height:7px; border-radius:50%; display:inline-block; }
.kv-punto.vivo { animation: kv-pulso 1.6s ease-in-out infinite; }

.kv-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: .9rem; margin: .2rem 0 1.1rem; }
.kv-kpi { position:relative; overflow:hidden; padding:1rem 1.1rem; border-radius: var(--kv-radio);
  background: var(--kv-vidrio); backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%);
  border:1px solid var(--kv-borde); box-shadow: var(--kv-sombra);
  transition: transform .2s ease, border-color .2s ease; animation: kv-entrar .45s ease both; }
.kv-kpi:hover { transform: translateY(-2px); border-color: var(--kv-borde2); box-shadow: var(--kv-sombra), 0 0 0 1px rgba(167,139,250,.18), 0 18px 40px -22px rgba(139,92,246,.9); }
.kv-kpi::before { content:""; position:absolute; inset:0 0 auto 0; height:2px;
  background: linear-gradient(90deg, transparent, var(--kv-acento, var(--kv-azul)), transparent); opacity:.95; }
.kv-kpi::after { content:""; position:absolute; width:160px; height:160px; right:-60px; top:-70px; border-radius:50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--kv-acento, #8B5CF6) 22%, transparent), transparent 70%); pointer-events:none; }
.kv-kpi .kv-kpi-top { display:flex; align-items:center; justify-content:space-between; color: var(--kv-tenue); font-size:.78rem; }
.kv-kpi .kv-kpi-icono { width:30px; height:30px; border-radius:9px; display:grid; place-items:center;
  background: color-mix(in srgb, var(--kv-acento, #8B5CF6) 14%, transparent); color: var(--kv-acento, var(--kv-azul)); }
.kv-kpi .kv-kpi-valor { font-size: 1.75rem; font-weight:600; letter-spacing:-.03em; margin-top:.45rem; line-height:1.1; }
.kv-kpi .kv-kpi-valor small { font-size:.85rem; color: var(--kv-tenue); font-weight:500; margin-left:.25rem; }
.kv-kpi .kv-kpi-pie { margin-top:.35rem; font-size:.76rem; color: var(--kv-tenue); }
.kv-sube { color: var(--kv-verde); } .kv-baja { color: var(--kv-rojo); }

.kv-seccion { display:flex; align-items:center; gap:.55rem; margin: .4rem 0 .7rem; }
.kv-seccion .kv-seccion-icono { color: var(--kv-cian); display:flex; }
.kv-seccion h3 { margin:0 !important; padding:0 !important; }
.kv-seccion span.kv-nota { margin-left:auto; color: var(--kv-tenue); font-size:.75rem; }

.kv-checks { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:.7rem; margin:.4rem 0 .9rem; }
.kv-check { padding:.85rem .95rem; border-radius:12px; border:1px solid var(--kv-borde);
  background: rgba(24,20,56,.55); backdrop-filter: blur(10px); display:flex; align-items:center; gap:.7rem; transition: all .3s ease; }
.kv-check .kv-check-icono { width:32px; height:32px; border-radius:50%; display:grid; place-items:center; flex:none; }
.kv-check .kv-check-nombre { font-size:.8rem; color: var(--kv-tenue); }
.kv-check .kv-check-estado { font-size:.92rem; font-weight:600; }
.kv-check.ok { border-color: rgba(52,211,153,.35); background: rgba(52,211,153,.06); }
.kv-check.ok .kv-check-icono { background: rgba(52,211,153,.15); color: var(--kv-verde); }
.kv-check.fallo { border-color: rgba(248,113,113,.4); background: rgba(248,113,113,.07); }
.kv-check.fallo .kv-check-icono { background: rgba(248,113,113,.15); color: var(--kv-rojo); }
.kv-check.pendiente .kv-check-icono { background: rgba(196,181,253,.10); color: var(--kv-cian); animation: kv-anillo 1.4s ease-out infinite; }

.kv-pasos { display:flex; gap:.5rem; margin: 0 0 1.2rem; flex-wrap:wrap; }
.kv-paso { flex:1 1 140px; display:flex; align-items:center; gap:.55rem; padding:.55rem .75rem; border-radius:10px;
  border:1px solid var(--kv-borde); color: var(--kv-tenue); font-size:.8rem; background: rgba(24,20,56,.45); }
.kv-paso b { width:22px; height:22px; border-radius:50%; display:grid; place-items:center; font-size:.72rem;
  background: rgba(148,163,184,.12); color: var(--kv-tenue); flex:none; }
.kv-paso.activo { border-color: rgba(139,92,246,.55); color: var(--kv-texto); background: rgba(139,92,246,.08); }
.kv-paso.activo b { background: var(--kv-azul); color:#fff; }
.kv-paso.hecho b { background: rgba(52,211,153,.2); color: var(--kv-verde); }

.kv-linea { position:relative; margin:.2rem 0 .6rem; padding-left:1.1rem; }
.kv-linea::before { content:""; position:absolute; left:5px; top:4px; bottom:4px; width:1px; background: var(--kv-borde2); }
.kv-evento { position:relative; display:flex; align-items:center; gap:.7rem; padding:.45rem 0; animation: kv-entrar .35s ease both; }
.kv-evento::before { content:""; position:absolute; left:-1.1rem; margin-left:1px; width:9px; height:9px; border-radius:50%;
  background: var(--kv-color, var(--kv-azul)); box-shadow: 0 0 0 3px rgba(8,7,24,1); }
.kv-evento .kv-hora { font-family:'JetBrains Mono', monospace; font-size:.75rem; color: var(--kv-tenue); width:62px; flex:none; }
.kv-evento .kv-tipo { font-weight:500; font-size:.86rem; }
.kv-evento .kv-valor { font-family:'JetBrains Mono', monospace; font-size:.82rem; margin-left:auto; }

.kv-banner { display:flex; align-items:center; gap:1rem; padding:1.1rem 1.2rem; border-radius: var(--kv-radio);
  margin: .2rem 0 1rem; animation: kv-entrar .45s ease both; }
.kv-banner .kv-banner-icono { width:44px; height:44px; border-radius:12px; display:grid; place-items:center; flex:none; }
.kv-banner h4 { margin:0; font-size:1.05rem; font-weight:600; }
.kv-banner p { margin:.15rem 0 0; color: var(--kv-tenue); font-size:.86rem; }
.kv-banner.ok { background: rgba(52,211,153,.08); border:1px solid rgba(52,211,153,.35); }
.kv-banner.ok .kv-banner-icono { background: rgba(52,211,153,.16); color: var(--kv-verde); }
.kv-banner.mal { background: rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.38); }
.kv-banner.mal .kv-banner-icono { background: rgba(248,113,113,.16); color: var(--kv-rojo); }
.kv-banner.info { background: rgba(139,92,246,.07); border:1px solid rgba(139,92,246,.3); }
.kv-banner.info .kv-banner-icono { background: rgba(139,92,246,.15); color: var(--kv-azul); }

.kv-nav { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:.9rem; }
.kv-nav a { text-decoration:none !important; display:block; }
.kv-nav-item { display:block; height:100%; padding:1.05rem 1.1rem; border-radius: var(--kv-radio); border:1px solid var(--kv-borde);
  background: var(--kv-vidrio); backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%); color: var(--kv-texto);
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; animation: kv-entrar .5s ease both; }
.kv-nav-item:hover { transform: translateY(-3px); border-color: rgba(139,92,246,.45); box-shadow: 0 14px 30px -18px rgba(139,92,246,.6); }
.kv-nav-item .kv-nav-icono { width:36px; height:36px; border-radius:10px; display:grid; place-items:center; margin-bottom:.7rem;
  background: color-mix(in srgb, var(--kv-acento, #8B5CF6) 14%, transparent); color: var(--kv-acento, var(--kv-azul)); }
.kv-nav-item h4 { margin:0 0 .25rem; font-size:.98rem; font-weight:600; color: var(--kv-texto); }
.kv-nav-item p { margin:0; color: var(--kv-tenue); font-size:.83rem; line-height:1.45; }
.kv-nav-item .kv-ir { margin-top:.7rem; display:flex; align-items:center; gap:.3rem; color: var(--kv-azul); font-size:.8rem; font-weight:500; }

.kv-flujo { display:flex; align-items:stretch; gap:.4rem; flex-wrap:wrap; margin:.3rem 0 .4rem; }
.kv-flujo-paso { flex:1 1 150px; display:flex; flex-direction:column; align-items:center; text-align:center; gap:.45rem;
  padding:.9rem .7rem; border-radius:14px; border:1px solid var(--kv-borde); background: rgba(24,20,56,.5);
  animation: kv-entrar .5s ease both; }
.kv-flujo-paso .kv-flujo-icono { width:40px; height:40px; border-radius:12px; display:grid; place-items:center;
  background: rgba(139,92,246,.16); color: var(--kv-cian); box-shadow: inset 0 0 0 1px rgba(167,139,250,.3), 0 0 18px -4px rgba(139,92,246,.6); }
.kv-flujo-paso b { font-size:.84rem; font-weight:600; }
.kv-flujo-paso span { font-size:.74rem; color: var(--kv-tenue); line-height:1.35; }
.kv-flujo-flecha { display:flex; align-items:center; color: rgba(167,139,250,.55); }
@media (max-width: 640px) { .kv-flujo-flecha { display:none; } .kv-flujo-paso { flex:1 1 calc(50% - .4rem); } }
.kv-barra { height:6px; border-radius:99px; background: rgba(167,139,250,.12); overflow:hidden; }
.kv-barra > i { display:block; height:100%; border-radius:99px; background: linear-gradient(90deg, #6366F1, #8B5CF6, #C084FC);
  box-shadow: 0 0 12px rgba(139,92,246,.7); }
.kv-mono { font-family:'JetBrains Mono', monospace; }
.kv-tenue { color: var(--kv-tenue); font-size:.82rem; }
@media (max-width: 640px) {
  .kv-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); gap:.6rem; }
  .kv-kpi { padding:.8rem .85rem; }
  .kv-kpi .kv-kpi-valor { font-size:1.35rem; }
  .kv-kpi .kv-kpi-pie { font-size:.7rem; }
  .kv-paso { flex:1 1 calc(50% - .5rem); padding:.45rem .55rem; font-size:.74rem; }
  .kv-checks { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kv-banner { padding:.9rem; gap:.75rem; }
  .kv-evento .kv-hora { width:54px; }
}
.kv-esqueleto { height:14px; border-radius:6px; background: linear-gradient(90deg, rgba(148,163,184,.06), rgba(148,163,184,.16), rgba(148,163,184,.06));
  background-size: 200% 100%; animation: kv-brillo 1.4s linear infinite; }
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def html(contenido):
    st.markdown(contenido, unsafe_allow_html=True)


def color(nombre):
    return PALETA.get(nombre, nombre)


def pildora(texto, tono="azul", vivo=False):
    clase = "kv-punto vivo" if vivo else "kv-punto"
    return (f'<span class="kv-pildora"><span class="{clase}" style="background:{color(tono)}"></span>'
            f'{escape(str(texto))}</span>')


def encabezado(titulo, subtitulo="", seccion="", pildoras=""):
    ceja = f'<div class="kv-eyebrow">{escape(seccion)}</div>' if seccion else ""
    sub = f"<p>{escape(subtitulo)}</p>" if subtitulo else ""
    html(f'<div class="kv-encabezado"><div>{ceja}<h1>{escape(titulo)}</h1>{sub}</div>'
         f'<div class="kv-pildoras">{pildoras}</div></div>')


def seccion(titulo, icono_nombre="actividad", nota=""):
    extra = f'<span class="kv-nota">{escape(nota)}</span>' if nota else ""
    html(f'<div class="kv-seccion"><span class="kv-seccion-icono">{icono(icono_nombre, 18)}</span>'
         f'<h3>{escape(titulo)}</h3>{extra}</div>')


def kpis(tarjetas):
    """tarjetas: lista de dicts con etiqueta, valor, unidad, pie, icono, acento, tendencia ('+' o '-')."""
    partes = []
    for i, t in enumerate(tarjetas):
        tendencia = t.get("tendencia")
        clase = "kv-sube" if tendencia == "+" else "kv-baja" if tendencia == "-" else ""
        unidad = f"<small>{escape(str(t['unidad']))}</small>" if t.get("unidad") else ""
        acento = color(t.get("acento", "azul"))
        partes.append(
            f'<div class="kv-kpi" style="--kv-acento:{acento};animation-delay:{i * 60}ms">'
            f'<div class="kv-kpi-top"><span>{escape(t["etiqueta"])}</span>'
            f'<span class="kv-kpi-icono">{icono(t.get("icono", "actividad"), 16)}</span></div>'
            f'<div class="kv-kpi-valor">{escape(str(t["valor"]))}{unidad}</div>'
            f'<div class="kv-kpi-pie"><span class="{clase}">{escape(t.get("pie", ""))}</span></div></div>'
        )
    html(f'<div class="kv-kpis">{"".join(partes)}</div>')


def banner(tipo, titulo, texto="", icono_nombre=None):
    icono_nombre = icono_nombre or {"ok": "escudo", "mal": "alerta", "info": "sensor"}[tipo]
    parrafo = f"<p>{escape(texto)}</p>" if texto else ""
    html(f'<div class="kv-banner {tipo}"><div class="kv-banner-icono">{icono(icono_nombre, 22)}</div>'
         f'<div><h4>{escape(titulo)}</h4>{parrafo}</div></div>')


def pasos(lista, actual):
    """lista de nombres; actual = índice del paso en curso (0..n). Los anteriores quedan hechos."""
    partes = []
    for i, nombre in enumerate(lista):
        clase = "hecho" if i < actual else "activo" if i == actual else ""
        marca = icono("check", 12, grosor=3) if i < actual else str(i + 1)
        partes.append(f'<div class="kv-paso {clase}"><b>{marca}</b>{escape(nombre)}</div>')
    html(f'<div class="kv-pasos">{"".join(partes)}</div>')


def flujo(pasos_lista):
    """Diagrama horizontal de proceso: lista de (icono, titulo, texto)."""
    partes = []
    for i, (ic, titulo, texto) in enumerate(pasos_lista):
        if i:
            partes.append(f'<div class="kv-flujo-flecha">{icono("flecha", 18)}</div>')
        partes.append(f'<div class="kv-flujo-paso" style="animation-delay:{i * 80}ms">'
                      f'<div class="kv-flujo-icono">{icono(ic, 20)}</div><b>{escape(titulo)}</b>'
                      f'<span>{escape(texto)}</span></div>')
    html(f'<div class="kv-flujo">{"".join(partes)}</div>')


def barra(fraccion):
    return f'<div class="kv-barra"><i style="width:{max(0, min(1, fraccion)) * 100:.0f}%"></i></div>'


def tarjeta(clave):
    """Contenedor con estilo de tarjeta. Uso: with tarjeta("resumen"): ..."""
    return st.container(key=f"tarjeta_{clave}")
