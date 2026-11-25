"""Backend de integración (de mentira) que implementa Hackaton/CONTRATO.md completo.

Sirve para que el frontend, el simulador IoT y las reglas funcionen juntos mientras
la persona 1 termina el backend real en FastAPI. Solo usa la librería estándar.

  python servidor_mock.py                 (puerto 8000)
  python servidor_mock.py --puerto 8000 --silencio 4

Endpoints del contrato:
  POST  /api/evento        eventos del simulador o del ESP32
  GET   /api/eventos       lista de eventos recibidos
  POST  /api/escaneo       escaneo de QR desde el frontend
  GET   /api/ot            órdenes de trabajo
  PATCH /api/ot/{id}       cambiar estado / comentario
Agregados para el frontend (ver sección 6 de CONTRATO.md):
  GET   /api/recepcion/{id}, /api/recepciones, /api/bultos, /api/calidad, /api/inventario

Nota: la correlación usa la HORA EN QUE EL SERVIDOR RECIBE cada mensaje, no el campo ts.
Así no importa si el reloj de la laptop del simulador y la del frontend no coinciden.
"""
import argparse
import json
import re
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------- Parámetros (los afina la persona de datos y reglas) ----------------
VENTANA_ANTES_S = 5         # eventos recibidos hasta 5 s antes del escaneo
VENTANA_DESPUES_S = 20      # y hasta 20 s después
ESPERA_SILENCIO_S = 4       # si ya llegaron presencia y peso, cerrar tras 4 s sin eventos nuevos
TOLERANCIA_PESO = 0.05      # 5 %
SEMBRAR_OT_DATOS = True     # OT de ejemplo de los CSV hasta que la persona 2 conecte su limpieza

TIPOS_EVENTO = {"presencia", "peso", "golpe", "inclinacion"}
ORIGENES = {"simulado", "fisico"}
REQUERIDOS = ("estacion", "tipo", "magnitud", "ts", "origen")
ESTADOS_OT = ("abierta", "en_revision", "cerrada")

# ---------------- Datos de ejemplo (después vienen de la base de datos) ----------------
BULTOS = {
    "B-0001": {"oc": "OC-1042", "sku": "1001", "descripcion": "Tornillo hexagonal M6x20 (caja)", "cantidad": 500, "peso_kg": 12.50},
    "B-0002": {"oc": "OC-1042", "sku": "1002", "descripcion": "Rondana plana 1/4 (caja)", "cantidad": 1000, "peso_kg": 8.00},
    "B-0003": {"oc": "OC-1043", "sku": "1003", "descripcion": "Rodamiento 6204", "cantidad": 40, "peso_kg": 4.40},
    "B-0004": {"oc": "OC-1044", "sku": "1004", "descripcion": "Cable THW calibre 14 (rollo 100 m)", "cantidad": 1, "peso_kg": 3.00},
    "B-0005": {"oc": "OC-1045", "sku": "1005", "descripcion": "Grasa de litio (cubeta)", "cantidad": 1, "peso_kg": 19.00},
    "B-0006": {"oc": "OC-1046", "sku": "1006", "descripcion": "Filtro de aceite (caja de 12)", "cantidad": 12, "peso_kg": 6.20},
}
INVENTARIO = {"1001": 1200, "1002": 3400, "1003": 18, "1004": 6, "1005": 2, "1006": 24}
DESCRIPCION_SKU = {b["sku"]: b["descripcion"] for b in BULTOS.values()}

CALIDAD_CSV = [  # lo reemplaza la persona 2 con su limpieza real
    {"fuente": "compras", "total": 420, "antes": 0.81, "despues": 0.97},
    {"fuente": "almacen", "total": 610, "antes": 0.74, "despues": 0.95},
    {"fuente": "costos", "total": 150, "antes": 0.88, "despues": 0.99},
    {"fuente": "ot_operativas", "total": 380, "antes": 0.69, "despues": 0.93},
]

EVENTOS = []
RECEPCIONES = []
OTS = []
FOLIOS_RECIBIDOS = set()
CANDADO = threading.RLock()


def ahora_ts():
    return datetime.now().isoformat(timespec="milliseconds")


# ---------------- Órdenes de trabajo ----------------
def nueva_ot(tipo, prioridad, causa, evidencia, bulto_id=None, estacion=None):
    ot = {
        "id": "OT-%04d" % (len(OTS) + 1),
        "tipo": tipo,
        "prioridad": prioridad,
        "causa": causa,
        "evidencia": evidencia,
        "bulto_id": bulto_id,
        "estacion": estacion,
        "estado": "abierta",
        "creada_ts": ahora_ts(),
        "cerrada_ts": None,
        "comentario": None,
    }
    OTS.append(ot)
    return ot


def sembrar_ot_datos():
    ev = lambda fuente, fila, detalle: [{"tipo": "registro", "fuente": fuente, "fila": fila,
                                         "detalle": detalle, "origen": "datos"}]
    nueva_ot("duplicado", "media", "Factura F-2231 capturada dos veces en compras con descripción distinta",
             ev("compras.csv", 118, "filas 118 y 131, similitud 93 %"))
    nueva_ot("dato_incompleto", "baja", "Movimiento de almacén sin responsable",
             ev("almacen.csv", 77, "campo responsable vacío"))
    nueva_ot("dato_incompleto", "media", "OT operativa con costo vacío y SKU inexistente (9999)",
             ev("ot_operativas.csv", 41, "costo_total vacío, sku 9999"))
    nueva_ot("cantidad_distinta", "media", "Almacén registró 92 piezas y compras 100 (OC-1040)",
             ev("almacen.csv", 203, "compras 100 vs almacén 92"))


# ---------------- Recepciones ----------------
def eventos_en_ventana(rec):
    ini = rec["_recibido"] - VENTANA_ANTES_S
    fin = rec["_recibido"] + VENTANA_DESPUES_S
    return [e for e in EVENTOS
            if e["estacion"] == rec["estacion"] and ini <= e["_recibido"] <= fin
            and e.get("_usado_por") in (None, rec["id"])]


def evaluar(rec, forzar=False):
    """Actualiza los chequeos. Cierra la recepción cuando corresponde."""
    if rec["estado"] != "PENDIENTE":
        return
    evs = eventos_en_ventana(rec)
    rec["eventos"] = [publico(e) for e in evs]
    t = time.time()
    presencias = [e for e in evs if e["tipo"] == "presencia"]
    pesos = [e for e in evs if e["tipo"] == "peso"]
    golpes = [e for e in evs if e["tipo"] == "golpe"]
    inclinaciones = [e for e in evs if e["tipo"] == "inclinacion"]

    # Chequeos visibles mientras espera
    rec["checks"]["presencia"] = "OK" if presencias else "PENDIENTE"
    rec["checks"]["manipulacion"] = "FALLO" if (golpes or inclinaciones) else "PENDIENTE"

    ultimo = max([e["_recibido"] for e in evs], default=rec["_recibido"])
    ventana_cerrada = t >= rec["_recibido"] + VENTANA_DESPUES_S
    completo = presencias and pesos and t >= ultimo + ESPERA_SILENCIO_S
    if not (forzar or ventana_cerrada or completo):
        return

    # ---- Resultado final ----
    bulto = BULTOS.get(rec["codigo"])
    ch = rec["checks"]
    fallos = []  # (check, tipo_ot, causa, evidencia)

    if ch["qr"] == "FALLO":
        tipo = "duplicado" if rec["_duplicado"] else "dato_incompleto"
        fallos.append(("qr", tipo, rec["mensaje"], [{"tipo": "qr", "codigo": rec["codigo"], "origen": "escaneo"}]))

    if presencias:
        ch["presencia"] = "OK"
    else:
        ch["presencia"] = "FALLO"
        fallos.append(("presencia", "sin_respaldo_fisico",
                       "Se escaneó %s y no se detectó ningún bulto en la estación %s" % (rec["codigo"], rec["estacion"]),
                       []))

    if pesos:
        medido = pesos[-1]["magnitud"]
        rec["peso_medido_kg"] = medido
        if bulto:
            esperado = bulto["peso_kg"]
            dif = (medido - esperado) / esperado
            rec["diferencia_pct"] = round(dif * 100, 1)
            if abs(dif) <= TOLERANCIA_PESO:
                ch["peso"] = "OK"
            else:
                ch["peso"] = "FALLO"
                fallos.append(("peso", "cantidad_distinta",
                               "Peso medido %.2f kg vs esperado %.2f kg (%+.1f %%)" % (medido, esperado, dif * 100),
                               [publico(pesos[-1])]))
        else:
            ch["peso"] = "FALLO"
            fallos.append(("peso", "cantidad_distinta", "Peso %.2f kg sin peso esperado: bulto no registrado" % medido,
                           [publico(pesos[-1])]))
    else:
        ch["peso"] = "FALLO"
        fallos.append(("peso", "cantidad_distinta", "No llegó lectura de peso de la estación", []))

    if golpes or inclinaciones:
        ch["manipulacion"] = "FALLO"
        partes = []
        if golpes:
            partes.append("golpe de %.2f g" % max(e["magnitud"] for e in golpes))
        if inclinaciones:
            partes.append("inclinación de %.1f°" % max(e["magnitud"] for e in inclinaciones))
        fallos.append(("manipulacion", "inspeccion", "Manipulación brusca: " + " y ".join(partes),
                       [publico(e) for e in golpes + inclinaciones]))
    else:
        ch["manipulacion"] = "OK"

    # Prioridad según el contrato: 1 fallo baja, 2 media, 3+ o golpe alta
    n = len(fallos)
    prioridad = "alta" if (n >= 3 or golpes) else "media" if n == 2 else "baja"
    for _, tipo, causa, evidencia in fallos:
        ot = nueva_ot(tipo, prioridad, causa, evidencia, rec["codigo"], rec["estacion"])
        rec["ots"].append(ot["id"])

    for e in evs:
        e["_usado_por"] = rec["id"]
    rec["eventos"] = [publico(e) for e in evs]
    rec["estado"] = "OK" if not fallos else "SOSPECHOSO"
    rec["cerrada_ts"] = ahora_ts()
    if bulto:
        rec["peso_esperado_kg"] = bulto["peso_kg"]
        rec["bulto"]["cantidad"] = bulto["cantidad"]
        if not fallos:
            INVENTARIO[bulto["sku"]] = INVENTARIO.get(bulto["sku"], 0) + bulto["cantidad"]


def vista_recepcion(rec):
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def publico(e):
    return {k: v for k, v in e.items() if not k.startswith("_")}


def ciclo_evaluador():
    """Evalúa recepciones pendientes cada segundo, aunque nadie esté consultando."""
    while True:
        time.sleep(1)
        with CANDADO:
            for rec in RECEPCIONES:
                evaluar(rec)


# ---------------- Calidad ----------------
def calidad():
    total_rec = [r for r in RECEPCIONES if r["estado"] != "PENDIENTE"]
    por_fuente = [dict(f) for f in CALIDAD_CSV]
    if total_rec:
        ok = sum(r["estado"] == "OK" for r in total_rec) / len(total_rec)
        por_fuente.append({"fuente": "recepciones", "total": len(total_rec), "antes": None, "despues": round(ok, 4)})
    base = [f for f in por_fuente if f["antes"] is not None]
    total = sum(f["total"] for f in base)
    hallazgos = {"duplicado": 37, "dato_incompleto": 58, "cantidad_distinta": 24,
                 "sin_respaldo_fisico": 0, "inspeccion": 0}
    for ot in OTS:  # las OT de recepciones se suman a los hallazgos de los CSV
        if ot["bulto_id"]:
            hallazgos[ot["tipo"]] = hallazgos.get(ot["tipo"], 0) + 1
    return {
        "global": {
            "antes": round(sum(f["antes"] * f["total"] for f in base) / total, 4),
            "despues": round(sum(f["despues"] * f["total"] for f in base) / total, 4),
        },
        "total_registros": total + len(total_rec),
        "por_fuente": por_fuente,
        "hallazgos": hallazgos,
        "recepciones": {
            "total": len(total_rec),
            "ok": sum(r["estado"] == "OK" for r in total_rec),
            "sospechosas": sum(r["estado"] == "SOSPECHOSO" for r in total_rec),
            "pendientes": sum(r["estado"] == "PENDIENTE" for r in RECEPCIONES),
        },
    }


# ---------------- HTTP ----------------
def validar_evento(ev):
    if not isinstance(ev, dict):
        return "el cuerpo debe ser un objeto JSON"
    faltan = [k for k in REQUERIDOS if k not in ev]
    if faltan:
        return "faltan campos: " + ", ".join(faltan)
    if ev["tipo"] not in TIPOS_EVENTO:
        return "tipo inválido: %r" % ev["tipo"]
    if ev["origen"] not in ORIGENES:
        return "origen inválido: %r" % ev["origen"]
    if not isinstance(ev["magnitud"], (int, float)) or isinstance(ev["magnitud"], bool):
        return "magnitud debe ser numérica"
    return None


class Handler(BaseHTTPRequestHandler):
    def _responder(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _cuerpo(self):
        largo = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(largo) or b"{}")

    def do_GET(self):
        ruta = self.path.split("?")[0].rstrip("/")
        with CANDADO:
            if ruta in ("", "/api"):
                return self._responder(200, {"ok": True, "servicio": "backend_mock"})
            if ruta == "/api/eventos":
                return self._responder(200, [publico(e) for e in EVENTOS])
            if ruta == "/api/ot":
                return self._responder(200, list(reversed(OTS)))
            if ruta == "/api/recepciones":
                return self._responder(200, [vista_recepcion(r) for r in reversed(RECEPCIONES)])
            m = re.fullmatch(r"/api/recepcion/(\d+)", ruta)
            if m:
                rid = int(m.group(1))
                if not 1 <= rid <= len(RECEPCIONES):
                    return self._responder(404, {"error": "no existe la recepción %d" % rid})
                rec = RECEPCIONES[rid - 1]
                evaluar(rec)
                return self._responder(200, vista_recepcion(rec))
            if ruta == "/api/bultos":
                return self._responder(200, [{"bulto_id": k, **v} for k, v in BULTOS.items()])
            if ruta == "/api/calidad":
                return self._responder(200, calidad())
            if ruta == "/api/inventario":
                return self._responder(200, [{"sku": s, "descripcion": DESCRIPCION_SKU.get(s, ""), "existencia": c}
                                             for s, c in INVENTARIO.items()])
        self._responder(404, {"error": "no existe"})

    def do_POST(self):
        ruta = self.path.split("?")[0].rstrip("/")
        try:
            cuerpo = self._cuerpo()
        except json.JSONDecodeError:
            return self._responder(400, {"error": "JSON inválido"})

        if ruta == "/api/evento":
            error = validar_evento(cuerpo)
            if error:
                return self._responder(422, {"error": error})
            with CANDADO:
                cuerpo["id"] = len(EVENTOS) + 1
                cuerpo["_recibido"] = time.time()
                EVENTOS.append(cuerpo)
            print("[evento %d] %s %-11s %7.2f %s" % (cuerpo["id"], cuerpo["estacion"], cuerpo["tipo"],
                                                     cuerpo["magnitud"], cuerpo["origen"]))
            return self._responder(201, {"ok": True, "id": cuerpo["id"]})

        if ruta == "/api/escaneo":
            codigo = str(cuerpo.get("codigo", "")).strip().upper()
            estacion = str(cuerpo.get("estacion", "")).strip()
            if not codigo or not estacion:
                return self._responder(422, {"error": "faltan campos: codigo, estacion"})
            with CANDADO:
                bulto = BULTOS.get(codigo)
                duplicado = codigo in FOLIOS_RECIBIDOS
                if bulto is None:
                    mensaje = "El código %s no existe en la base de datos" % codigo
                elif duplicado:
                    mensaje = "El folio %s ya se había escaneado en otra recepción" % codigo
                else:
                    mensaje = "QR válido"
                FOLIOS_RECIBIDOS.add(codigo)
                rec = {
                    "id": len(RECEPCIONES) + 1,
                    "codigo": codigo,
                    "estacion": estacion,
                    "ts": cuerpo.get("ts") or ahora_ts(),
                    "estado": "PENDIENTE",
                    "mensaje": mensaje,
                    "bulto": ({"bulto_id": codigo, "oc": bulto["oc"], "sku": bulto["sku"],
                               "descripcion": bulto["descripcion"]} if bulto else None),
                    "checks": {"qr": "OK" if (bulto and not duplicado) else "FALLO",
                               "presencia": "PENDIENTE", "peso": "PENDIENTE", "manipulacion": "PENDIENTE"},
                    "peso_medido_kg": None,
                    "peso_esperado_kg": None,   # recepción ciega: se revela al cerrar
                    "diferencia_pct": None,
                    "eventos": [],
                    "ots": [],
                    "cerrada_ts": None,
                    "_recibido": time.time(),
                    "_duplicado": duplicado,
                }
                RECEPCIONES.append(rec)
            print("[escaneo] recepción %d: %s en %s (%s)" % (rec["id"], codigo, estacion, mensaje))
            return self._responder(201, {"ok": True, "recepcion_id": rec["id"], "estado": "PENDIENTE",
                                         "qr_valido": rec["checks"]["qr"] == "OK", "mensaje": mensaje,
                                         "bulto": rec["bulto"]})

        self._responder(404, {"error": "no existe"})

    def do_PATCH(self):
        ruta = self.path.split("?")[0].rstrip("/")
        m = re.fullmatch(r"/api/ot/(OT-\d+)", ruta)
        if not m:
            return self._responder(404, {"error": "no existe"})
        try:
            cuerpo = self._cuerpo()
        except json.JSONDecodeError:
            return self._responder(400, {"error": "JSON inválido"})
        estado = cuerpo.get("estado")
        if estado is not None and estado not in ESTADOS_OT:
            return self._responder(422, {"error": "estado inválido: %r" % estado})
        with CANDADO:
            for ot in OTS:
                if ot["id"] == m.group(1):
                    if estado:
                        ot["estado"] = estado
                        ot["cerrada_ts"] = ahora_ts() if estado == "cerrada" else None
                    if "comentario" in cuerpo:
                        ot["comentario"] = cuerpo["comentario"]
                    return self._responder(200, ot)
        self._responder(404, {"error": "no existe la OT %s" % m.group(1)})

    def log_message(self, *a):
        pass


def main():
    global ESPERA_SILENCIO_S, VENTANA_DESPUES_S
    ap = argparse.ArgumentParser(description="Backend de integración (mock) del contrato v1")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--silencio", type=float, default=ESPERA_SILENCIO_S,
                    help="segundos sin eventos para cerrar una recepción que ya tiene presencia y peso")
    ap.add_argument("--ventana", type=float, default=VENTANA_DESPUES_S,
                    help="segundos después del escaneo en que se aceptan eventos")
    a = ap.parse_args()
    ESPERA_SILENCIO_S, VENTANA_DESPUES_S = a.silencio, a.ventana
    if SEMBRAR_OT_DATOS:
        sembrar_ot_datos()
    threading.Thread(target=ciclo_evaluador, daemon=True).start()
    print("Backend mock en http://localhost:%d  (Ctrl+C para salir)" % a.puerto)
    ThreadingHTTPServer(("0.0.0.0", a.puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
