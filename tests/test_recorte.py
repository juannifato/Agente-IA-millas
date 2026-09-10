r"""Tests del recorte (ia/recorte.py). No usan red: se corren siempre.

    .\.venv\Scripts\python.exe tests\test_recorte.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ia.recorte import medir, recortar
from tests.datos_muestra import CRUDO


def main() -> int:
    r = recortar(CRUDO)
    ida = r["tramos"][0]
    directo, escala = ida["vuelos"][0], ida["vuelos"][1]

    chequeos = [
        ("los tramos salen ordenados ida->vuelta",
         [t["tramo"] for t in r["tramos"]] == ["ida", "vuelta"]),
        ("total_opciones = 4 (la tarifa sin millas no cuenta)",
         r["total_opciones"] == 4),
        ("las fechas con zona horaria se recortan a minutos",
         directo["sale"] == "2026-09-15T08:10"),
        ("el directo no tiene escalas", directo["escalas"] == 0),
        ("la escala se detecta y dice donde",
         escala["escalas"] == 1 and escala["escalas_en"] == ["MDZ"]),
        ("sin totalDuration, la duracion se calcula de los horarios",
         escala["duracion_min"] == 260),
        ("el vuelo con escala arma la ruta completa AEP->BRC",
         escala["origen"] == "AEP" and escala["destino"] == "BRC"),
        ("se descarto la tarifa sin millas", len(directo["tarifas"]) == 1),
        ("los ids son unicos y estables",
         [t["id"] for v in ida["vuelos"] for t in v["tarifas"]] == ["ida-1.1", "ida-2.1"]),
        ("el recorte achica al menos 85%", medir(CRUDO, r)["reduccion_pct"] >= 85),
    ]
    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
