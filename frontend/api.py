"""Cliente del backend según Hackaton/CONTRATO.md.
Las páginas solo llaman a estas funciones; si cambia una ruta o un campo, se corrige aquí."""
import subprocess
import sys
from datetime import datetime

import requests

import config


class ErrorAPI(Exception):
    pass


def _llamar(metodo, ruta, **kwargs):
    url = f"{config.API_URL}{ruta}"
    try:
        r = requests.request(metodo, url, timeout=5, **kwargs)
    except requests.ConnectionError as e:
        raise ErrorAPI(f"No hay conexión con el backend en {config.API_URL}. "
                       "¿Está corriendo servidor_mock.py?") from e
    except requests.RequestException as e:
        raise ErrorAPI(f"Error al llamar {metodo} {ruta}: {e}") from e
    if r.status_code >= 400:
        try:
            detalle = r.json().get("error", r.text)
        except ValueError:
            detalle = r.text
        raise ErrorAPI(f"{metodo} {ruta} respondió {r.status_code}: {detalle}")
    return r.json()


def _ahora():
    return datetime.now().isoformat(timespec="milliseconds")


# ---- Contrato, sección 2: escaneo ----
def escanear(codigo, estacion=None):
    return _llamar("POST", "/api/escaneo", json={
        "codigo": codigo.strip().upper(),
        "estacion": estacion or config.ESTACION,
        "ts": _ahora(),
    })


def obtener_recepcion(recepcion_id):
    return _llamar("GET", f"/api/recepcion/{recepcion_id}")


def listar_recepciones():
    return _llamar("GET", "/api/recepciones")


# ---- Contrato, sección 1: eventos IoT ----
def listar_eventos():
    return _llamar("GET", "/api/eventos")


# ---- Contrato, sección 4: órdenes de trabajo ----
def listar_ot():
    return _llamar("GET", "/api/ot")


def actualizar_ot(ot_id, estado, comentario=None):
    return _llamar("PATCH", f"/api/ot/{ot_id}", json={"estado": estado, "comentario": comentario})


# ---- Agregados para el frontend (CONTRATO.md, sección 6) ----
def listar_bultos():
    return _llamar("GET", "/api/bultos")


def obtener_calidad():
    return _llamar("GET", "/api/calidad")


def obtener_inventario():
    return _llamar("GET", "/api/inventario")


def backend_activo():
    try:
        _llamar("GET", "/api")
        return True
    except ErrorAPI:
        return False


# ---- Simulador de la carpeta IoT ----
def lanzar_simulador(escenarios, peso, estacion=None, velocidad=1.0, ruido=None, semilla=None, pausa=3.0):
    """Ejecuta simulador.py en segundo plano. Envía los eventos a config.API_URL."""
    ruta = config.RUTA_SIMULADOR
    if not ruta.exists():
        raise ErrorAPI(f"No se encontró el simulador en {ruta}")
    comando = [
        sys.executable, ruta.name,
        "--escenario", ",".join(escenarios),
        "--peso", str(peso),
        "--estacion", estacion or config.ESTACION,
        "--api", config.API_URL,
        "--velocidad", str(velocidad),
        "--pausa", str(pausa),
    ]
    if ruido is not None:
        comando += ["--ruido", str(ruido)]
    if semilla is not None:
        comando += ["--semilla", str(int(semilla))]
    subprocess.Popen(comando, cwd=ruta.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return comando
