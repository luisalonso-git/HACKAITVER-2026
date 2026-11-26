"""Lectura de QR desde una foto de la cámara (OpenCV) y extracción del código del bulto."""
from urllib.parse import parse_qs, urlparse

try:
    import cv2
    import numpy as np
    HAY_LECTOR = True
except ImportError:
    HAY_LECTOR = False


def extraer_codigo(texto):
    """El QR puede traer la URL de Recepción (…/recepcion?qr=B-0001) o solo el código."""
    texto = (texto or "").strip()
    if "qr=" in texto:
        valores = parse_qs(urlparse(texto).query).get("qr")
        if valores:
            return valores[0].strip().upper()
    return texto.upper() or None


def leer_qr(imagen_bytes):
    """Devuelve el código del bulto que aparece en la foto, o None si no encuentra un QR legible."""
    if not HAY_LECTOR or not imagen_bytes:
        return None
    imagen = cv2.imdecode(np.frombuffer(imagen_bytes, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        return None
    detector = cv2.QRCodeDetector()
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    intentos = [imagen, gris, cv2.resize(gris, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC),
                cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)]
    for img in intentos:
        try:
            texto, _, _ = detector.detectAndDecode(img)
        except cv2.error:
            continue
        if texto:
            return extraer_codigo(texto)
    return None
