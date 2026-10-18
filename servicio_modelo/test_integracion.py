#!/usr/bin/env python3
"""
Comprobacion de INTEGRACION.md: con perfiles.json y replicas=10000, los cuatro
casos de modelo/casos_referencia.json deben dar las mismas bandas, la misma
metrica determinante, y medianas y certidumbre con tolerancia de 0,005.

Los casos se corren por el mismo camino que usa la app: el script
recomendar.py como subproceso, con la peticion JSON por stdin.

Uso:
    python servicio_modelo/test_integracion.py
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI / "recomendar.py"
CASOS = json.loads((AQUI.parent / "modelo" / "casos_referencia.json")
                   .read_text(encoding="utf-8"))
TOL = 0.005
TRM = 4000.0


def correr_como_la_app(entrada):
    peticion = {"accion": "recomendar", **entrada, "trm": TRM, "replicas": 10000}
    proc = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(peticion),
                          capture_output=True, text=True, encoding="utf-8", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"recomendar.py falló: {proc.stdout} {proc.stderr}")
    return json.loads(proc.stdout)


class CasosReferencia(unittest.TestCase):
    salidas = {}

    @classmethod
    def setUpClass(cls):
        for nombre, caso in CASOS.items():
            cls.salidas[nombre] = correr_como_la_app(caso["entrada"])

    def test_casos(self):
        for nombre, esperado in CASOS.items():
            r = self.salidas[nombre]["resultado"]
            with self.subTest(caso=nombre):
                self.assertEqual([b["redes"] for b in r["bandas"]], esperado["bandas"])
                self.assertIsNotNone(r["determinante"])
                self.assertEqual(r["determinante"]["metrica"], esperado["determinante"])
                self.assertAlmostEqual(r["certidumbre"], esperado["certidumbre"], delta=TOL)
                medianas = {red: p["mediana"] for b in r["bandas"]
                            for red, p in b["puntajes"].items()}
                self.assertEqual(set(medianas), set(esperado["medianas"]))
                for red, m in esperado["medianas"].items():
                    self.assertAlmostEqual(medianas[red], m, delta=TOL, msg=red)

    def test_respuesta_trae_lo_que_la_app_debe_mostrar(self):
        for nombre, salida in self.salidas.items():
            with self.subTest(caso=nombre):
                self.assertIn("advertencias", salida["resultado"])
                self.assertTrue(salida["medicion"])
                self.assertIn(salida["nivel_certidumbre"], ("alta", "media", "baja"))


def imprimir_salidas():
    print("\nSalida de los cuatro casos (replicas=10000, trm=4000):")
    for nombre, esperado in CASOS.items():
        s = CasosReferencia.salidas[nombre]
        r = s["resultado"]
        print(f"\n  {nombre}  {json.dumps(esperado['entrada'], ensure_ascii=False)}")
        print(f"    certidumbre  {r['certidumbre']:.3f} ({s['nivel_certidumbre']})"
              f"   esperada {esperado['certidumbre']:.3f}")
        for b in r["bandas"]:
            meds = "  ".join(f"{red} {p['mediana']:.3f} [{p['p05']:.3f}-{p['p95']:.3f}]"
                             f" (esp. {esperado['medianas'][red]:.3f})"
                             for red, p in b["puntajes"].items())
            print(f"    banda {b['banda']}  {meds}")
        d = r["determinante"]
        print(f"    determinante {d['metrica']} (contribución {d['contribucion']:.4f})"
              f"   esperada {esperado['determinante']}")
        for adv in r["advertencias"]:
            print(f"    aviso: {adv}")
        print(f"    medición: {s['medicion']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    programa = unittest.main(exit=False, verbosity=2)
    if CasosReferencia.salidas:
        imprimir_salidas()
    sys.exit(not programa.result.wasSuccessful())
