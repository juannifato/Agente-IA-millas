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
from tests.datos_muestra import CRUDO, CRUDO_SOLO_IDA


def usar_scraper(crudo):
    """El backend usa un scraper simulado que devuelve `crudo` (sin token real)."""
    class Falso(Scraper):
        clave = "aerolineas_arg"
        nombre = "Aerolineas (simulado)"

        def buscar(self, *a, **k):
            return crudo

    appmod.scrapers.obtener = lambda clave: Falso()


def main() -> int:
    cliente = appmod.app.test_client()

    # --- 1) ida y vuelta ---
    usar_scraper(CRUDO)
    r = cliente.post("/buscar", json={
        "origen": "AEP", "destino": "BRC",
        "fecha": "15/09/2026", "fecha_vuelta": "22/09/2026",
    })
    j = r.get_json()

    r2 = cliente.post("/buscar", json={"origen": "AEP", "destino": "AEP", "fecha": "15/09/2026"})
    j2 = r2.get_json()

    # --- 2) solo ida ---
    usar_scraper(CRUDO_SOLO_IDA)
    ri = cliente.post("/buscar", json={"origen": "AEP", "destino": "BRC", "fecha": "15/09/2026"})
    ji = ri.get_json()

    chequeos = [
        ("ida+vuelta: HTTP 200", r.status_code == 200 and j["ok"]),
        ("ida+vuelta: ya no se devuelve el 'crudo'", "crudo" not in j),
        ("ida+vuelta: recomendacion con dos tramos",
         j.get("mejor") and len(j["mejor"]["tramos"]) == 2),
        ("ida+vuelta: millas totales = suma de tramos",
         j["mejor"]["millas"] == sum(t["millas"] for t in j["mejor"]["tramos"])),
        ("ida+vuelta: evaluo las 4 opciones", j.get("opciones_evaluadas") == 4),
        ("ida+vuelta: hay texto de analisis", len(j.get("analisis", "")) > 10),
        ("origen==destino -> HTTP 400 con motivo",
         r2.status_code == 400 and j2["motivo"] == "datos_invalidos"),
        ("solo ida: HTTP 200 con un unico tramo",
         ri.status_code == 200 and ji["mejor"] and len(ji["mejor"]["tramos"]) == 1),
        ("solo ida: el tramo es la 'ida'", ji["mejor"]["tramos"][0]["tramo"] == "ida"),
        ("solo ida: eligio la mas barata (22000)", ji["mejor"]["millas"] == 22000),
    ]
    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print("\nRESULTADO:", "todo bien" if ok else "REVISAR")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
