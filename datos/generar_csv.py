"""Genera los CSV "sucios" de compras, almacén, costos y órdenes de trabajo operativas.

Los errores se siembran a propósito y se anotan en crudos/errores_sembrados.json
(la "hoja de respuestas"). Así el motor de limpieza se puede calificar:
cuántos errores encontró de los que había.

Solo librería estándar. Siempre genera lo mismo (semilla fija).
  python generar_csv.py
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 2026
CARPETA = Path(__file__).parent / "crudos"
rng = random.Random(SEMILLA)

# ---------------- Catálogo (limpio, es la referencia) ----------------
CATALOGO = [
    # sku, descripcion, unidad, costo vigente MXN, abreviatura usada en capturas "a mano"
    ("1001", "Tornillo hexagonal M6x20", "pieza", 2.10, "TORN. HEX M6 20mm"),
    ("1002", "Rondana plana 1/4", "pieza", 0.60, "RONDANA 1/4 PLANA"),
    ("1003", "Rodamiento 6204", "pieza", 85.00, "BALERO 6204"),
    ("1004", "Cable THW calibre 14 (rollo 100 m)", "rollo", 1450.00, "CABLE THW 14 ROLLO"),
    ("1005", "Grasa de litio (cubeta 19 kg)", "cubeta", 2300.00, "GRASA LITIO CUB."),
    ("1006", "Filtro de aceite", "pieza", 165.00, "FILTRO ACEITE"),
    ("1007", "Banda en V A-42", "pieza", 140.00, "BANDA A42"),
    ("1008", "Guante de nitrilo (par)", "par", 38.00, "GUANTE NITRILO"),
    ("1009", "Contactor 3P 25 A", "pieza", 690.00, "CONTACTOR 25A"),
    ("1010", "Fusible 10 A", "pieza", 12.00, "FUSIBLE 10A"),
]
SKU = {c[0]: c for c in CATALOGO}
PROVEEDORES = ["Ferretera del Golfo", "Rodamientos del Puerto", "Eléctrica Veracruz",
               "Lubricantes Boca del Río", "Suministros Industriales Jarocho"]
RESPONSABLES = ["M. Hernández", "J. Cruz", "A. Domínguez", "R. Lara"]
TECNICOS = ["L. Ortiz", "C. Méndez", "P. Rivas", "S. Aguilar"]
EQUIPOS = ["Compresor C-01", "Banda transportadora BT-02", "Torno CNC T-03",
           "Bomba de agua B-04", "Prensa hidráulica P-05", "Montacargas M-06"]
UBICACIONES = ["A-01", "A-02", "B-01", "B-02", "C-01"]
CANTIDADES = {"pieza": (20, 1000), "rollo": (1, 6), "cubeta": (1, 4), "par": (50, 300)}

# OC que todavía no llegan: se reciben en la estación IoT (mismos datos que backend_mock).
EN_TRANSITO = [("OC-1042", "1001", 500, "Ferretera del Golfo"), ("OC-1042", "1002", 1000, "Ferretera del Golfo"),
               ("OC-1043", "1003", 40, "Rodamientos del Puerto"), ("OC-1044", "1004", 1, "Eléctrica Veracruz"),
               ("OC-1045", "1005", 1, "Lubricantes Boca del Río"), ("OC-1046", "1006", 12, "Ferretera del Golfo")]

INICIO = date(2026, 9, 1)
_uid = 0


def uid():
    global _uid
    _uid += 1
    return _uid


def fecha_iso(d):
    return d.isoformat()


def fila(**campos):
    campos["_uid"] = uid()
    campos["_errores"] = []
    return campos


def marcar(r, categoria, detalle, ref=None):
    r["_errores"].append({"categoria": categoria, "detalle": detalle, "ref": ref})


# ---------------- Datos limpios ----------------
def base():
    compras, almacen, ots = [], [], []
    factura = 2001
    d = INICIO
    for n in range(1, 42):  # OC-1001 ... OC-1041 ya recibidas
        oc = f"OC-{1000 + n}"
        proveedor = rng.choice(PROVEEDORES)
        d += timedelta(days=rng.randint(0, 2))
        for sku in rng.sample(list(SKU), rng.randint(1, 3)):
            _, desc, unidad, costo, _ = SKU[sku]
            cant = rng.randint(*CANTIDADES[unidad])
            compras.append(fila(oc_id=oc, fecha=fecha_iso(d), proveedor=proveedor, sku=sku, descripcion=desc,
                                cantidad=cant, precio_unitario=round(costo * rng.uniform(0.97, 1.03), 2),
                                factura=f"F-{factura}"))
            almacen.append(fila(mov_id=None, fecha=fecha_iso(d + timedelta(days=rng.randint(1, 3))),
                                tipo="entrada", referencia=oc, sku=sku, cantidad=cant,
                                ubicacion=rng.choice(UBICACIONES), responsable=rng.choice(RESPONSABLES)))
        factura += 1
    for oc, sku, cant, proveedor in EN_TRANSITO:
        _, desc, _, costo, _ = SKU[sku]
        compras.append(fila(oc_id=oc, fecha=fecha_iso(date(2026, 11, 20)), proveedor=proveedor, sku=sku,
                            descripcion=desc, cantidad=cant, precio_unitario=costo,
                            factura=f"F-{factura}", _protegida=True))
        factura += 1

    d = INICIO + timedelta(days=5)
    for n in range(1, 61):
        d += timedelta(days=rng.randint(0, 1))
        sku = rng.choice(list(SKU))
        _, _, unidad, costo, _ = SKU[sku]
        cant = rng.randint(1, 4) if unidad in ("rollo", "cubeta") else rng.randint(2, 40)
        ot_id = f"OT-{500 + n}"
        ots.append(fila(ot_id=ot_id, fecha=fecha_iso(d), equipo=rng.choice(EQUIPOS), sku=sku, cantidad=cant,
                        costo_total=round(cant * costo * rng.uniform(0.99, 1.01), 2),
                        tecnico=rng.choice(TECNICOS), estado=rng.choice(["cerrada", "cerrada", "abierta"])))
        almacen.append(fila(mov_id=None, fecha=fecha_iso(d), tipo="salida", referencia=ot_id, sku=sku,
                            cantidad=cant, ubicacion=rng.choice(UBICACIONES), responsable=rng.choice(RESPONSABLES)))

    costos = [fila(sku=s, costo_unitario=c[3], moneda="MXN", vigente_desde="2026-01-01") for s, c in SKU.items()]
    return compras, almacen, costos, ots


# ---------------- Siembra de errores ----------------
def elegir(filas, n, condicion=lambda r: True):
    libres = [r for r in filas if not r["_errores"] and not r.get("_protegida") and condicion(r)]
    return rng.sample(libres, n)


def insertar_copia(filas, original, **cambios):
    copia = {k: v for k, v in original.items() if k not in ("_uid", "_errores", "_protegida")}
    copia.update(cambios)
    copia = fila(**copia)
    filas.insert(rng.randint(filas.index(original) + 1, len(filas)), copia)
    return copia


def sembrar(compras, almacen, costos, ots):
    # --- compras ---
    for r in elegir(compras, 3):
        c = insertar_copia(compras, r)
        marcar(c, "duplicado", "Copia exacta de otra línea de compra", r["_uid"])
    for r in elegir(compras, 4):
        d = date.fromisoformat(r["fecha"]) + timedelta(days=1)
        c = insertar_copia(compras, r, descripcion=SKU[r["sku"]][4], fecha=fecha_iso(d))
        marcar(c, "duplicado", "Misma factura, SKU y cantidad, capturada con otra descripción y fecha", r["_uid"])
    for r, campo in zip(elegir(compras, 6), ["proveedor", "factura", "precio_unitario"] * 2):
        r[campo] = ""
        marcar(r, "dato_incompleto", f"Campo {campo} vacío")
    for r in elegir(compras, 2):
        r["sku"] = "9999"
        marcar(r, "dato_incompleto", "SKU 9999 no existe en el catálogo")
    for r, valor in zip(elegir(compras, 2), [0, -50]):
        r["cantidad"] = valor
        marcar(r, "dato_incompleto", f"Cantidad inválida ({valor})")
    for r in elegir(compras, 4, lambda r: r["precio_unitario"] != ""):
        r["precio_unitario"] = round(SKU[r["sku"]][3] * rng.choice([1.22, 1.35, 0.78]), 2)
        marcar(r, "costo_distinto", "Precio unitario fuera de ±10 % del costo vigente")
    for r in elegir(compras, 5):
        d = date.fromisoformat(r["fecha"])
        r["fecha"] = d.strftime("%d/%m/%Y")
        marcar(r, "formato", "Fecha en formato dd/mm/aaaa")
    for r in elegir(compras, 3, lambda r: r["proveedor"]):
        r["proveedor"] = "  " + r["proveedor"].upper() + " "
        marcar(r, "formato", "Proveedor con mayúsculas y espacios de más")

    # --- almacén ---
    entradas = lambda r: r["tipo"] == "entrada"
    salidas = lambda r: r["tipo"] == "salida"
    for r in elegir(almacen, 5, entradas):
        r["cantidad"] = max(1, r["cantidad"] - rng.randint(1, max(2, r["cantidad"] // 8)))
        marcar(r, "cantidad_distinta", "Entrada con menos piezas que la orden de compra")
    for r in elegir(almacen, 3, salidas):
        r["cantidad"] = r["cantidad"] + rng.randint(1, 5)
        marcar(r, "cantidad_distinta", "Salida con más piezas de las que consumió la OT")
    for r in elegir(almacen, 2, entradas):
        r["referencia"] = f"OC-{rng.randint(9000, 9999)}"
        marcar(r, "dato_incompleto", "Entrada que apunta a una orden de compra inexistente")
    for r in elegir(almacen, 4):
        r["responsable"] = ""
        marcar(r, "dato_incompleto", "Movimiento sin responsable")
    for r in elegir(almacen, 3):
        c = insertar_copia(almacen, r)
        marcar(c, "duplicado", "Mismo movimiento registrado dos veces con distinto folio", r["_uid"])
    for r in elegir(almacen, 3):
        r["fecha"] = date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y")
        marcar(r, "formato", "Fecha en formato dd/mm/aaaa")

    # --- costos ---
    r = next(r for r in costos if r["sku"] == "1009")
    r["costo_unitario"] = ""
    marcar(r, "dato_incompleto", "Costo vacío")
    r = next(r for r in costos if r["sku"] == "1010")
    r["costo_unitario"], r["moneda"] = round(12.00 / 18.0, 2), "USD"
    marcar(r, "formato", "Costo capturado en dólares")
    r = next(r for r in costos if r["sku"] == "1003")
    c = insertar_copia(costos, r, costo_unitario=92.50)
    marcar(c, "duplicado", "Mismo SKU con dos costos vigentes desde la misma fecha", r["_uid"])

    # --- órdenes de trabajo operativas ---
    for r in elegir(ots, 3):
        c = insertar_copia(ots, r)
        marcar(c, "duplicado", "OT registrada dos veces", r["_uid"])
    for r in elegir(ots, 3):
        r["costo_total"] = ""
        marcar(r, "dato_incompleto", "Costo total vacío")
    for r in elegir(ots, 2):
        r["tecnico"] = ""
        marcar(r, "dato_incompleto", "OT sin técnico")
    for r in elegir(ots, 4):
        r["costo_total"] = round(r["costo_total"] * rng.choice([1.3, 1.45, 0.7]), 2)
        marcar(r, "costo_distinto", "Costo total no cuadra con cantidad por costo vigente")
    for r in elegir(ots, 1):
        r["sku"] = "9999"
        marcar(r, "dato_incompleto", "SKU 9999 no existe en el catálogo")
    for r, valor in zip(elegir(ots, 4, lambda r: r["estado"] == "cerrada"),
                        ["Cerrada", "CERRADA ", "cerrado", " cerrada"]):
        r["estado"] = valor
        marcar(r, "formato", f"Estado escrito como '{valor}'")


# ---------------- Escritura ----------------
def escribir(nombre, filas, columnas, clave):
    ruta = CARPETA / nombre
    linea_de = {}
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        for i, r in enumerate(filas, start=2):  # la línea 1 es el encabezado
            w.writerow([r[c] for c in columnas])
            linea_de[r["_uid"]] = i
    for r in filas:
        for e in r["_errores"]:
            registro = {"archivo": nombre, "linea": linea_de[r["_uid"]], "id": str(r[clave]),
                        "categoria": e["categoria"], "detalle": e["detalle"]}
            if e["ref"]:
                registro["duplica_linea"] = linea_de[e["ref"]]
            ERRORES.append(registro)
    return len(filas)


ERRORES = []


def main():
    CARPETA.mkdir(exist_ok=True)
    compras, almacen, costos, ots = base()
    almacen.sort(key=lambda r: r["fecha"])
    sembrar(compras, almacen, costos, ots)
    for i, r in enumerate(almacen, start=1):
        r["mov_id"] = f"M-{i:04d}"

    with (CARPETA / "catalogo.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "descripcion", "unidad"])
        for sku, desc, unidad, _, _ in CATALOGO:
            w.writerow([sku, desc, unidad])

    totales = {
        "compras.csv": escribir("compras.csv", compras, ["oc_id", "fecha", "proveedor", "sku", "descripcion",
                                                         "cantidad", "precio_unitario", "factura"], "oc_id"),
        "almacen.csv": escribir("almacen.csv", almacen, ["mov_id", "fecha", "tipo", "referencia", "sku",
                                                         "cantidad", "ubicacion", "responsable"], "mov_id"),
        "costos.csv": escribir("costos.csv", costos, ["sku", "costo_unitario", "moneda", "vigente_desde"], "sku"),
        "ot_operativas.csv": escribir("ot_operativas.csv", ots, ["ot_id", "fecha", "equipo", "sku", "cantidad",
                                                                 "costo_total", "tecnico", "estado"], "ot_id"),
    }
    ERRORES.sort(key=lambda e: (e["archivo"], e["linea"]))
    resumen = {"semilla": SEMILLA, "registros": totales, "total_errores": len(ERRORES), "errores": ERRORES}
    (CARPETA / "errores_sembrados.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")

    print("Archivos en", CARPETA)
    for archivo, n in totales.items():
        con_error = len({e["linea"] for e in ERRORES if e["archivo"] == archivo})
        print(f"  {archivo:<18} {n:>4} registros, {con_error:>3} con error")
    print(f"  Total de errores sembrados: {len(ERRORES)}")
    por_categoria = {}
    for e in ERRORES:
        por_categoria[e["categoria"]] = por_categoria.get(e["categoria"], 0) + 1
    for cat, n in sorted(por_categoria.items(), key=lambda x: -x[1]):
        print(f"    {cat:<18} {n}")


if __name__ == "__main__":
    main()
