"""Registro de scrapers disponibles (ruteo dinamico de la Fase 7).

Para sumar una aerolinea: crear el modulo, importarlo aca y agregarlo a la
lista DISPONIBLES. No hay que tocar nada mas del backend.
"""
from scrapers.aerolineas_arg import AerolineasArgentinas
from scrapers.base import ErrorScraper, Scraper

DISPONIBLES: list[type[Scraper]] = [
    AerolineasArgentinas,
    # Fase 7: Smiles, AmericanAirlines, ...
]

_POR_CLAVE: dict[str, type[Scraper]] = {c.clave: c for c in DISPONIBLES}

# Si el frontend no manda aerolinea, se usa la primera.
CLAVE_POR_DEFECTO = DISPONIBLES[0].clave


def obtener(clave: str) -> Scraper:
    """Devuelve una instancia del scraper pedido.

    Raises:
        ErrorScraper: si la clave no corresponde a ninguna aerolinea registrada.
    """
    clase = _POR_CLAVE.get(clave)
    if clase is None:
        disponibles = ", ".join(sorted(_POR_CLAVE))
        raise ErrorScraper(
            f"La aerolinea '{clave}' no esta soportada. Disponibles: {disponibles}",
            motivo="aerolinea_desconocida",
        )
    return clase()


def catalogo() -> list[dict]:
    """Lista de aerolineas soportadas, para que el frontend arme su combo."""
    return [{"clave": c.clave, "nombre": c.nombre} for c in DISPONIBLES]


__all__ = ["ErrorScraper", "Scraper", "catalogo", "obtener", "CLAVE_POR_DEFECTO"]
