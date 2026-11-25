"""Motor de limpieza de Kardex Vivo, construido sobre el trabajo del equipo (datos/equipo/).

Toma la normalización de limpieza.py (fechas, mayúsculas, espacios, variantes de texto) y las
revisiones de "Reporte de errores.py", y agrega lo que faltaba para integrarlo:
  - cada hallazgo queda anotado con archivo, línea, id, campo, valor y regla;
  - lo de FORMATO se corrige solo; lo demás abre una orden de trabajo (contrato, sección 4);
  - cruce registro por registro entre compras y entradas de almacén (no solo totales por SKU);
  - evaluación contra datos/fuentes/errores_sembrados.csv.

Solo librería estándar (el backend lo importa sin dependencias extra).
  python motor_limpieza.py          imprime el resumen y escribe salida/ (CSV limpios y reporte para Excel)
"""
import csv
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

CARPETA = Path(__file__).parent
FUENTES = CARPETA / "fuentes"

ARCHIVOS = {
    "compras.csv": {"id": "id_compra", "fuente": "compras",
                    "columnas": ["id_compra", "fecha", "proveedor", "sku", "descripcion", "cantidad", "costo_unitario"]},
    "almacen.csv": {"id": "id_mov", "fuente": "almacen",
                    "columnas": ["id_mov", "fecha", "sku", "descripcion", "cantidad_recibida", "ubicacion"]},
    "ordenes_trabajo.csv": {"id": "id_ot", "fuente": "ordenes_trabajo",
                            "columnas": ["id_ot", "fecha", "sku", "tipo", "cantidad", "estado"]},
}
ESTADOS_OT = {"abierta", "en_proceso", "cerrada"}
DIAS_PARA_RECIBIR = 3          # una entrada de almacén cuadra con una compra si llega 0 a 3 días después
PESO_UNITARIO_KG = {            # de datos/equipo/database.py; SKU-004 agregado para la estación IoT
    "SKU-001": 2.5, "SKU-002": 0.4, "SKU-003": 1.2, "SKU-004": 0.06,
}

# regla -> (categoría, acción)
REGLAS = {
    "formato_fecha": ("formato", "corregido"),
    "formato_texto": ("formato", "corregido"),
    "duplicado_exacto": ("duplicado", "ot"),
    "duplicado_distinto_id": ("duplicado", "ot"),
    "campo_vacio": ("dato_incompleto", "ot"),
    "valor_invalido": ("dato_incompleto", "ot"),
    "fecha_futura": ("dato_incompleto", "ot"),
    "sku_inexistente": ("dato_incompleto", "ot"),
    "estado_invalido": ("dato_incompleto", "ot"),
    "diferencia_cantidad": ("cantidad_distinta", "ot"),
    "sin_recepcion": ("cantidad_distinta", "ot"),
}
PRIORIDAD = {"duplicado": "media", "dato_incompleto": "baja", "cantidad_distinta": "alta"}
VACIO = {"fecha": "Fecha vacía", "proveedor": "Proveedor vacío", "sku": "SKU vacío", "cantidad": "Cantidad vacía",
         "costo_unitario": "Costo unitario vacío", "cantidad_recibida": "Cantidad recibida vacía",
         "ubicacion": "Ubicación vacía", "estado": "Estado vacío"}
NOMBRE_CAMPO = {"cantidad": "Cantidad", "cantidad_recibida": "Cantidad recibida"}
NOMBRE_REGLA = {
    "formato_fecha": "Fecha en otro formato", "formato_texto": "Mayúsculas o espacios",
    "duplicado_exacto": "Duplicado exacto", "duplicado_distinto_id": "Duplicado con otro folio",
    "campo_vacio": "Campo vacío", "valor_invalido": "Valor inválido", "fecha_futura": "Fecha futura",
    "sku_inexistente": "SKU inexistente", "estado_invalido": "Estado no válido",
    "diferencia_cantidad": "Diferencia de cantidad", "sin_recepcion": "Compra sin recepción",
}


# ---------------- Normalización (misma lógica que datos/equipo/limpieza.py) ----------------
def texto(v):
    return " ".join(str(v or "").split())


def fecha(v):
    t = str(v or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, formato).date()
        except ValueError:
            pass
    return None


def numero(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def canonicos(valores):
    """Para cada variante (sin importar mayúsculas/espacios) devuelve la forma más común (unificar_texto)."""
    grupos = {}
    for v in valores:
        t = texto(v)
        if t:
            grupos.setdefault(t.casefold(), Counter())[t] += 1
    return {k: c.most_common(1)[0][0] for k, c in grupos.items()}


def leer(archivo, carpeta):
    with open(Path(carpeta) / archivo, newline="", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        faltan = [c for c in ARCHIVOS[archivo]["columnas"] if c not in (lector.fieldnames or [])]
        if faltan:
            raise ValueError(f"{archivo} no tiene las columnas: {', '.join(faltan)}")
        return [{"_linea": i, **fila} for i, fila in enumerate(lector, start=2)]


# ---------------- Registro de hallazgos ----------------
class Hallazgos(list):
    def agregar(self, archivo, fila, regla, detalle, campo=None, original=None, corregido=None, impacto=None):
        categoria, accion = REGLAS[regla]
        self.append({
            "archivo": archivo, "fuente": ARCHIVOS[archivo]["fuente"], "linea": fila["_linea"],
            "id": fila.get(ARCHIVOS[archivo]["id"], ""), "sku": texto(fila.get("sku")).upper(),
            "regla": regla, "regla_nombre": NOMBRE_REGLA[regla], "categoria": categoria, "accion": accion,
            "detalle": detalle, "campo": campo,
            "valor_original": original, "valor_corregido": corregido,
            "impacto_mxn": round(impacto, 2) if impacto else None,
        })


def normalizar_formato(archivo, filas, h, campos_texto, campo_estado=None):
    """Corrige fecha, SKU y textos; anota cada cambio como 'formato'."""
    canon = {c: canonicos(f.get(c) for f in filas) for c in campos_texto}
    for f in filas:
        if f.get("_duplicado"):
            continue
        cambios = []
        d = fecha(f["fecha"])
        if d and d.isoformat() != f["fecha"]:
            h.agregar(archivo, f, "formato_fecha", f"Fecha {f['fecha']} normalizada a {d.isoformat()}",
                      "fecha", f["fecha"], d.isoformat())
            f["fecha"] = d.isoformat()
        sku = texto(f.get("sku")).upper()
        if f.get("sku") and sku != f["sku"]:
            cambios.append(("sku", f["sku"], sku))
            f["sku"] = sku
        for c in campos_texto:
            t = texto(f.get(c))
            nuevo = canon[c].get(t.casefold(), t) if t else ""
            if f.get(c) and nuevo != f[c]:
                cambios.append((c, f[c], nuevo))
                f[c] = nuevo
        if campo_estado and f.get(campo_estado) and f[campo_estado] != f[campo_estado].strip().lower():
            cambios.append((campo_estado, f[campo_estado], f[campo_estado].strip().lower()))
            f[campo_estado] = f[campo_estado].strip().lower()
        for campo, antes, despues in cambios:
            h.agregar(archivo, f, "formato_texto", f"{campo}: '{antes}' → '{despues}'", campo, antes, despues)


def marcar_duplicados(archivo, filas, h, campos):
    """Duplicado = mismo contenido (ya normalizado) sin contar el folio. Se queda el primero."""
    id_campo = ARCHIVOS[archivo]["id"]
    canon = {c: canonicos(f.get(c) for f in filas) for c in campos if c in ("proveedor", "descripcion")}
    vistos = {}
    for f in filas:
        clave = []
        for c in campos:
            v = texto(f.get(c))
            if c == "fecha":
                d = fecha(v)
                v = d.isoformat() if d else v
            elif c == "sku":
                v = v.upper()
            elif c in canon:
                v = canon[c].get(v.casefold(), v).casefold()
            elif numero(v) is not None:
                v = f"{numero(v):g}"
            clave.append(v.casefold())
        clave = tuple(clave)
        if clave in vistos:
            original = vistos[clave]
            f["_duplicado"] = True
            if original[id_campo] == f[id_campo]:
                h.agregar(archivo, f, "duplicado_exacto",
                          f"Fila repetida completa de {f[id_campo]} (línea {original['_linea']})")
            else:
                h.agregar(archivo, f, "duplicado_distinto_id",
                          f"Mismo contenido que {original[id_campo]} (línea {original['_linea']}) con otro folio")
        else:
            vistos[clave] = f


# ---------------- Proceso completo ----------------
def analizar(carpeta=FUENTES, hoy=None, evaluar=True):
    hoy = hoy or date.today()
    compras = leer("compras.csv", carpeta)
    almacen = leer("almacen.csv", carpeta)
    ots = leer("ordenes_trabajo.csv", carpeta)
    h = Hallazgos()

    # 1) Duplicados y formato
    marcar_duplicados("compras.csv", compras, h, ["fecha", "proveedor", "sku", "descripcion", "cantidad", "costo_unitario"])
    marcar_duplicados("almacen.csv", almacen, h, ["fecha", "sku", "descripcion", "cantidad_recibida", "ubicacion"])
    marcar_duplicados("ordenes_trabajo.csv", ots, h, ["fecha", "sku", "tipo", "cantidad", "estado"])
    normalizar_formato("compras.csv", compras, h, ["proveedor", "descripcion"])
    normalizar_formato("almacen.csv", almacen, h, ["descripcion", "ubicacion"])
    normalizar_formato("ordenes_trabajo.csv", ots, h, ["tipo"], campo_estado="estado")

    catalogo = {}
    for f in compras:
        if f["sku"] and not f.get("_duplicado"):
            catalogo.setdefault(f["sku"], {"descripcion": f["descripcion"], "costos": []})
            c = numero(f["costo_unitario"])
            if c and c > 0:
                catalogo[f["sku"]]["costos"].append(c)
    for sku, info in catalogo.items():
        costos = sorted(info.pop("costos"))
        info["costo_unitario"] = costos[len(costos) // 2] if costos else None
        info["peso_unitario_kg"] = PESO_UNITARIO_KG.get(sku)

    # 2) Reglas por registro
    def revisar(archivo, filas, obligatorios, campo_cantidad, revisar_sku=True):
        for f in filas:
            if f.get("_duplicado"):
                continue
            for c in obligatorios:
                if not texto(f.get(c)):
                    h.agregar(archivo, f, "campo_vacio", VACIO.get(c, f"{c} vacío"), c, "", None)
            cant = numero(f.get(campo_cantidad))
            if texto(f.get(campo_cantidad)) and (cant is None or cant <= 0):
                problema = ("negativa (" + f[campo_cantidad] + ")" if cant is not None and cant < 0
                            else "igual a 0" if cant == 0 else "no numérica (" + f[campo_cantidad] + ")")
                h.agregar(archivo, f, "valor_invalido", f"{NOMBRE_CAMPO[campo_cantidad]} {problema}",
                          campo_cantidad, f[campo_cantidad])
            d = fecha(f.get("fecha"))
            if d and d > hoy:
                h.agregar(archivo, f, "fecha_futura", f"Fecha {d.isoformat()} posterior a hoy ({hoy.isoformat()})",
                          "fecha", f["fecha"])
            if revisar_sku and f.get("sku") and f["sku"] not in catalogo:
                h.agregar(archivo, f, "sku_inexistente", f"{f['sku']} no existe en compras ni en el catálogo",
                          "sku", f["sku"])

    revisar("compras.csv", compras, ["fecha", "proveedor", "sku", "cantidad", "costo_unitario"], "cantidad",
            revisar_sku=False)
    for f in compras:
        costo = numero(f.get("costo_unitario"))
        if not f.get("_duplicado") and costo is not None and costo < 0:
            h.agregar("compras.csv", f, "valor_invalido", f"Costo unitario negativo ({f['costo_unitario']})",
                      "costo_unitario", f["costo_unitario"])
    revisar("almacen.csv", almacen, ["fecha", "sku", "cantidad_recibida", "ubicacion"], "cantidad_recibida")
    revisar("ordenes_trabajo.csv", ots, ["fecha", "sku", "cantidad", "estado"], "cantidad")
    for f in ots:
        if not f.get("_duplicado") and f.get("estado") and f["estado"] not in ESTADOS_OT:
            h.agregar("ordenes_trabajo.csv", f, "estado_invalido",
                      f"Estado '{f['estado']}' no válido (válidos: {', '.join(sorted(ESTADOS_OT))})", "estado", f["estado"])

    # 3) Cruce compra ↔ entrada de almacén, registro por registro
    def valido(f, campo):
        d, c = fecha(f.get("fecha")), numero(f.get(campo))
        return (not f.get("_duplicado") and f.get("sku") in catalogo and c and c > 0 and d and d <= hoy)

    entradas = [m for m in almacen if valido(m, "cantidad_recibida")]
    usadas = set()
    pendientes = []
    for c in sorted((c for c in compras if valido(c, "cantidad")), key=lambda c: (c["fecha"], c["_linea"])):
        dc, qc = fecha(c["fecha"]), numero(c["cantidad"])
        candidatas = [m for m in entradas if m["_linea"] not in usadas and m["sku"] == c["sku"]
                      and 0 <= (fecha(m["fecha"]) - dc).days <= DIAS_PARA_RECIBIR]
        if not candidatas:
            costo = numero(c["costo_unitario"]) or catalogo[c["sku"]]["costo_unitario"] or 0
            h.agregar("compras.csv", c, "sin_recepcion",
                      f"Compra de {qc:g} sin entrada en almacén ({c['descripcion']})", "cantidad", c["cantidad"],
                      impacto=qc * abs(costo))
            pendientes.append({"id_compra": c["id_compra"], "sku": c["sku"], "descripcion": c["descripcion"],
                               "cantidad": int(qc), "fecha": c["fecha"], "proveedor": c["proveedor"]})
            continue
        m = min(candidatas, key=lambda m: (numero(m["cantidad_recibida"]) != qc,
                                           (fecha(m["fecha"]) - dc).days, m["_linea"]))
        usadas.add(m["_linea"])
        qm = numero(m["cantidad_recibida"])
        m["_compra"] = c["id_compra"]
        if qm != qc:
            costo = numero(c["costo_unitario"]) or catalogo[c["sku"]]["costo_unitario"] or 0
            h.agregar("almacen.csv", m, "diferencia_cantidad",
                      f"Recibido {qm:g} vs {qc:g} comprados en {c['id_compra']} ({qm - qc:+g})",
                      "cantidad_recibida", m["cantidad_recibida"], impacto=abs(qc - qm) * abs(costo))

    # 4) Métricas
    inventario = Counter()
    for m in entradas:
        inventario[m["sku"]] += int(numero(m["cantidad_recibida"]))
    por_fuente = []
    for archivo, filas in (("compras.csv", compras), ("almacen.csv", almacen), ("ordenes_trabajo.csv", ots)):
        mios = [x for x in h if x["archivo"] == archivo]
        con_ot = {x["linea"] for x in mios if x["accion"] == "ot"}
        corregidos = {x["linea"] for x in mios if x["accion"] == "corregido"} - con_ot
        total = len(filas)
        sanos = total - len(con_ot | corregidos)
        por_fuente.append({
            "fuente": ARCHIVOS[archivo]["fuente"], "archivo": archivo, "total": total,
            "antes": round(sanos / total, 4), "despues": round((sanos + len(corregidos)) / total, 4),
            "corregidos": len(corregidos), "en_cuarentena": len(con_ot),
            "lineas_en_cuarentena": sorted(con_ot),
        })
    total = sum(f["total"] for f in por_fuente)
    resultado = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "fecha_referencia": hoy.isoformat(),
        "total_registros": total,
        "global": {
            "antes": round(sum(f["antes"] * f["total"] for f in por_fuente) / total, 4),
            "despues": round(sum(f["despues"] * f["total"] for f in por_fuente) / total, 4),
        },
        "por_fuente": por_fuente,
        "hallazgos": h,
        "por_categoria": dict(Counter(x["categoria"] for x in h)),
        "por_regla": dict(Counter(x["regla"] for x in h)),
        "corregidos_automaticamente": sum(f["corregidos"] for f in por_fuente),
        "en_cuarentena": sum(f["en_cuarentena"] for f in por_fuente),
        "impacto_mxn": round(sum(x["impacto_mxn"] or 0 for x in h), 2),
        "ots": [ot_de(x) for x in h if x["accion"] == "ot"],
        "catalogo": catalogo,
        "inventario": dict(inventario),
        "pendientes": pendientes,
        "limpios": {a: [limpia(f) for f in filas if not f.get("_duplicado")]
                    for a, filas in (("compras.csv", compras), ("almacen.csv", almacen), ("ordenes_trabajo.csv", ots))},
    }
    if evaluar and (Path(carpeta) / "errores_sembrados.csv").exists():
        resultado["evaluacion"] = evaluar_contra(h, Path(carpeta) / "errores_sembrados.csv")
    return resultado


def limpia(f):
    return {k: v for k, v in f.items() if not k.startswith("_")}


def ot_de(x):
    return {
        "tipo": x["categoria"],
        "prioridad": PRIORIDAD[x["categoria"]],
        "causa": f"{x['detalle']} · {x['archivo']} línea {x['linea']} ({x['id']})",
        "evidencia": [{"tipo": "registro", "fuente": x["archivo"], "fila": x["linea"], "id": x["id"],
                       "sku": x["sku"], "regla": x["regla"], "detalle": x["detalle"],
                       "impacto_mxn": x["impacto_mxn"], "origen": "datos"}],
    }


def evaluar_contra(h, ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        clave = list(csv.DictReader(f))
    esperados = {(e["archivo"], e["id_registro"]) for e in clave}
    detectados = {(x["archivo"], x["id"]) for x in h}
    aciertos = esperados & detectados
    por_tipo = {}
    for e in clave:
        t = por_tipo.setdefault(e["tipo_error"], {"sembrados": 0, "detectados": 0})
        t["sembrados"] += 1
        t["detectados"] += (e["archivo"], e["id_registro"]) in detectados
    return {
        "sembrados": len(esperados),
        "detectados_correctos": len(aciertos),
        "deteccion": round(len(aciertos) / len(esperados), 4) if esperados else None,
        "precision": round(len(aciertos) / len(detectados), 4) if detectados else None,
        "no_detectados": sorted(esperados - detectados),
        "fuera_de_la_hoja": sorted(detectados - esperados),
        "por_tipo": por_tipo,
    }


# ---------------- Reporte para Excel (formato de "Reporte de errores.py") ----------------
COLUMNAS_REPORTE = ["fuente", "fila_origen", "id", "sku", "campo", "valor_actual", "tipo_error", "detalle",
                    "accion", "valor_corregido", "impacto_mxn"]


def filas_reporte(hallazgos):
    return [{
        "fuente": x["fuente"], "fila_origen": x["linea"], "id": x["id"], "sku": x["sku"], "campo": x["campo"] or "",
        "valor_actual": "" if x["valor_original"] is None else x["valor_original"],
        "tipo_error": x["regla"].upper(), "detalle": x["detalle"],
        "accion": "Corregido automáticamente" if x["accion"] == "corregido" else "Orden de trabajo",
        "valor_corregido": x["valor_corregido"] or "", "impacto_mxn": x["impacto_mxn"] or "",
    } for x in hallazgos]


def reporte_excel(hallazgos):
    """Texto CSV con ';' y BOM, para abrir directo en Excel en español."""
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNAS_REPORTE, delimiter=";")
    w.writeheader()
    w.writerows(filas_reporte(hallazgos))
    return "﻿" + buf.getvalue()


def main():
    res = analizar()
    salida = CARPETA / "salida"
    salida.mkdir(exist_ok=True)
    for archivo, filas in res["limpios"].items():
        with open(salida / archivo.replace(".csv", "_cln.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    (salida / "reporte_errores_excel.csv").write_text(reporte_excel(res["hallazgos"]), encoding="utf-8")
    resumen = {k: v for k, v in res.items() if k not in ("limpios",)}
    (salida / "reporte.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Registros: {res['total_registros']} · fecha de referencia {res['fecha_referencia']}")
    print(f"{'Fuente':<17}{'Total':>6}{'Antes':>9}{'Después':>9}{'Corregidos':>12}{'Cuarentena':>12}")
    for f in res["por_fuente"]:
        print(f"{f['fuente']:<17}{f['total']:>6}{f['antes']:>9.1%}{f['despues']:>9.1%}"
              f"{f['corregidos']:>12}{f['en_cuarentena']:>12}")
    g = res["global"]
    print(f"{'GLOBAL':<17}{res['total_registros']:>6}{g['antes']:>9.1%}{g['despues']:>9.1%}"
          f"{res['corregidos_automaticamente']:>12}{res['en_cuarentena']:>12}")
    print(f"\nPor regla: {res['por_regla']}")
    print(f"OT: {len(res['ots'])} · dinero involucrado: ${res['impacto_mxn']:,.2f} MXN · pendientes: "
          f"{[p['id_compra'] for p in res['pendientes']]}")
    ev = res.get("evaluacion")
    if ev:
        print(f"\nHoja de respuestas: {ev['detectados_correctos']} de {ev['sembrados']} "
              f"({ev['deteccion']:.0%}) · registros señalados fuera de la hoja: {ev['fuera_de_la_hoja']}")
        for t, v in ev["por_tipo"].items():
            print(f"  {t:<24}{v['detectados']}/{v['sembrados']}")
        for e in ev["no_detectados"]:
            print("  NO detectado:", e)
    print(f"\nArchivos en {salida}")


if __name__ == "__main__":
    main()
