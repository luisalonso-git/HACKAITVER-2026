"""Genera los QR de los escenarios de demo en la carpeta qr/.
Cada QR contiene una URL: al escanearlo con la cámara del celular se abre la pantalla
de recepción con el código ya cargado. Antes de correrlo, ajusta FRONT_URL en config.py.

Uso:  python generar_qr.py
"""
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

import config

ESCENARIOS = [
    ("KV-1042-1001-0001", "Correcto (escanéalo 2 veces = duplicado)"),
    ("KV-1042-1002-0002", "Peso bajo (faltante)"),
    ("KV-1043-1003-0003", "Sin producto en la báscula"),
    ("KV-9999-1001-0001", "Orden de compra inexistente"),
    ("KV-1044-1004-0001", "Correcto"),
]

carpeta = Path(__file__).parent / "qr"
carpeta.mkdir(exist_ok=True)

try:
    fuente = ImageFont.load_default(size=20)
except TypeError:  # Pillow antiguo
    fuente = ImageFont.load_default()

for codigo, descripcion in ESCENARIOS:
    url = f"{config.FRONT_URL}/recepcion?qr={codigo}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")

    lienzo = Image.new("RGB", (imagen.width, imagen.height + 70), "white")
    lienzo.paste(imagen, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.text((20, imagen.height), codigo, fill="black", font=fuente)
    dibujo.text((20, imagen.height + 30), descripcion, fill="black", font=fuente)

    archivo = carpeta / f"{codigo}.png"
    lienzo.save(archivo)
    print(f"{archivo.name}  ->  {url}")

print(f"\nListo: {len(ESCENARIOS)} QR en {carpeta}")
