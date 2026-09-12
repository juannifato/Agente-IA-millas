"""Orquesta una busqueda: pide los vuelos, los recorta y elige el mejor.

Es el camino que comparten el endpoint /buscar (formulario) y el chat: los dos
llegan con los datos ya validados y necesitan lo mismo. Los errores (ErrorScraper,
ErrorRecorte, ErrorIA) se dejan propagar para que cada quien decida el codigo HTTP.

Guarda en memoria el ultimo crudo de cada busqueda por unos minutos. Asi cuando
el chat refina ("y a la manana?", "sin escalas") no se vuelve a consultar a la
aerolinea: se filtra sobre lo ya traido, respetando el limite de consultas.
"""
import time

import scrapers
from ia import recortar
from ia.analisis_ia import analizar
from ia.recorte import filtrar_por_franja

_CACHE: dict = {}
_TTL_SEG = 300  # 5 minutos, suficiente para encadenar refinamientos de una charla


def limpiar_cache() -> None:
    """Vacia el cache de crudos. Lo usan los tests para aislar cada caso."""
    _CACHE.clear()


def _traer_crudo(clave, origen, destino, fecha_iso, fecha_vuelta_iso, adultos) -> dict:
    """El crudo de la aerolinea, reusando el cacheado si es reciente."""
    llave = (clave, origen, destino, fecha_iso, fecha_vuelta_iso, adultos)
    ahora = time.time()
    guardado = _CACHE.get(llave)
    if guardado and ahora - guardado[0] < _TTL_SEG:
        return guardado[1]

    extractor = scrapers.obtener(clave)
    crudo = extractor.buscar(origen, destino, fecha_iso, fecha_vuelta_iso, adultos)
    _CACHE[llave] = (ahora, crudo)
    return crudo


def buscar_vuelos(origen: str, destino: str, fecha_iso: str,
                  fecha_vuelta_iso: str | None = None, adultos: int = 1,
                  clave: str | None = None, franja: str | None = None) -> dict:
    """Devuelve la recomendacion para esos datos.

    Args:
        franja: si viene ('manana', 'tarde', ...), se filtran los vuelos por hora
            de salida antes de elegir.

    Returns:
        `{"vacio": True}` si la busqueda salio bien pero no hay vuelos (con
        `motivo_vacio: "franja"` si el vacio es por el filtro de horario), o
        `{"vacio": False, "mejor": ..., ...}` si los hay.

    Raises:
        ErrorScraper, ErrorRecorte, ErrorIA: segun donde falle la cadena.
    """
    clave = clave or scrapers.CLAVE_POR_DEFECTO
    crudo = _traer_crudo(clave, origen, destino, fecha_iso, fecha_vuelta_iso, adultos)

    recortado = recortar(crudo)
    if franja:
        recortado = filtrar_por_franja(recortado, franja)

    if recortado["total_opciones"] == 0:
        vacio = {"vacio": True}
        if recortado.get("sin_franja"):
            vacio["motivo_vacio"] = "franja"
        return vacio

    analisis = analizar(recortado)
    return {
        "vacio": False,
        "mejor": analisis["mejor"],
        "analisis": analisis["analisis"],
        "eleccion_por_ia": analisis["eleccion_por_ia"],
        "opciones_evaluadas": recortado["total_opciones"],
    }
