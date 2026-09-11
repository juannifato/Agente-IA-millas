"""Orquesta una busqueda: pide los vuelos, los recorta y elige el mejor.

Es el camino que comparten el endpoint /buscar (formulario) y el chat (Fase 6):
los dos llegan con los datos ya validados y necesitan exactamente lo mismo. Los
errores (ErrorScraper, ErrorRecorte, ErrorIA) se dejan propagar para que cada
quien decida el codigo HTTP.
"""
import scrapers
from ia import recortar
from ia.analisis_ia import analizar


def buscar_vuelos(origen: str, destino: str, fecha_iso: str,
                  fecha_vuelta_iso: str | None = None, adultos: int = 1,
                  clave: str | None = None) -> dict:
    """Devuelve la recomendacion para esos datos.

    Returns:
        `{"vacio": True}` si la busqueda salio bien pero no hay vuelos en millas,
        o `{"vacio": False, "mejor": ..., "analisis": ..., "eleccion_por_ia": ...,
        "opciones_evaluadas": ...}` si los hay.

    Raises:
        ErrorScraper, ErrorRecorte, ErrorIA: segun donde falle la cadena.
    """
    clave = clave or scrapers.CLAVE_POR_DEFECTO
    extractor = scrapers.obtener(clave)
    crudo = extractor.buscar(origen, destino, fecha_iso, fecha_vuelta_iso, adultos)

    recortado = recortar(crudo)
    if recortado["total_opciones"] == 0:
        return {"vacio": True}

    analisis = analizar(recortado)
    return {
        "vacio": False,
        "mejor": analisis["mejor"],
        "analisis": analisis["analisis"],
        "eleccion_por_ia": analisis["eleccion_por_ia"],
        "opciones_evaluadas": recortado["total_opciones"],
    }
