"""Genera los QR de los bultos en la carpeta qr/.
Cada QR contiene una URL: al escanearlo con la cámara del celular se abre la pantalla
de recepción con el código del bulto ya cargado. Antes de correrlo, ajusta FRONT_URL en config.py.

Uso:  python generar_qr.py
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

import api
import config

try:
    BULTOS = [(b["bulto_id"], b["descripcion"]) for b in api.listar_bultos()]
    print("Bultos tomados del backend.")
except api.ErrorAPI:
    print("Backend apagado: uso la lista de respaldo.")
    BULTOS = [(f"B-000{i}", "") for i in range(1, 7)]
BULTOS.append(("B-9999", "No existe en la base (demo de dato incompleto)"))

carpeta = Path(__file__).parent / "qr"
carpeta.mkdir(exist_ok=True)

try:
    fuente = ImageFont.load_default(size=20)
except TypeError:  # Pillow antiguo
    fuente = ImageFont.load_default()

for codigo, descripcion in BULTOS:
    url = f"{config.FRONT_URL}/recepcion?qr={codigo}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")

    lienzo = Image.new("RGB", (imagen.width, imagen.height + 70), "white")
    lienzo.paste(imagen, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.text((20, imagen.height), codigo, fill="black", font=fuente)
    dibujo.text((20, imagen.height + 30), descripcion[:40], fill="black", font=fuente)

    archivo = carpeta / f"{codigo}.png"
    lienzo.save(archivo)
    print(f"{archivo.name}  ->  {url}")

print(f"\nListo: {len(BULTOS)} QR en {carpeta}")
