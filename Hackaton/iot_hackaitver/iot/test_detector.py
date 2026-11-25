import random
import unittest

import simulador as sim
from detector import Detector


def eventos_de(nombre, ruido=sim.RUIDO_G, semilla=1):
    rng = random.Random(semilla)
    det = Detector(fs=sim.FS)
    out = []
    for t, ax, ay, az in sim.muestras(sim.ESCENARIOS[nombre], rng, ruido):
        out += det.feed(t, ax, ay, az)
    return out


class PruebasDetector(unittest.TestCase):
    def test_normal_da_una_presencia(self):
        ev = eventos_de("normal")
        self.assertEqual([e.tipo for e in ev], ["presencia"])
        self.assertTrue(0.6 <= ev[0].magnitud <= 1.3)

    def test_golpe_da_presencia_y_golpe(self):
        ev = eventos_de("golpe")
        self.assertEqual(sorted(e.tipo for e in ev), ["golpe", "presencia"])
        golpe = [e for e in ev if e.tipo == "golpe"][0]
        self.assertGreaterEqual(golpe.magnitud, 2.5)

    def test_inclinado_da_inclinacion(self):
        ev = eventos_de("inclinado")
        self.assertEqual(sorted(e.tipo for e in ev), ["inclinacion", "presencia"])
        incl = [e for e in ev if e.tipo == "inclinacion"][0]
        self.assertTrue(30 <= incl.magnitud <= 45)

    def test_sin_presencia_no_da_eventos(self):
        self.assertEqual(eventos_de("sin_presencia"), [])

    def test_ruidoso_sigue_dando_una_presencia(self):
        ev = eventos_de("ruidoso", ruido=0.06)
        self.assertEqual([e.tipo for e in ev], ["presencia"])

    def test_sin_falsos_positivos_con_ruido(self):
        for semilla in range(50):
            self.assertEqual(eventos_de("sin_presencia", ruido=0.03, semilla=semilla), [],
                             "falso positivo con semilla %d" % semilla)

    def test_dos_bultos_separados_dan_dos_presencias(self):
        det = Detector(fs=sim.FS)
        rng = random.Random(3)
        out = []
        for i in range(300):
            t = i / sim.FS
            az = 1.0
            for t0 in (0.5, 1.5):
                if t >= t0:
                    az += 1.0 * __import__("math").exp(-(t - t0) / 0.04)
            out += det.feed(t, rng.gauss(0, .02), rng.gauss(0, .02), az + rng.gauss(0, .02))
        self.assertEqual([e.tipo for e in out], ["presencia", "presencia"])

    def test_peso_simulado_cerca_del_esperado(self):
        rng = random.Random(5)
        for _ in range(100):
            p = sim.generar_peso(10.0, 1.0, rng)
            self.assertTrue(9.5 <= p <= 10.5)
        self.assertLess(sim.generar_peso(10.0, 0.8, rng), 8.6)


if __name__ == "__main__":
    unittest.main()
