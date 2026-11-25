import re

# Formato del QR: KV-<orden_compra>-<articulo>-<lote>, ej. KV-1042-1001-0001
PATRON_QR = re.compile(r"^KV-(\d{3,6})-(\d{3,6})-(\d{4})$")

TIPOS_OT = {
    "RECEPCION_SOSPECHOSA": "Recepción sospechosa",
    "DUPLICADO": "Duplicado",
    "DIFERENCIA_CANTIDAD": "Diferencia de cantidad",
    "REGISTRO_INCOMPLETO": "Registro incompleto",
    "INCONSISTENCIA_COSTO": "Inconsistencia de costo",
}

ESTADOS_OT = ["ABIERTA", "EN_REVISION", "CERRADA"]
PRIORIDADES_OT = ["ALTA", "MEDIA", "BAJA"]


def interpretar_qr(texto):
    """Devuelve {'orden_compra', 'articulo', 'lote'} o None si el formato no es válido."""
    if not texto:
        return None
    m = PATRON_QR.match(texto.strip().upper())
    if not m:
        return None
    return {"orden_compra": m.group(1), "articulo": m.group(2), "lote": m.group(3)}
