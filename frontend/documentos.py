"""Documentos descargables: orden de trabajo en PDF y bandeja de OT en CSV para Excel."""
import io
from datetime import datetime
from html import escape

from utils import NOMBRE_ESTADO, NOMBRE_ORIGEN, TIPOS_EVENTO, TIPOS_OT, origen_de_ot

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAY_PDF = True
except ImportError:
    HAY_PDF = False

VIOLETA = "#7C3AED"
INDIGO = "#4F46E5"
TINTA = "#1E1B3A"
GRIS = "#6B6890"
LINEA = "#DDD8F5"
FONDO_SUAVE = "#F5F3FF"
COLOR_PRIORIDAD = {"alta": "#DC2626", "media": "#D97706", "baja": "#4F46E5"}


def _fecha(ts):
    if not ts:
        return "—"
    try:
        return datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return ts


def _filas_evidencia(ot):
    filas = []
    for e in ot.get("evidencia") or []:
        if "magnitud" in e:
            nombre, unidad = TIPOS_EVENTO.get(e.get("tipo"), (e.get("tipo"), ""))
            filas.append([nombre, f"{e['magnitud']} {unidad}", NOMBRE_ORIGEN.get(e.get("origen"), e.get("origen", "")),
                          _fecha(e.get("ts"))])
        else:
            fuente = e.get("fuente") or e.get("origen", "")
            if "fila" in e:
                fuente += f" · línea {e['fila']}"
            filas.append([fuente, e.get("detalle") or e.get("codigo") or "",
                          NOMBRE_ORIGEN.get(e.get("origen"), e.get("origen", "")),
                          f"${e['impacto_mxn']:,.2f}" if e.get("impacto_mxn") else "—"])
    return filas


def nombre_archivo(ot):
    return f"{ot['id']}_{ot['tipo']}.pdf"


def pdf_orden(ot):
    """Devuelve los bytes del PDF de una orden de trabajo (contrato, sección 4)."""
    if not HAY_PDF:
        raise RuntimeError("Falta reportlab: python -m pip install reportlab")
    buf = io.BytesIO()
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")

    def encabezado(canvas, doc):
        ancho, alto = letter
        canvas.saveState()
        pasos = 40
        for i in range(pasos):  # banda superior en degradado índigo → violeta
            t = i / (pasos - 1)
            r = int(0x4F + (0x7C - 0x4F) * t); g = int(0x46 + (0x3A - 0x46) * t); b = int(0xE5 + (0xED - 0xE5) * t)
            canvas.setFillColorRGB(r / 255, g / 255, b / 255)
            canvas.rect(ancho * t, alto - 34 * mm, ancho / pasos + 1, 34 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(18 * mm, alto - 15 * mm, "Kardex Vivo")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(18 * mm, alto - 21 * mm, "Orden de trabajo · validación de datos con evidencia IoT")
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawRightString(ancho - 18 * mm, alto - 16 * mm, ot["id"])
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(ancho - 18 * mm, alto - 22 * mm, f"Generada {generado}")
        canvas.setStrokeColor(colors.HexColor(LINEA))
        canvas.line(18 * mm, 14 * mm, ancho - 18 * mm, 14 * mm)
        canvas.setFillColor(colors.HexColor(GRIS))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, 9 * mm, "HackaITVER 2026 · Kardex Vivo · documento generado automáticamente")
        canvas.drawRightString(ancho - 18 * mm, 9 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=44 * mm, bottomMargin=22 * mm, title=f"Orden de trabajo {ot['id']}",
                            author="Kardex Vivo")
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor(TINTA))
    etiqueta = ParagraphStyle("etq", parent=base, fontSize=7.5, leading=10, textColor=colors.HexColor(GRIS))
    titulo = ParagraphStyle("tit", parent=base, fontName="Helvetica-Bold", fontSize=11, leading=15,
                            textColor=colors.HexColor(VIOLETA), spaceBefore=10, spaceAfter=5)
    causa = ParagraphStyle("causa", parent=base, fontSize=11, leading=15, alignment=TA_LEFT)

    def celda(et, valor, color=None):
        v = f'<font color="{color}"><b>{escape(str(valor))}</b></font>' if color else f"<b>{escape(str(valor))}</b>"
        return [Paragraph(et.upper(), etiqueta), Paragraph(v, base)]

    prioridad = ot.get("prioridad", "")
    datos = [
        celda("Tipo", TIPOS_OT.get(ot["tipo"], ot["tipo"])),
        celda("Prioridad", prioridad.capitalize(), COLOR_PRIORIDAD.get(prioridad)),
        celda("Estado", NOMBRE_ESTADO.get(ot["estado"], ot["estado"])),
        celda("Origen", NOMBRE_ORIGEN.get(origen_de_ot(ot), "")),
        celda("Bulto", ot.get("bulto_id") or "N/A"),
        celda("Estación", ot.get("estacion") or "N/A"),
        celda("Creada", _fecha(ot.get("creada_ts"))),
        celda("Cerrada", _fecha(ot.get("cerrada_ts"))),
    ]
    rejilla = Table([datos[0:4], datos[4:8]], colWidths=[44 * mm] * 4)
    rejilla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(FONDO_SUAVE)),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINEA)),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor(LINEA)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))

    historia = [rejilla, Paragraph("Causa", titulo), Paragraph(escape(ot["causa"]), causa)]

    historia.append(Paragraph("Evidencia", titulo))
    filas = _filas_evidencia(ot)
    if filas:
        encab = ["Registro / evento", "Valor o detalle", "Origen", "Hora o impacto"]
        tabla = Table([encab] + [[Paragraph(escape(str(c)), base) for c in f] for f in filas],
                      colWidths=[44 * mm, 72 * mm, 26 * mm, 34 * mm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INDIGO)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(FONDO_SUAVE)]),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINEA)),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor(LINEA)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        historia.append(tabla)
        if any(e.get("origen") == "simulado" for e in ot.get("evidencia") or []):
            historia.append(Spacer(1, 4))
            historia.append(Paragraph("Nota: lecturas de sensor simuladas; el peso es simulado mientras no haya "
                                      "celda de carga.", etiqueta))
    else:
        historia.append(Paragraph("Sin eventos: la estación no reportó lecturas en la ventana de recepción.", base))

    historia.append(Paragraph("Resolución", titulo))
    comentario = ot.get("comentario") or ""
    caja = Table([[Paragraph(escape(comentario) if comentario else
                             '<font color="#9A95BD">Pendiente de revisión. Anotar qué se verificó y qué se corrigió.</font>',
                             base)]], colWidths=[176 * mm], rowHeights=[None if comentario else 26 * mm])
    caja.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINEA)),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                              ("TOPPADDING", (0, 0), (-1, -1), 7)]))
    historia.append(caja)

    historia.append(Spacer(1, 18 * mm))
    firmas = Table([["", "", ""], ["Atendió", "", "Autorizó"]], colWidths=[70 * mm, 36 * mm, 70 * mm])
    firmas.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, colors.HexColor(TINTA)),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, colors.HexColor(TINTA)),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"), ("FONTSIZE", (0, 1), (-1, 1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor(GRIS)),
    ]))
    historia.append(firmas)

    doc.build(historia, onFirstPage=encabezado, onLaterPages=encabezado)
    return buf.getvalue()


def csv_bandeja(ots):
    """Lista de OT en CSV con ';' y BOM, para abrir directo en Excel."""
    import csv
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";")
    w.writerow(["OT", "Tipo", "Prioridad", "Estado", "Origen", "Bulto", "Estación", "Causa", "Creada", "Cerrada",
                "Comentario"])
    for o in ots:
        w.writerow([o["id"], TIPOS_OT.get(o["tipo"], o["tipo"]), o["prioridad"], NOMBRE_ESTADO.get(o["estado"], o["estado"]),
                    NOMBRE_ORIGEN.get(origen_de_ot(o), ""), o.get("bulto_id") or "", o.get("estacion") or "",
                    o["causa"], _fecha(o.get("creada_ts")), _fecha(o.get("cerrada_ts")), o.get("comentario") or ""])
    return ("﻿" + salida.getvalue()).encode("utf-8")


def etiquetas_qr_pdf(bultos, front_url):
    """Hoja de etiquetas con el QR de cada bulto. El QR lleva la URL de Recepción: con la cámara del
    celular abre la pantalla con el código cargado, y la cámara de la laptop lee el código de la URL."""
    if not HAY_PDF:
        raise RuntimeError("Falta reportlab: python -m pip install reportlab")
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
    from reportlab.pdfgen import canvas as lienzo

    buf = io.BytesIO()
    c = lienzo.Canvas(buf, pagesize=letter)
    ancho, alto = letter
    c.setTitle("Etiquetas QR · Kardex Vivo")
    columnas, filas = 2, 3
    margen = 14 * mm
    celda_w = (ancho - 2 * margen) / columnas
    celda_h = (alto - 2 * margen - 12 * mm) / filas
    lado = 44 * mm
    for i, b in enumerate(bultos):
        if i and i % (columnas * filas) == 0:
            c.showPage()
        pos = i % (columnas * filas)
        if pos == 0:
            c.setFillColor(colors.HexColor(VIOLETA))
            c.setFont("Helvetica-Bold", 13)
            c.drawString(margen, alto - margen, "Kardex Vivo · Etiquetas de recepción")
            c.setFillColor(colors.HexColor(GRIS))
            c.setFont("Helvetica", 8.5)
            c.drawRightString(ancho - margen, alto - margen, "Escanea en Recepción: cámara de la laptop o del celular")
        x = margen + (pos % columnas) * celda_w
        y = alto - margen - 12 * mm - (pos // columnas + 1) * celda_h
        c.setStrokeColor(colors.HexColor(LINEA))
        c.setDash(3, 3)
        c.roundRect(x + 3 * mm, y + 3 * mm, celda_w - 6 * mm, celda_h - 6 * mm, 4 * mm, stroke=1, fill=0)
        c.setDash()
        url = f"{front_url.rstrip('/')}/recepcion?qr={b['bulto_id']}"
        codigo = qr.QrCodeWidget(url, barLevel="M")
        x0, y0, x1, y1 = codigo.getBounds()
        dibujo = Drawing(lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0])
        dibujo.add(codigo)
        renderPDF.draw(dibujo, c, x + (celda_w - lado) / 2, y + celda_h - lado - 7 * mm)
        c.setFillColor(colors.HexColor(TINTA))
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + celda_w / 2, y + 20 * mm, b["bulto_id"])
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor(GRIS))
        c.drawCentredString(x + celda_w / 2, y + 14.5 * mm, f"Compra {b.get('oc', '')} · SKU {b.get('sku', '')}")
        c.drawCentredString(x + celda_w / 2, y + 10 * mm, (b.get("descripcion") or "")[:48])
    c.save()
    return buf.getvalue()
