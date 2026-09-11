r"""Corre todos los tests del proyecto y devuelve un unico resultado.

    .\.venv\Scripts\python.exe tests\correr_todo.py

test_endpoint necesita GROQ_API_KEY (pega contra Groq de verdad); el resto no
usa red. Si falta la clave, ese test se marca como salteado, no como fallado.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import GROQ_API_KEY

# (modulo, necesita_groq)
SUITE = [
    ("tests.test_recorte", False),
    ("tests.test_analisis", False),
    ("tests.test_contrato", False),
    ("tests.test_endpoint", True),
    ("tests.test_chat", True),
]


def main() -> int:
    hay_groq = bool(GROQ_API_KEY) and "pegar_aca" not in GROQ_API_KEY
    fallaron, salteados = [], []

    for nombre, necesita_groq in SUITE:
        print(f"\n{'=' * 60}\n{nombre}\n{'=' * 60}")
        if necesita_groq and not hay_groq:
            print("  SALTEADO: falta GROQ_API_KEY en el .env.")
            salteados.append(nombre)
            continue
        modulo = importlib.import_module(nombre)
        if modulo.main() != 0:
            fallaron.append(nombre)

    print(f"\n{'#' * 60}")
    if fallaron:
        print("HAY TESTS QUE FALLARON:", ", ".join(fallaron))
    else:
        print("TODOS LOS TESTS PASARON.")
    if salteados:
        print("Salteados (sin red):", ", ".join(salteados))
    return 1 if fallaron else 0


if __name__ == "__main__":
    sys.exit(main())
