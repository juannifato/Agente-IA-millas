"""Contrato comun de todos los scrapers.

Cada aerolinea nueva (Fase 7) hereda de Scraper y solo implementa `buscar`.
El resto del sistema no sabe con que aerolinea esta hablando: pide vuelos y
recibe siempre la misma forma de datos.
"""
from abc import ABC, abstractmethod


class ErrorScraper(Exception):
    """Falla al obtener datos de la aerolinea.

    `motivo` es un codigo corto para que el frontend pueda reaccionar, y el
    mensaje de la excepcion es el texto que se le muestra al usuario.
    """

    def __init__(self, mensaje: str, motivo: str = "error_aerolinea"):
        super().__init__(mensaje)
        self.motivo = motivo


class Scraper(ABC):
    """Base de todos los extractores de vuelos."""

    # Identificador que manda el frontend para elegir esta aerolinea.
    clave: str = ""
    # Nombre para mostrarle al usuario.
    nombre: str = ""

    @abstractmethod
    def buscar(
        self,
        origen: str,
        destino: str,
        fecha_iso: str,
        fecha_vuelta_iso: str | None = None,
        adultos: int = 1,
    ) -> dict:
        """Devuelve los datos crudos de los vuelos disponibles.

        Args:
            origen: codigo IATA de salida, en mayusculas (ej. "BUE").
            destino: codigo IATA de llegada, en mayusculas (ej. "MAD").
            fecha_iso: fecha de salida en formato AAAA-MM-DD.
            fecha_vuelta_iso: fecha de regreso en AAAA-MM-DD. Si es None se
                busca solo ida.
            adultos: cantidad de pasajeros adultos.

        Returns:
            Un dict con los datos tal como los entrega la aerolinea. No se
            normaliza nada aca a proposito: de eso se encarga la IA en la
            Fase 4, que es justamente lo que evita escribir un parser
            distinto para cada aerolinea.

        Raises:
            ErrorScraper: si la aerolinea no responde o rechaza la consulta.
        """
        raise NotImplementedError
