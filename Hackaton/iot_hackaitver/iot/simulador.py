"""Simulador de la estación IoT (MPU6050 + celda de carga).

Genera una señal de aceleración a 100 Hz, la pasa por el MISMO detector que irá
en el ESP32 y envía los eventos al backend con el contrato de CONTRATO.md.
Los eventos salen marcados con origen = "simulado".

Ejemplos:
  python simulador.py --escenario normal --peso 12.5
  python simulador.py --escenario normal,golpe,peso_bajo --pausa 5
  python simulador.py --escenario inclinado --dry-run --rapido
"""
import argparse
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from detector import Detector

FS = 100              # muestras por segundo
RUIDO_G = 0.02        # desviación estándar del ruido del acelerómetro
DURACION_S = 4.0
T_IMPACTO = 1.0       # instante en que se coloca el bulto
T_INCLINACION = 2.5   # instante en que empieza a inclinarse
T_PESO = T_IMPACTO + 1.5   # la celda de carga se estabiliza 1.5 s después

# amp: pico del impulso al colocar el bulto (g); None = no llega ningún bulto
# incl: ángulo final de inclinación (grados); None = se queda recto
# peso: factor sobre el peso esperado; None = la celda no mide nada
ESCENARIOS = {
    "normal":        {"amp": 1.0,  "incl": None, "peso": 1.00},
    "sin_presencia": {"amp": None, "incl": None, "peso": None},
    "peso_bajo":     {"amp": 1.0,  "incl": None, "peso": 0.80},
    "peso_alto":     {"amp": 1.0,  "incl": None, "peso": 1.25},
    "golpe":         {"amp": 3.8,  "incl": None, "peso": 1.00},
    "inclinado":     {"amp": 1.0,  "incl": 40.0, "peso": 1.00},
    "ruidoso":       {"amp": 0.9,  "incl": None, "peso": 1.00, "ruido": 0.06},
}

UNIDADES = {"presencia": "g", "golpe": "g", "inclinacion": "°", "peso": "kg"}


def muestras(esc, rng, ruido=RUIDO_G, duracion=DURACION_S):
    """Genera (t, ax, ay, az) en g. Gravedad + ruido + impulso + inclinación."""
    for i in range(int(duracion * FS)):
        t = i / FS
        th = 0.0
        if esc["incl"] is not None and t >= T_INCLINACION:
            th = esc["incl"] * min(1.0, (t - T_INCLINACION) / 0.4)   # rampa de 0.4 s
        th_r = math.radians(th)
        ax, ay, az = math.sin(th_r), 0.0, math.cos(th_r)
        if esc["amp"] is not None and t >= T_IMPACTO:
            az += esc["amp"] * math.exp(-(t - T_IMPACTO) / 0.04)      # impulso amortiguado
        yield (t, ax + rng.gauss(0, ruido), ay + rng.gauss(0, ruido), az + rng.gauss(0, ruido))


def generar_peso(esperado, factor, rng):
    """Lectura simulada de la celda de carga: esperado x factor con ~1 % de ruido."""
    return round(esperado * factor * (1 + rng.gauss(0, 0.01)), 2)


def armar_evento(estacion, tipo, magnitud, ts):
    return {
        "estacion": estacion,
        "tipo": tipo,
        "magnitud": magnitud,
        "ts": ts.isoformat(timespec="milliseconds"),
        "origen": "simulado",
    }


def enviar(api, ev, dry_run):
    if dry_run:
        return True
    req = urllib.request.Request(
        api.rstrip("/") + "/api/evento",
        data=json.dumps(ev).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError) as e:
        print("   ! no se pudo enviar: %s" % e, file=sys.stderr)
        return False


def correr_escenario(nombre, args, rng):
    esc = ESCENARIOS[nombre]
    ruido = args.ruido if args.ruido is not None else esc.get("ruido", RUIDO_G)
    det = Detector(fs=FS)
    base = datetime.now()
    peso_pendiente = esc["peso"] is not None
    enviados = 0
    print("== escenario: %s (peso esperado %.2f kg) ==" % (nombre, args.peso))

    def emitir(tipo, magnitud, t):
        nonlocal enviados
        ev = armar_evento(args.estacion, tipo, magnitud, base + timedelta(seconds=t))
        ok = enviar(args.api, ev, args.dry_run)
        enviados += 1 if ok else 0
        print("   t=%.2fs  %-12s %7.2f %s  %s" % (t, tipo, magnitud, UNIDADES[tipo], "" if ok else "(falló)"))
        if args.dry_run:
            print("   " + json.dumps(ev, ensure_ascii=False))

    for t, ax, ay, az in muestras(esc, rng, ruido):
        for e in det.feed(t, ax, ay, az):
            emitir(e.tipo, e.magnitud, e.t)
        if peso_pendiente and t >= T_PESO:
            emitir("peso", generar_peso(args.peso, esc["peso"], rng), t)
            peso_pendiente = False
        if args.velocidad > 0:
            time.sleep(1.0 / (FS * args.velocidad))
    return enviados


def main():
    ap = argparse.ArgumentParser(description="Simulador de la estación IoT")
    ap.add_argument("--escenario", default="normal",
                    help="uno o varios separados por coma. Opciones: " + ", ".join(ESCENARIOS))
    ap.add_argument("--estacion", default="E1")
    ap.add_argument("--peso", type=float, default=10.0, help="peso esperado del bulto en kg")
    ap.add_argument("--api", default="http://localhost:8000", help="URL base del backend")
    ap.add_argument("--dry-run", action="store_true", help="no envía; solo imprime el JSON")
    ap.add_argument("--rapido", action="store_true", help="no espera tiempo real")
    ap.add_argument("--velocidad", type=float, default=1.0, help="1.0 = tiempo real, 2.0 = el doble")
    ap.add_argument("--ruido", type=float, default=None, help="sobrescribe el ruido del escenario (g)")
    ap.add_argument("--semilla", type=int, default=None, help="para resultados repetibles")
    ap.add_argument("--pausa", type=float, default=3.0, help="segundos entre escenarios")
    args = ap.parse_args()
    if args.rapido:
        args.velocidad = 0

    nombres = [n.strip() for n in args.escenario.split(",") if n.strip()]
    desconocidos = [n for n in nombres if n not in ESCENARIOS]
    if desconocidos:
        ap.error("escenario(s) desconocido(s): %s" % ", ".join(desconocidos))

    rng = random.Random(args.semilla)
    for i, n in enumerate(nombres):
        correr_escenario(n, args, rng)
        if i < len(nombres) - 1 and args.velocidad > 0:
            time.sleep(args.pausa)


if __name__ == "__main__":
    main()
