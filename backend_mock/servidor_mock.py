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
  GET   /api/datos, /api/datos/reporte  (motor de limpieza: hallazgos, calidad, evaluación, CSV para Excel)
  GET   /api/series?rango=1h|24h|7d|30d   (historial SIMULADO de 30 días + actividad real de la sesión)

Nota: la correlación usa la HORA EN QUE EL SERVIDOR RECIBE cada mensaje, no el campo ts.
Así no importa si el reloj de la laptop del simulador y la del frontend no coinciden.
"""
import argparse
import json
import re
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------- Parámetros (los afina la persona de datos y reglas) ----------------
VENTANA_ANTES_S = 5         # eventos recibidos hasta 5 s antes del escaneo
VENTANA_DESPUES_S = 20      # y hasta 20 s después
ESPERA_SILENCIO_S = 4       # si ya llegaron presencia y peso, cerrar tras 4 s sin eventos nuevos
TOLERANCIA_PESO = 0.05      # 5 %
SEMBRAR_OT_DATOS = True     # abre una OT por cada hallazgo del motor de limpieza

TIPOS_EVENTO = {"presencia", "peso", "golpe", "inclinacion"}
ORIGENES = {"simulado", "fisico"}
REQUERIDOS = ("estacion", "tipo", "magnitud", "ts", "origen")
ESTADOS_OT = ("abierta", "en_revision", "cerrada")

# ---------------- Datos: vienen del motor de limpieza (datos/motor_limpieza.py) ----------------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "datos"))
from motor_limpieza import analizar, reporte_excel  # noqa: E402

DATOS = analizar()

# Compras que llegan a la estación IoT. B-0001 es C021, la compra que el motor detecta "sin recepción"
# en los datos del equipo; las demás son compras nuevas para la demo (no están en compras.csv).
EN_TRANSITO = [
    ("B-0001", "C021", "SKU-003", 45), ("B-0002", "C022", "SKU-001", 12), ("B-0003", "C023", "SKU-002", 20),
    ("B-0004", "C024", "SKU-004", 40), ("B-0005", "C025", "SKU-003", 10), ("B-0006", "C026", "SKU-001", 4),
]
CATALOGO = DATOS["catalogo"]
BULTOS = {
    b: {"oc": compra, "sku": sku, "descripcion": CATALOGO[sku]["descripcion"], "cantidad": cantidad,
        "peso_kg": round(cantidad * CATALOGO[sku]["peso_unitario_kg"], 2)}
    for b, compra, sku, cantidad in EN_TRANSITO
}
INVENTARIO = dict(DATOS["inventario"])
DESCRIPCION_SKU = {s: c["descripcion"] for s, c in CATALOGO.items()}

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
        "_creada": time.time(),
        "_cerrada": None,
    }
    OTS.append(ot)
    return ot


def sembrar_ot_datos():
    """Una OT por cada hallazgo del motor que no se corrige solo."""
    for ot in DATOS["ots"]:
        nueva_ot(ot["tipo"], ot["prioridad"], ot["causa"], ot["evidencia"])


def resolver_por_recepcion(rec, bulto):
    """Si llega a la estación una compra que el motor marcó 'sin recepción', su OT se cierra sola."""
    for ot in OTS:
        ev = ot["evidencia"][0] if ot["evidencia"] else {}
        if ot["estado"] != "cerrada" and ev.get("regla") == "sin_recepcion" and ev.get("id") == bulto["oc"]:
            ot["estado"] = "cerrada"
            ot["cerrada_ts"] = ahora_ts()
            ot["_cerrada"] = time.time()
            ot["comentario"] = ("Resuelta automáticamente: el bulto %s llegó a la estación %s (recepción %d, %.2f kg)"
                                % (rec["codigo"], rec["estacion"], rec["id"], rec["peso_medido_kg"] or 0))
            rec["resuelve"] = ot["id"]


# ---------------- Recepciones ----------------
def eventos_en_ventana(rec):
    """Eventos de la estación entre este escaneo y el siguiente escaneo en la misma estación."""
    otros = [r["_recibido"] for r in RECEPCIONES if r["estacion"] == rec["estacion"] and r is not rec]
    anterior = max([t for t in otros if t < rec["_recibido"]], default=float("-inf"))
    siguiente = min([t for t in otros if t > rec["_recibido"]], default=float("inf"))
    ini = max(rec["_recibido"] - VENTANA_ANTES_S, anterior)
    fin = min(rec["_recibido"] + VENTANA_DESPUES_S, siguiente)
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
    hay_escaneo_nuevo = any(r["estacion"] == rec["estacion"] and r["_recibido"] > rec["_recibido"]
                            for r in RECEPCIONES)
    ventana_cerrada = t >= rec["_recibido"] + VENTANA_DESPUES_S or (hay_escaneo_nuevo and not evs)
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
    rec["_cerrada"] = time.time()
    if bulto:
        rec["peso_esperado_kg"] = bulto["peso_kg"]
        rec["bulto"]["cantidad"] = bulto["cantidad"]
        if not fallos:
            INVENTARIO[bulto["sku"]] = INVENTARIO.get(bulto["sku"], 0) + bulto["cantidad"]
            resolver_por_recepcion(rec, bulto)


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
    """Índice de calidad: 'antes' = datos crudos; 'después' = corregidos solos + registros cuyas OT ya se cerraron."""
    cerradas = {}
    for ot in OTS:
        for ev in ot["evidencia"]:
            if ev.get("origen") == "datos":
                clave = (ev["fuente"], ev["fila"])
                cerradas[clave] = cerradas.get(clave, True) and ot["estado"] == "cerrada"
    por_fuente = []
    for f in DATOS["por_fuente"]:
        resueltos = sum(1 for linea in f["lineas_en_cuarentena"] if cerradas.get((f["archivo"], linea)))
        sanos_y_corregidos = round(f["despues"] * f["total"])
        por_fuente.append({
            "fuente": f["fuente"], "total": f["total"], "antes": f["antes"],
            "despues": round((sanos_y_corregidos + resueltos) / f["total"], 4),
            "corregidos": f["corregidos"], "en_cuarentena": f["en_cuarentena"] - resueltos, "resueltos": resueltos,
        })
    total_rec = [r for r in RECEPCIONES if r["estado"] != "PENDIENTE"]
    if total_rec:
        ok = sum(r["estado"] == "OK" for r in total_rec) / len(total_rec)
        por_fuente.append({"fuente": "recepciones", "total": len(total_rec), "antes": None, "despues": round(ok, 4)})
    base = [f for f in por_fuente if f["antes"] is not None]
    total = sum(f["total"] for f in base)
    hallazgos = {k: 0 for k in ("duplicado", "dato_incompleto", "cantidad_distinta", "formato",
                                "sin_respaldo_fisico", "inspeccion")}
    for k, n in DATOS["por_categoria"].items():
        hallazgos[k] = hallazgos.get(k, 0) + n
    for ot in OTS:  # las OT de recepciones se suman a los hallazgos de los datos
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
        "corregidos_automaticamente": DATOS["corregidos_automaticamente"],
        "impacto_mxn": DATOS["impacto_mxn"],
        "recepciones": {
            "total": len(total_rec),
            "ok": sum(r["estado"] == "OK" for r in total_rec),
            "sospechosas": sum(r["estado"] == "SOSPECHOSO" for r in total_rec),
            "pendientes": sum(r["estado"] == "PENDIENTE" for r in RECEPCIONES),
        },
    }


def vista_datos():
    """Detalle del motor de limpieza para la pantalla Datos, con el estado actual de cada OT."""
    estado_ot = {}
    for ot in OTS:
        for ev in ot["evidencia"]:
            if ev.get("origen") == "datos":
                estado_ot[(ev["fuente"], ev["fila"], ev.get("regla"))] = (ot["id"], ot["estado"])
    hallazgos = []
    for x in DATOS["hallazgos"]:
        ot_id, estado = estado_ot.get((x["archivo"], x["linea"], x["regla"]), (None, None))
        hallazgos.append({**x, "ot_id": ot_id, "ot_estado": estado})
    c = calidad()
    return {
        "generado": DATOS["generado"], "fecha_referencia": DATOS["fecha_referencia"],
        "total_registros": DATOS["total_registros"], "global": c["global"],
        "por_fuente": [f for f in c["por_fuente"] if f["antes"] is not None],
        "por_regla": DATOS["por_regla"], "por_categoria": DATOS["por_categoria"],
        "corregidos_automaticamente": DATOS["corregidos_automaticamente"],
        "impacto_mxn": DATOS["impacto_mxn"],
        "pendientes": [{**p, "recibido": any(r["estado"] == "OK" and (r.get("bulto") or {}).get("oc") == p["id_compra"]
                                             for r in RECEPCIONES),
                        "bulto_id": next((b for b, v in BULTOS.items() if v["oc"] == p["id_compra"]), None)}
                       for p in DATOS["pendientes"]],
        "evaluacion": DATOS.get("evaluacion"), "hallazgos": hallazgos,
        "limpios": DATOS["limpios"],
    }


# ---------------- Series de tiempo (rangos 1 h, 24 h, 7 d, 30 d) ----------------
RANGOS = {"1h": (3600, 300), "24h": (86400, 3600), "7d": (7 * 86400, 6 * 3600), "30d": (30 * 86400, 86400)}
HISTORIA = []          # actividad simulada de los últimos 30 días, solo para las gráficas
INICIO_SERVIDOR = time.time()


def sembrar_historia(semilla=7):
    """Genera 30 días de actividad simulada en horario laboral (y algo en la última hora)."""
    import random
    rng = random.Random(semilla)
    ahora = time.time()
    hoy = datetime.now().replace(minute=0, second=0, microsecond=0)

    def recepcion(t):
        ok = rng.random() < 0.86
        HISTORIA.append({"t": t, "clase": "rec_ok" if ok else "rec_sosp"})
        if rng.random() > 0.03:
            HISTORIA.append({"t": t + 1, "clase": "presencia"})
            HISTORIA.append({"t": t + 2.5, "clase": "peso"})
        if not ok:
            if rng.random() < 0.35:
                HISTORIA.append({"t": t + 1, "clase": "golpe"})
            if rng.random() < 0.25:
                HISTORIA.append({"t": t + 3, "clase": "inclinacion"})
            HISTORIA.append({"t": t + 5, "clase": "ot_creada"})
            cierre = t + rng.uniform(0.5, 30) * 3600
            if cierre < ahora and rng.random() < 0.85:
                HISTORIA.append({"t": cierre, "clase": "ot_cerrada"})

    for dias in range(30, -1, -1):
        dia = hoy.replace(hour=0) - timedelta(days=dias)
        for hora in range(8, 19):
            for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
                t = (dia + timedelta(hours=hora, minutes=rng.uniform(0, 59))).timestamp()
                if t < ahora - 3600:
                    recepcion(t)
    for _ in range(rng.randint(5, 8)):  # actividad reciente para el rango de 1 h
        recepcion(ahora - rng.uniform(120, 3500))
    HISTORIA.sort(key=lambda x: x["t"])


def calidad_en(t, actual):
    """Índice de calidad simulado: sube de 'antes' a 'después' durante los 30 días."""
    import math
    avance = max(0.0, min(1.0, 1 - (INICIO_SERVIDOR - t) / (30 * 86400)))
    suave = 1 / (1 + math.exp(-8 * (avance - 0.45)))
    ruido = 0.006 * math.sin(t / 7200)
    valor = actual["antes"] + (actual["despues"] - actual["antes"]) * suave + ruido
    return round(min(valor, actual["despues"]), 4)


def series(rango):
    duracion, paso = RANGOS[rango]
    fin = time.time()
    inicio = fin - duracion
    n = duracion // paso
    claves = ["rec_ok", "rec_sosp", "presencia", "peso", "golpe", "inclinacion", "ot_creada", "ot_cerrada"]
    cubetas = [dict.fromkeys(claves, 0) for _ in range(n)]

    def sumar(t, clase):
        if inicio <= t < fin:
            cubetas[min(n - 1, int((t - inicio) // paso))][clase] += 1

    for h in HISTORIA:
        sumar(h["t"], h["clase"])
    for r in RECEPCIONES:  # actividad real de esta sesión
        if r.get("_cerrada"):
            sumar(r["_cerrada"], "rec_ok" if r["estado"] == "OK" else "rec_sosp")
    for e in EVENTOS:
        sumar(e["_recibido"], e["tipo"])
    for o in OTS:
        if o["bulto_id"]:
            sumar(o["_creada"], "ot_creada")
            if o.get("_cerrada"):
                sumar(o["_cerrada"], "ot_cerrada")

    actual = calidad()["global"]
    puntos = []
    for i, c in enumerate(cubetas):
        t = inicio + (i + 1) * paso
        puntos.append({
            "t": datetime.fromtimestamp(inicio + i * paso).isoformat(timespec="minutes"),
            "recepciones_ok": c["rec_ok"], "recepciones_sospechosas": c["rec_sosp"],
            "presencia": c["presencia"], "peso": c["peso"], "golpe": c["golpe"], "inclinacion": c["inclinacion"],
            "ot_creadas": c["ot_creada"], "ot_cerradas": c["ot_cerrada"],
            "calidad": calidad_en(min(t, INICIO_SERVIDOR), actual) if t < INICIO_SERVIDOR else actual["despues"],
        })
    total = lambda k: sum(p[k] for p in puntos)
    rec = total("recepciones_ok") + total("recepciones_sospechosas")
    return {
        "rango": rango, "paso_s": paso, "historico": "simulado",
        "puntos": puntos,
        "totales": {
            "recepciones": rec,
            "recepciones_ok": total("recepciones_ok"),
            "tasa_ok": round(total("recepciones_ok") / rec, 4) if rec else None,
            "eventos": sum(total(k) for k in ("presencia", "peso", "golpe", "inclinacion")),
            "ot_creadas": total("ot_creadas"), "ot_cerradas": total("ot_cerradas"),
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

    def _responder_texto(self, codigo, texto, tipo):
        datos = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
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
                return self._responder(200, [publico(o) for o in reversed(OTS)])
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
            if ruta == "/api/series":
                consulta = dict(p.split("=", 1) for p in self.path.partition("?")[2].split("&") if "=" in p)
                rango = consulta.get("rango", "24h")
                if rango not in RANGOS:
                    return self._responder(422, {"error": "rango inválido; usa 1h, 24h, 7d o 30d"})
                return self._responder(200, series(rango))
            if ruta == "/api/datos":
                return self._responder(200, vista_datos())
            if ruta == "/api/datos/reporte":
                return self._responder_texto(200, reporte_excel(DATOS["hallazgos"]), "text/csv; charset=utf-8")
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
                        ot["_cerrada"] = time.time() if estado == "cerrada" else None
                    if "comentario" in cuerpo:
                        ot["comentario"] = cuerpo["comentario"]
                    return self._responder(200, publico(ot))
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
    sembrar_historia()
    threading.Thread(target=ciclo_evaluador, daemon=True).start()
    ev = DATOS.get("evaluacion") or {}
    print("Motor de limpieza: %d registros, %d hallazgos, %d OT de datos, hoja de respuestas %s/%s"
          % (DATOS["total_registros"], len(DATOS["hallazgos"]), len(DATOS["ots"]),
             ev.get("detectados_correctos", "-"), ev.get("sembrados", "-")))
    print("Backend mock en http://127.0.0.1:%d  (Ctrl+C para salir)" % a.puerto)
    ThreadingHTTPServer(("0.0.0.0", a.puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
