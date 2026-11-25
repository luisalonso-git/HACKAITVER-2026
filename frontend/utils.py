"""Nombres y formatos del contrato (Hackaton/CONTRATO.md)."""
import re

# El QR solo contiene el identificador del bulto, ej. B-0001
PATRON_QR = re.compile(r"^B-\d{4}$")

TIPOS_OT = {
    "duplicado": "Duplicado",
    "sin_respaldo_fisico": "Sin respaldo físico",
    "cantidad_distinta": "Cantidad distinta",
    "dato_incompleto": "Dato incompleto",
    "inspeccion": "Inspección (manipulación)",
}
ESTADOS_OT = ["abierta", "en_revision", "cerrada"]
NOMBRE_ESTADO = {"abierta": "Abierta", "en_revision": "En revisión", "cerrada": "Cerrada"}
PRIORIDADES_OT = ["alta", "media", "baja"]

TIPOS_EVENTO = {
    "presencia": ("Presencia", "g"),
    "peso": ("Peso", "kg"),
    "golpe": ("Golpe", "g"),
    "inclinacion": ("Inclinación", "°"),
}
NOMBRE_ORIGEN = {"simulado": "Simulado", "fisico": "Físico", "datos": "Datos (CSV)", "escaneo": "Escaneo"}

CHEQUEOS = [
    ("qr", "QR válido"),
    ("presencia", "Presencia"),
    ("peso", "Peso"),
    ("manipulacion", "Manipulación"),
]

# Escenarios de Hackaton/iot_hackaitver/iot/simulador.py
ESCENARIOS_SIMULADOR = {
    "normal": "Normal: presencia y peso correcto",
    "sin_presencia": "Sin presencia: se escanea pero no llega el bulto",
    "peso_bajo": "Peso bajo: 20 % menos",
    "peso_alto": "Peso alto: 25 % más",
    "golpe": "Golpe: manipulación brusca (3.8 g)",
    "inclinado": "Inclinado: el bulto se inclina 40°",
    "ruidoso": "Ruidoso: normal con 3 veces más ruido",
}


def codigo_valido(texto):
    return bool(texto) and bool(PATRON_QR.match(texto.strip().upper()))


def origen_de_ot(ot):
    """Origen que se muestra en pantalla: físico, simulado o datos (CSV)."""
    origenes = {e.get("origen") for e in (ot.get("evidencia") or [])}
    for o in ("fisico", "simulado", "datos"):
        if o in origenes:
            return o
    return "escaneo" if ot.get("bulto_id") else "datos"


def hora(ts):
    """'2026-11-25T11:03:12.345' -> '11:03:12'."""
    if not ts:
        return ""
    return ts.split("T")[-1][:8]
