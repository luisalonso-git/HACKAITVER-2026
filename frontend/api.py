"""Cliente de la API. Todas las páginas llaman a estas funciones, nunca a requests directo.
Si config.USAR_MOCK es True, responde el backend simulado (mock_api.py)."""
import requests

import config
import mock_api


class ErrorAPI(Exception):
    pass


def _llamar(metodo, ruta, **kwargs):
    url = f"{config.API_URL}{ruta}"
    try:
        r = requests.request(metodo, url, timeout=5, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise ErrorAPI(f"Error al llamar {metodo} {ruta}: {e}") from e


def _mock(funcion, *args):
    try:
        return funcion(*args)
    except (KeyError, ValueError) as e:
        raise ErrorAPI(e.args[0] if e.args else str(e)) from e


def escanear_qr(qr, estacion=None):
    estacion = estacion or config.ESTACION
    if config.USAR_MOCK:
        return _mock(mock_api.escanear_qr, qr, estacion)
    return _llamar("POST", "/api/recepcion/scan", json={"qr": qr, "estacion": estacion})


def obtener_recepcion(recepcion_id):
    if config.USAR_MOCK:
        return _mock(mock_api.obtener_recepcion, recepcion_id)
    return _llamar("GET", f"/api/recepcion/{recepcion_id}")


def listar_ot():
    if config.USAR_MOCK:
        return mock_api.listar_ot()
    return _llamar("GET", "/api/ot")


def actualizar_ot(ot_id, estado, resolucion=None):
    if config.USAR_MOCK:
        return _mock(mock_api.actualizar_ot, ot_id, estado, resolucion)
    return _llamar("PATCH", f"/api/ot/{ot_id}", json={"estado": estado, "resolucion": resolucion})


def obtener_calidad():
    if config.USAR_MOCK:
        return mock_api.obtener_calidad()
    return _llamar("GET", "/api/calidad")


def obtener_inventario():
    if config.USAR_MOCK:
        return mock_api.obtener_inventario()
    return _llamar("GET", "/api/inventario")
