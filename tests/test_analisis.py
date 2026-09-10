r"""Tests de la reconstruccion y la red de seguridad (ia/analisis_ia.py).

No usan red: prueban que, pase lo que pase con la IA, Python arma una respuesta
completa y coherente. La llamada real a Groq se prueba en test_endpoint.py.

    .\.venv\Scripts\python.exe tests\test_analisis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ia.analisis_ia import _construir_mejor
from ia.recorte import recortar
from tests.datos_muestra import CRUDO

REC = recortar(CRUDO)  # ida: ida-1.1(30000), ida-2.1(25000); vuelta: v-1.1(32000), v-2.1(28000)


def main() -> int:
    chequeos = []

    m, regla = _construir_mejor(REC, {"ida": "ida-1.1", "vuelta": "vuelta-2.1"})
    chequeos.append(("IA elige ids validos: se respetan",
                     m["tramos"][0]["millas"] == 30000 and m["millas"] == 58000 and not regla))

    m, regla = _construir_mejor(REC, {"ida": "ida-99.9", "vuelta": "vuelta-2.1"})
    chequeos.append(("id inexistente: cae a la regla (menos millas = 25000) y avisa",
                     m["tramos"][0]["millas"] == 25000 and regla))

    m, regla = _construir_mejor(REC, {"ida": "ida-1.1", "vuelta": "ida-2.1"})
    chequeos.append(("id de otro tramo: se rechaza y cae a la regla en la vuelta",
                     m["tramos"][1]["millas"] == 28000 and regla))

    m, regla = _construir_mejor(REC, {})
    chequeos.append(("sin elecciones: regla en los dos tramos (25000 + 28000)",
                     m["millas"] == 53000 and regla))

    m, _ = _construir_mejor(REC, {"ida": "ida-1.1", "vuelta": "vuelta-1.1"})
    chequeos.append(("los impuestos se suman", m["impuestos"] == 128044))

    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
