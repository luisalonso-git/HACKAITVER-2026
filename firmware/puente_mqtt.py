"""Puente MQTT → backend: recibe los eventos que publica el ESP32 (Wokwi o real) y los manda a /api/evento.

  python -m pip install paho-mqtt
  python firmware/puente_mqtt.py
  python firmware/puente_mqtt.py --api http://127.0.0.1:8000 --topico kardexvivo/hackaitver2026/eventos
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.exit("Falta paho-mqtt. Instálalo con:  python -m pip install paho-mqtt")


def reenviar(api, evento):
    if not evento.get("ts"):
        evento["ts"] = datetime.now().isoformat(timespec="milliseconds")  # el ESP32 no tiene reloj
    peticion = urllib.request.Request(api.rstrip("/") + "/api/evento", data=json.dumps(evento).encode("utf-8"),
                                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return f"{e.code} {e.read().decode('utf-8', 'replace')}"
    except (urllib.error.URLError, OSError) as e:
        return f"sin conexión con el backend ({e})"


def main():
    ap = argparse.ArgumentParser(description="Puente MQTT → backend de Kardex Vivo")
    ap.add_argument("--broker", default="broker.hivemq.com")
    ap.add_argument("--puerto", type=int, default=1883)
    ap.add_argument("--topico", default="kardexvivo/hackaitver2026/eventos")
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    a = ap.parse_args()

    def al_conectar(cliente, *args):
        print(f"Conectado a {a.broker}. Escuchando '{a.topico}' y reenviando a {a.api}/api/evento")
        cliente.subscribe(a.topico)

    def al_recibir(cliente, datos, mensaje):
        try:
            evento = json.loads(mensaje.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            print("  mensaje ignorado (no es JSON):", mensaje.payload[:80])
            return
        resultado = reenviar(a.api, evento)
        print(f"  {datetime.now():%H:%M:%S}  {evento.get('estacion')}  {evento.get('tipo', '?'):<11} "
              f"{evento.get('magnitud')}  {evento.get('origen')}  ->  {resultado}")

    try:  # paho-mqtt 2.x
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:  # paho-mqtt 1.x
        cliente = mqtt.Client()
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir
    print(f"Conectando a {a.broker}:{a.puerto} ...")
    cliente.connect(a.broker, a.puerto, keepalive=30)
    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nPuente detenido.")


if __name__ == "__main__":
    main()
