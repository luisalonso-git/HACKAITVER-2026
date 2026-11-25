"""Backend simulado. Imita las respuestas del contrato para trabajar sin FastAPI.

Escenarios de demo según el lote del QR:
  lote terminado en 1 (o cualquier otro) -> recepción correcta
  lote terminado en 2                    -> peso 18 % menor (faltante)
  lote terminado en 3                    -> no hay producto en la báscula
  mismo QR escaneado dos veces           -> duplicado
  orden de compra o artículo inexistente -> QR inválido
"""
import random
import threading
import time
from datetime import datetime

from utils import interpretar_qr

SEGUNDOS_PARA_LECTURA = 5  # lo que "tarda" la báscula en mandar el evento

CATALOGO = {
    "1001": {"descripcion": "Tornillo hexagonal M6x20", "peso_unitario_kg": 0.005, "tolerancia_pct": 2},
    "1002": {"descripcion": "Rondana plana 1/4", "peso_unitario_kg": 0.002, "tolerancia_pct": 3},
    "1003": {"descripcion": "Rodamiento 6204", "peso_unitario_kg": 0.110, "tolerancia_pct": 1},
    "1004": {"descripcion": "Cable THW calibre 14 (m)", "peso_unitario_kg": 0.030, "tolerancia_pct": 2},
}

ORDENES_COMPRA = {
    "1042": {"proveedor": "Ferretera del Golfo", "articulos": {"1001": 500, "1002": 1000}},
    "1043": {"proveedor": "Rodamientos del Puerto", "articulos": {"1003": 40}},
    "1044": {"proveedor": "Eléctrica Veracruz", "articulos": {"1004": 200}},
}

_inventario = {"1001": 1200, "1002": 3400, "1003": 18, "1004": 450}
_recepciones = {}
_qr_usados = set()
_ots = []
_contador = {"recepcion": 0, "ot": 0}
_candado = threading.Lock()

# Hallazgos que ya habría encontrado la limpieza de los CSV
_HALLAZGOS_CSV = {
    "DUPLICADO": 37,
    "REGISTRO_INCOMPLETO": 58,
    "DIFERENCIA_CANTIDAD": 24,
    "INCONSISTENCIA_COSTO": 11,
}


def _ahora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _nueva_ot(tipo, prioridad, causa, evidencia, origen, referencias,
              asignado_a="Almacén", estado="ABIERTA"):
    _contador["ot"] += 1
    ot = {
        "ot_id": f"OTV-{_contador['ot']:04d}",
        "tipo": tipo,
        "prioridad": prioridad,
        "causa": causa,
        "evidencia": evidencia,
        "origen": origen,
        "referencias": referencias,
        "estado": estado,
        "asignado_a": asignado_a,
        "creada": _ahora(),
        "cerrada": None,
        "resolucion": None,
    }
    _ots.append(ot)
    return ot


def _sembrar_ots():
    _nueva_ot("DUPLICADO", "MEDIA",
              "La factura F-2231 aparece dos veces en compras con descripción distinta",
              {"registros": ["compras#118", "compras#131"], "similitud_descripcion": 0.93},
              "CSV", {"orden_compra": "1039", "articulo": "1001"}, asignado_a="Compras")
    _nueva_ot("REGISTRO_INCOMPLETO", "BAJA",
              "Movimiento de almacén sin responsable",
              {"registro": "almacen#77", "campos_vacios": ["responsable"]},
              "CSV", {"articulo": "1002"})
    _nueva_ot("INCONSISTENCIA_COSTO", "ALTA",
              "Costo en la OT operativa 14 % mayor al costo vigente",
              {"costo_ot": 1140.0, "costo_vigente": 1000.0},
              "CSV", {"ot_operativa": "OT-558", "articulo": "1003"}, asignado_a="Costos")
    _nueva_ot("DIFERENCIA_CANTIDAD", "MEDIA",
              "Almacén registró 92 piezas y compras 100",
              {"compras": 100, "almacen": 92},
              "CSV", {"orden_compra": "1040", "articulo": "1004"}, estado="EN_REVISION")


_sembrar_ots()


def escanear_qr(qr, estacion):
    datos = interpretar_qr(qr)
    if datos is None:
        raise ValueError("Formato de QR no válido")
    oc, art, lote = datos["orden_compra"], datos["articulo"], datos["lote"]
    with _candado:
        _contador["recepcion"] += 1
        rid = _contador["recepcion"]
        existe = oc in ORDENES_COMPRA and art in ORDENES_COMPRA[oc]["articulos"]
        duplicado = qr in _qr_usados
        _qr_usados.add(qr)
        qr_ok = existe and not duplicado
        if not existe:
            mensaje = "El QR no corresponde a ninguna orden de compra abierta"
        elif duplicado:
            mensaje = "Este QR ya se había usado en otra recepción"
        else:
            mensaje = "QR válido"
        _recepciones[rid] = {
            "recepcion_id": rid, "qr": qr, "estacion": estacion,
            "orden_compra": oc, "articulo": art, "lote": lote,
            "descripcion": CATALOGO.get(art, {}).get("descripcion", "Artículo desconocido"),
            "inicio": time.time(), "estado": "PENDIENTE",
            "existe": existe, "duplicado": duplicado, "mensaje": mensaje,
            "checks": {"qr": "OK" if qr_ok else "FALLO", "presencia": "PENDIENTE", "peso": "PENDIENTE"},
            "peso_kg": None, "peso_esperado_kg": None,
            "cantidad_calculada": None, "cantidad_esperada": None, "ot_id": None,
        }
        rec = _recepciones[rid]
        return {
            "recepcion_id": rid, "estado": "PENDIENTE", "qr_valido": qr_ok, "mensaje": mensaje,
            "orden_compra": oc, "articulo": art, "lote": lote, "descripcion": rec["descripcion"],
        }


def _resolver(rec):
    art = rec["articulo"]
    info = CATALOGO.get(art, {"peso_unitario_kg": 0.01, "tolerancia_pct": 2})
    peso_u = info["peso_unitario_kg"]
    esperada = ORDENES_COMPRA[rec["orden_compra"]]["articulos"][art] if rec["existe"] else 0
    peso_esperado = esperada * peso_u

    if rec["lote"].endswith("3"):
        presencia, peso = False, 0.0
    elif rec["lote"].endswith("2"):
        presencia, peso = True, peso_esperado * 0.82
    else:
        presencia = True
        peso = peso_esperado * random.uniform(0.995, 1.005) if esperada else random.uniform(1.0, 3.0)

    peso_ok = (presencia and esperada > 0
               and abs(peso - peso_esperado) <= peso_esperado * info["tolerancia_pct"] / 100)
    rec["checks"]["presencia"] = "OK" if presencia else "FALLO"
    rec["checks"]["peso"] = "OK" if peso_ok else "FALLO"
    rec["peso_kg"] = round(peso, 3)
    rec["peso_esperado_kg"] = round(peso_esperado, 3)
    rec["cantidad_calculada"] = round(peso / peso_u) if peso_u else 0
    rec["cantidad_esperada"] = esperada

    fallos = [k for k, v in rec["checks"].items() if v == "FALLO"]
    if not fallos:
        rec["estado"] = "OK"
        _inventario[art] = _inventario.get(art, 0) + rec["cantidad_calculada"]
        return

    rec["estado"] = "SOSPECHOSO"
    motivos = []
    if "qr" in fallos:
        motivos.append(rec["mensaje"])
    if "presencia" in fallos:
        motivos.append("No se detectó producto en la báscula")
    if "peso" in fallos and presencia and esperada:
        diferencia = (peso - peso_esperado) / peso_esperado * 100
        motivos.append(f"Peso {abs(diferencia):.0f} % {'menor' if diferencia < 0 else 'mayor'} al esperado")
    if fallos == ["qr"] and rec["duplicado"]:
        tipo = "DUPLICADO"
    elif fallos == ["peso"]:
        tipo = "DIFERENCIA_CANTIDAD"
    else:
        tipo = "RECEPCION_SOSPECHOSA"
    ot = _nueva_ot(
        tipo, "ALTA" if len(fallos) >= 2 else "MEDIA", "; ".join(motivos),
        {**rec["checks"], "peso_kg": rec["peso_kg"], "peso_esperado_kg": rec["peso_esperado_kg"]},
        "IOT",
        {"orden_compra": rec["orden_compra"], "articulo": art, "recepcion_id": rec["recepcion_id"]},
    )
    rec["ot_id"] = ot["ot_id"]


def _vista(rec):
    terminado = rec["estado"] != "PENDIENTE"
    return {
        "recepcion_id": rec["recepcion_id"],
        "estado": rec["estado"],
        "checks": dict(rec["checks"]),
        "orden_compra": rec["orden_compra"],
        "articulo": rec["articulo"],
        "lote": rec["lote"],
        "descripcion": rec["descripcion"],
        "mensaje": rec["mensaje"],
        "peso_kg": rec["peso_kg"],
        "cantidad_calculada": rec["cantidad_calculada"],
        # Recepción ciega: lo esperado solo se revela al terminar
        "peso_esperado_kg": rec["peso_esperado_kg"] if terminado else None,
        "cantidad_esperada": rec["cantidad_esperada"] if terminado else None,
        "ot_id": rec["ot_id"],
    }


def obtener_recepcion(recepcion_id):
    with _candado:
        rec = _recepciones.get(int(recepcion_id))
        if rec is None:
            raise KeyError(f"No existe la recepción {recepcion_id}")
        if rec["estado"] == "PENDIENTE" and time.time() - rec["inicio"] >= SEGUNDOS_PARA_LECTURA:
            _resolver(rec)
        return _vista(rec)


def listar_ot():
    with _candado:
        return [dict(ot) for ot in reversed(_ots)]


def actualizar_ot(ot_id, estado, resolucion=None):
    with _candado:
        for ot in _ots:
            if ot["ot_id"] == ot_id:
                ot["estado"] = estado
                ot["resolucion"] = resolucion
                ot["cerrada"] = _ahora() if estado == "CERRADA" else None
                return dict(ot)
    raise KeyError(f"No existe la OT {ot_id}")


def obtener_calidad():
    por_fuente = [
        {"fuente": "compras", "total": 420, "antes": 0.81, "despues": 0.97},
        {"fuente": "almacen", "total": 610, "antes": 0.74, "despues": 0.95},
        {"fuente": "costos", "total": 150, "antes": 0.88, "despues": 0.99},
        {"fuente": "ot_operativas", "total": 380, "antes": 0.69, "despues": 0.93},
    ]
    total = sum(f["total"] for f in por_fuente)
    antes = sum(f["antes"] * f["total"] for f in por_fuente) / total
    despues = sum(f["despues"] * f["total"] for f in por_fuente) / total
    with _candado:
        hallazgos = dict(_HALLAZGOS_CSV)
        hallazgos["RECEPCION_SOSPECHOSA"] = 0
        for ot in _ots:
            if ot["origen"] == "IOT":
                hallazgos[ot["tipo"]] = hallazgos.get(ot["tipo"], 0) + 1
    return {
        "global": {"antes": round(antes, 4), "despues": round(despues, 4)},
        "total_registros": total,
        "por_fuente": por_fuente,
        "hallazgos": hallazgos,
    }


def obtener_inventario():
    with _candado:
        return [
            {"articulo": art, "descripcion": CATALOGO[art]["descripcion"], "existencia": cant}
            for art, cant in _inventario.items()
        ]
