r"""Test de integracion de POST /buscar, de punta a punta.

Simula el scraper (para no depender del token de Aerolineas) pero pega contra
Groq DE VERDAD, asi que necesita GROQ_API_KEY cargada en el .env.

    .\.venv\Scripts\python.exe tests\test_endpoint.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as appmod
import scrapers
from scrapers.base import Scraper
from tests.datos_muestra import CRUDO


class ScraperFalso(Scraper):
    clave = "aerolineas_arg"
    nombre = "Aerolineas (simulado)"

    def buscar(self, *a, **k):
        return CRUDO


def main() -> int:
    # Se reemplaza el scraper real por el falso: no toca el token de Aerolineas.
    appmod.scrapers.obtener = lambda clave: ScraperFalso()
    cliente = appmod.app.test_client()

    r = cliente.post("/buscar", json={
        "origen": "AEP", "destino": "BRC",
        "fecha": "15/09/2026", "fecha_vuelta": "22/09/2026",
    })
    j = r.get_json()

    r2 = cliente.post("/buscar", json={"origen": "AEP", "destino": "AEP", "fecha": "15/09/2026"})
    j2 = r2.get_json()

    chequeos = [
        ("HTTP 200 en la busqueda valida", r.status_code == 200 and j["ok"]),
        ("ya no se devuelve el 'crudo'", "crudo" not in j),
        ("hay recomendacion 'mejor' con ida y vuelta",
         j.get("mejor") and len(j["mejor"]["tramos"]) == 2),
        ("las millas totales son la suma de los tramos",
         j["mejor"]["millas"] == sum(t["millas"] for t in j["mejor"]["tramos"])),
        ("evaluo las 4 opciones", j.get("opciones_evaluadas") == 4),
        ("hay texto de analisis", len(j.get("analisis", "")) > 10),
        ("origen==destino -> HTTP 400 con motivo",
         r2.status_code == 400 and j2["motivo"] == "datos_invalidos"),
    ]
    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "REVISAR")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
