"""Detector de eventos a partir de aceleración (MPU6050).

Solo librería estándar. Está escrito con una máquina de estados simple y sin
dependencias para poder portarse tal cual al firmware del ESP32 (mismos umbrales).

Entrada : muestras (t en segundos, ax, ay, az en g)
Salida  : eventos "presencia", "golpe" e "inclinacion"
"""
import math
from collections import deque
from dataclasses import dataclass

# --- Parámetros (los mismos irán en el firmware) ---
UMBRAL_PRESENCIA_G = 0.4     # |a| - 1 g mínimo para considerar que se colocó un bulto
UMBRAL_GOLPE_G = 2.5         # pico a partir del cual es manipulación brusca
PAUSA_MIN_S = 0.15           # anti-rebote entre eventos
VENTANA_PICO_S = 0.10        # tiempo máximo para medir el pico
UMBRAL_INCLINACION_DEG = 30.0
HISTERESIS_DEG = 5.0         # la inclinación se rearma al bajar de 25 grados
TIEMPO_INCLINACION_S = 0.5   # debe sostenerse para contar
VENTANA_PROMEDIO = 10        # muestras para promediar el ángulo


@dataclass
class Evento:
    tipo: str        # "presencia" | "golpe" | "inclinacion"
    magnitud: float  # g (presencia, golpe) o grados (inclinacion)
    t: float         # segundos, instante de la muestra que lo originó


class Detector:
    def __init__(self, fs=100,
                 umbral_presencia=UMBRAL_PRESENCIA_G,
                 umbral_golpe=UMBRAL_GOLPE_G,
                 umbral_inclinacion=UMBRAL_INCLINACION_DEG):
        self.fs = fs
        self.umbral_presencia = umbral_presencia
        self.umbral_golpe = umbral_golpe
        self.umbral_incl = umbral_inclinacion
        self.muestras_incl = max(1, int(TIEMPO_INCLINACION_S * fs))
        self._buf = deque(maxlen=VENTANA_PROMEDIO)
        # estado del detector de picos
        self._en_pico = False
        self._pico = 0.0
        self._t_pico = 0.0
        self._libre_desde = 0.0
        # estado del detector de inclinación
        self._n_incl = 0
        self._incl_activa = False

    def feed(self, t, ax, ay, az):
        """Procesa una muestra y devuelve la lista (posiblemente vacía) de eventos."""
        eventos = []
        mag = math.sqrt(ax * ax + ay * ay + az * az)
        dyn = abs(mag - 1.0)

        # ---- picos: presencia y golpe ----
        if self._en_pico:
            self._pico = max(self._pico, dyn)
            if dyn < self.umbral_presencia * 0.5 or (t - self._t_pico) >= VENTANA_PICO_S:
                eventos.append(Evento("presencia", round(self._pico, 2), self._t_pico))
                if self._pico >= self.umbral_golpe:
                    eventos.append(Evento("golpe", round(self._pico, 2), self._t_pico))
                self._en_pico = False
                self._libre_desde = t + PAUSA_MIN_S
        elif dyn >= self.umbral_presencia and t >= self._libre_desde:
            self._en_pico = True
            self._pico = dyn
            self._t_pico = t

        # ---- inclinación: ángulo promediado respecto a la vertical ----
        self._buf.append((ax, ay, az))
        n = len(self._buf)
        mx = sum(m[0] for m in self._buf) / n
        my = sum(m[1] for m in self._buf) / n
        mz = sum(m[2] for m in self._buf) / n
        ang = math.degrees(math.atan2(math.sqrt(mx * mx + my * my), mz))

        if ang >= self.umbral_incl:
            self._n_incl += 1
            if not self._incl_activa and self._n_incl >= self.muestras_incl:
                eventos.append(Evento("inclinacion", round(ang, 1), t))
                self._incl_activa = True
        else:
            self._n_incl = 0
            if ang < self.umbral_incl - HISTERESIS_DEG:
                self._incl_activa = False

        return eventos
