"""Backend de mentira para probar el simulador mientras el real no está listo.

  python mock_api.py --puerto 8000
POST /api/evento  -> valida el contrato y guarda en memoria
GET  /api/eventos -> lista lo recibido
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TIPOS = {"presencia", "peso", "golpe", "inclinacion"}
ORIGENES = {"simulado", "fisico"}
REQUERIDOS = ("estacion", "tipo", "magnitud", "ts", "origen")
EVENTOS = []


def validar(ev):
    if not isinstance(ev, dict):
        return "el cuerpo debe ser un objeto JSON"
    faltan = [k for k in REQUERIDOS if k not in ev]
    if faltan:
        return "faltan campos: " + ", ".join(faltan)
    if ev["tipo"] not in TIPOS:
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

    def do_POST(self):
        if self.path != "/api/evento":
            return self._responder(404, {"error": "no existe"})
        largo = int(self.headers.get("Content-Length", 0))
        try:
            ev = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self._responder(400, {"error": "JSON inválido"})
        error = validar(ev)
        if error:
            return self._responder(422, {"error": error})
        ev["id"] = len(EVENTOS) + 1
        EVENTOS.append(ev)
        print("[%d] %s %s %s %s" % (ev["id"], ev["estacion"], ev["tipo"], ev["magnitud"], ev["origen"]))
        self._responder(201, {"ok": True, "id": ev["id"]})

    def do_GET(self):
        if self.path.startswith("/api/eventos"):
            return self._responder(200, EVENTOS)
        self._responder(404, {"error": "no existe"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8000)
    a = ap.parse_args()
    print("Mock API en http://localhost:%d  (Ctrl+C para salir)" % a.puerto)
    ThreadingHTTPServer(("0.0.0.0", a.puerto), Handler).serve_forever()
