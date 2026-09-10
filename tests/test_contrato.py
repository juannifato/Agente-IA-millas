r"""Tests del contrato de la API que consume Visual Basic. No usan red.

Cubren la validacion de entrada, los casos sin resultados y de API rota, y que
TODA respuesta (incluidos 404/405/502) sea JSON con `motivo`, porque si al
cliente de VB le llega HTML le explota al parsear.

    .\.venv\Scripts\python.exe tests\test_contrato.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as appmod
import scrapers
from scrapers.base import Scraper
from tests.datos_muestra import CRUDO_ROTO, CRUDO_VACIO

_OBTENER_ORIGINAL = scrapers.obtener


def usar_scraper(crudo):
    """Hace que el backend use un scraper simulado que devuelve `crudo`."""
    class Falso(Scraper):
        clave = "aerolineas_arg"
        nombre = "simulado"

        def buscar(self, *a, **k):
            return crudo

    appmod.scrapers.obtener = lambda clave: Falso()


def usar_scraper_real():
    """Restaura el ruteo real (para probar, ej., aerolinea desconocida)."""
    appmod.scrapers.obtener = _OBTENER_ORIGINAL


def main() -> int:
    cli = appmod.app.test_client()
    base = {"origen": "AEP", "destino": "BRC", "fecha": "15/09/2026"}
    chequeos = []

    def caso(nombre, cond):
        chequeos.append((nombre, cond))

    # --- validacion de entrada: todo 400 con motivo datos_invalidos ---
    usar_scraper_real()
    r = cli.post("/buscar", data="no soy json", content_type="text/plain")
    caso("cuerpo no-JSON -> 400 cuerpo_invalido",
         r.status_code == 400 and r.get_json()["motivo"] == "cuerpo_invalido")

    r = cli.post("/buscar", json={"destino": "BRC", "fecha": "15/09/2026"})
    caso("falta origen -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "origen": "BUEN"})
    caso("IATA de 4 letras -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "fecha": "01/01/2020"})
    caso("fecha en el pasado -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "fecha": "31/02/2026"})
    caso("fecha inexistente (31/02) -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "fecha_vuelta": "10/09/2026"})
    caso("vuelta antes que la ida -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "adultos": 0})
    caso("adultos fuera de rango -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "origen": "AEP", "destino": "AEP"})
    caso("origen igual a destino -> 400", r.status_code == 400)

    r = cli.post("/buscar", json={**base, "aerolinea": "no_existe"})
    caso("aerolinea desconocida -> 400 aerolinea_desconocida",
         r.status_code == 400 and r.get_json()["motivo"] == "aerolinea_desconocida")

    # --- sin resultados: la busqueda salio bien pero vino vacia ---
    usar_scraper(CRUDO_VACIO)
    r = cli.post("/buscar", json=base)
    j = r.get_json()
    caso("sin resultados -> 200 con mejor=null y mensaje",
         r.status_code == 200 and j["ok"] and j["mejor"] is None and "mensaje" in j)

    # --- API rota: la aerolinea cambio su formato ---
    usar_scraper(CRUDO_ROTO)
    r = cli.post("/buscar", json=base)
    j = r.get_json()
    caso("API sin brandedOffers -> 502 formato_desconocido",
         r.status_code == 502 and j["motivo"] == "formato_desconocido")

    # --- GET de servicio ---
    usar_scraper_real()
    r = cli.get("/salud")
    caso("/salud -> 200 ok", r.status_code == 200 and r.get_json()["ok"])

    r = cli.get("/aerolineas")
    j = r.get_json()
    caso("/aerolineas -> 200 con al menos una aerolinea",
         r.status_code == 200 and len(j["aerolineas"]) >= 1)

    # --- errores HTTP: siempre JSON, nunca HTML ---
    r = cli.get("/ruta-que-no-existe")
    caso("404 devuelve JSON con motivo",
         r.status_code == 404 and r.is_json and r.get_json()["motivo"] == "ruta_inexistente")

    r = cli.get("/buscar")  # /buscar es POST, un GET es metodo incorrecto
    caso("405 devuelve JSON con motivo",
         r.status_code == 405 and r.is_json and r.get_json()["motivo"] == "metodo_incorrecto")

    for txt, ok in chequeos:
        print(f"  [{'OK ' if ok else 'MAL'}] {txt}")
    ok = all(o for _, o in chequeos)
    print(f"\n{len(chequeos)} casos. RESULTADO:", "todo bien" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
