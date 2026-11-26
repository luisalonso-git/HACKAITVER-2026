from html import escape

from estilo import PALETA, html, icono, pildora
from utils import CHEQUEOS, NOMBRE_ORIGEN, TIPOS_EVENTO, hora

COLOR_EVENTO = {"presencia": "cian", "peso": "azul", "golpe": "rojo", "inclinacion": "ambar"}
TEXTO_CHECK = {"OK": "Correcto", "FALLO": "Falló", "PENDIENTE": "Esperando"}
ICONO_CHECK = {"OK": "check", "FALLO": "x", "PENDIENTE": "reloj"}


def mostrar_checks(checks):
    partes = []
    for i, (llave, nombre) in enumerate(CHEQUEOS):
        estado = checks.get(llave, "PENDIENTE")
        clase = {"OK": "ok", "FALLO": "fallo"}.get(estado, "pendiente")
        partes.append(
            f'<div class="kv-check {clase}" style="animation:kv-entrar .4s ease {i * 70}ms both">'
            f'<div class="kv-check-icono">{icono(ICONO_CHECK.get(estado, "reloj"), 16, grosor=2.4)}</div>'
            f'<div><div class="kv-check-nombre">{escape(nombre)}</div>'
            f'<div class="kv-check-estado">{TEXTO_CHECK.get(estado, estado)}</div></div></div>'
        )
    html(f'<div class="kv-checks">{"".join(partes)}</div>')


def linea_eventos(eventos, mostrar_estacion=False, vacio="Esperando eventos de la estación…", limite=None):
    if not eventos:
        html(f'<div class="kv-tenue" style="padding:.6rem 0">{escape(vacio)}</div>'
             '<div class="kv-esqueleto" style="width:70%;margin:.3rem 0"></div>'
             '<div class="kv-esqueleto" style="width:45%;margin:.5rem 0"></div>')
        return
    filas = []
    for e in (eventos[:limite] if limite else eventos):
        nombre, unidad = TIPOS_EVENTO.get(e.get("tipo"), (e.get("tipo"), ""))
        tono = PALETA[COLOR_EVENTO.get(e.get("tipo"), "azul")]
        estacion = (f'<span class="kv-pildora" style="padding:.1rem .5rem">{escape(str(e.get("estacion", "")))}</span>'
                    if mostrar_estacion else "")
        origen = e.get("origen", "")
        etiqueta_origen = pildora(NOMBRE_ORIGEN.get(origen, origen), "ambar" if origen == "simulado" else "verde")
        if e.get("dispositivo"):
            etiqueta_origen += pildora(e["dispositivo"], "azul")
        filas.append(
            f'<div class="kv-evento" style="--kv-color:{tono}">'
            f'<span class="kv-hora">{hora(e.get("ts"))}</span>{estacion}'
            f'<span class="kv-tipo">{escape(nombre)}</span>{etiqueta_origen}'
            f'<span class="kv-valor" style="color:{tono}">{e.get("magnitud")} {unidad}</span></div>'
        )
    html(f'<div class="kv-linea">{"".join(filas)}</div>')


def aviso_origen(eventos):
    """El contrato pide mostrar siempre si los datos son simulados o físicos."""
    origenes = {e.get("origen") for e in eventos}
    partes = []
    if "simulado" in origenes:
        partes.append(pildora("Sensor simulado · peso simulado sin celda de carga", "ambar"))
    if "fisico" in origenes:
        partes.append(pildora("Sensor físico · ESP32 + MPU6050", "verde", vivo=True))
    if partes:
        html(f'<div class="kv-pildoras" style="margin:.2rem 0 .6rem">{"".join(partes)}</div>')


def estado_conexion(activo, simulador_ok, estacion):
    partes = [
        pildora("Backend en línea" if activo else "Backend sin conexión", "verde" if activo else "rojo", vivo=activo),
        pildora(f"Estación {estacion}", "cian"),
    ]
    if not simulador_ok:
        partes.append(pildora("Simulador no encontrado", "ambar"))
    return "".join(partes)
