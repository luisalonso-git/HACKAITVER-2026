"""Genera las etiquetas QR de los bultos en la carpeta qr/.

- qr/etiquetas_qr.pdf: hoja lista para imprimir (o abrir en otra pantalla), con todos los bultos.
- qr/B-000X.png: una imagen por bulto (solo si está instalado qrcode).

Cada QR lleva la URL de Recepción con el código: con la cámara del celular abre la pantalla con el código
cargado; con la cámara de la laptop (modo Cámara de Recepción) se lee el código de la URL.
Antes de correrlo, pon en config.py FRONT_URL = la "Network URL" que muestra Streamlit.

Uso:  python generar_qr.py      (con el backend encendido)
"""
from pathlib import Path

import api
import config
import documentos

carpeta = Path(__file__).parent / "qr"
carpeta.mkdir(exist_ok=True)

try:
    bultos = api.listar_bultos()
except api.ErrorAPI as e:
    raise SystemExit(f"Enciende el backend primero: {e}")
bultos.append({"bulto_id": "B-9999", "oc": "—", "sku": "—", "descripcion": "No existe en la base (prueba de error)"})

(carpeta / "etiquetas_qr.pdf").write_bytes(documentos.etiquetas_qr_pdf(bultos, config.FRONT_URL))
print(f"Hoja de etiquetas: {carpeta / 'etiquetas_qr.pdf'}")

try:
    import qrcode
except ImportError:
    qrcode = None
if qrcode:
    for b in bultos:
        url = f"{config.FRONT_URL}/recepcion?qr={b['bulto_id']}"
        qrcode.make(url).save(carpeta / f"{b['bulto_id']}.png")
        print(f"{b['bulto_id']}.png  ->  {url}")
print(f"\nURL usada: {config.FRONT_URL}/recepcion?qr=...  (cámbiala en config.py si no es la IP de tu laptop)")
